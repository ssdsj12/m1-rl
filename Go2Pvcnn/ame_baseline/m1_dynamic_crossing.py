"""Direction-latched, per-wheel encounters for an unordered mixed course.

This adapter supplies one real encountered obstacle to the legacy physical
clearance/landing/recovery gate. It never calls a random tile 'completed'.
"""
from __future__ import annotations
import torch
from .m1_strict_crossing import StrictCrossingTracker, m1_wheel_lateral_half_width_from_quat


class EncounterCrossingTracker:
    def __init__(self,num_envs,device,*,obstacle_count):
        self.inner=StrictCrossingTracker(num_envs,device,obstacle_count=1)
        self.device=torch.device(device)
        self.capacity=obstacle_count
        self.slot=torch.full((num_envs,),-1,device=device,dtype=torch.long)
        self.target_obstacle_id=torch.full_like(self.slot,-1)
        self.heading=torch.zeros(num_envs,2,device=device);self.heading[:,0]=1
        self.early_lift=torch.zeros(num_envs,device=device,dtype=torch.bool)
        self.prelift_rewarded=torch.zeros_like(self.early_lift)
        self.prelift_high_water=torch.zeros(num_envs,device=device)
        self.last_contact_bottom=torch.full((num_envs,),float('nan'),device=device)
        self.prelift_bottom_high_water=torch.full_like(self.last_contact_bottom,float('nan'))
        self.used=torch.zeros(num_envs,obstacle_count,4,device=device,dtype=torch.bool)
        self.known_ids=torch.full((num_envs,obstacle_count),-2,device=device,dtype=torch.long)
        self.crossing_count=torch.zeros_like(self.slot)

    def __getattr__(self,name):
        return getattr(self.inner,name)

    def reset(self,rows):
        self.inner.reset(rows)
        self.slot[rows]=-1;self.target_obstacle_id[rows]=-1
        self.early_lift[rows]=False;self.used[rows]=False
        self.prelift_rewarded[rows]=False
        self.prelift_high_water[rows]=0
        self.last_contact_bottom[rows]=float('nan')
        self.prelift_bottom_high_water[rows]=float('nan')
        self.crossing_count[rows]=0;self.known_ids[rows]=-2

    @torch.no_grad()
    def update(self,*,wheel_pos_w,wheel_quat_w,course,direction_w,wheel_bottom_z_w,wheel_grounded,
               support_safe,touchdown_safe,collision,wheel_horizontal_radius,
               wheel_vertical_radius,wheel_thickness,required_clearance=.03,
               required_far_margin=.04,stable_frames=5,approach_distance=.25):
        b=wheel_pos_w.shape[0];rows=torch.arange(b,device=self.device)
        centers=course['centers_top'];extents=course['half_extents'];valid=course['valid'];ids=course['ids']
        if wheel_grounded.shape!=(b,4) or wheel_grounded.dtype!=torch.bool:
            raise ValueError('wheel_grounded must be measured bool [B,4]')
        if centers.shape!=(b,self.capacity,3) or valid.shape!=(b,self.capacity) or ids.shape!=valid.shape:
            raise ValueError('course registry capacity/batch mismatch')
        if (extents.shape!=(b,self.capacity,2) or direction_w.shape!=(b,2)
                or not torch.isfinite(direction_w).all()
                or not torch.isfinite(centers[valid]).all()
                or not torch.isfinite(extents[valid]).all()
                or (extents[valid]<=0).any()):
            raise ValueError('invalid actual course geometry/direction')
        changed=(self.known_ids!=-2).any(-1)&(self.known_ids!=ids).any(-1)
        if changed.any(): self.reset(changed)
        self.known_ids.copy_(ids)
        norm=torch.linalg.vector_norm(direction_w,dim=-1)
        direction=direction_w/norm.clamp_min(1e-9)[:,None]
        idle=self.slot<0
        self.heading=torch.where(idle[:,None]&(norm>1e-6)[:,None],direction,self.heading)
        side=torch.stack((-self.heading[:,1],self.heading[:,0]),-1)
        # Rotate wheel quaternions into the latched encounter frame before
        # measuring the lateral projection; do not assume world-Y wheel width.
        theta=torch.atan2(self.heading[:,1],self.heading[:,0])/2
        c,s=theta.cos()[:,None],theta.sin()[:,None]
        qw,qx,qy,qz=wheel_quat_w.unbind(-1)
        local_quat=torch.stack((c*qw+s*qz,c*qx+s*qy,c*qy-s*qx,c*qz-s*qw),-1)
        widths=m1_wheel_lateral_half_width_from_quat(local_quat,
            wheel_radius=wheel_vertical_radius,wheel_thickness=wheel_thickness)
        hx=(extents*self.heading.abs()[:,None]).sum(-1)
        hy=(extents*side.abs()[:,None]).sum(-1)
        rel=wheel_pos_w[:,None,:,:2]-centers[:,:,None,:2]
        longitudinal=(rel*self.heading[:,None,None]).sum(-1)
        lateral=(rel*side[:,None,None]).sum(-1).abs()
        gap=-hx[:,:,None]-(longitudinal+wheel_horizontal_radius)
        eligible=(valid[:,:,None]&~self.used&(gap>=0)&(gap<=approach_distance)
            &(lateral<=hy[:,:,None]+widths[:,None])&idle[:,None,None]
            &(norm>1e-6)[:,None,None]&~changed[:,None,None]&~self.inner.failed[:,None,None])
        choice=torch.where(eligible,gap,torch.full_like(gap,torch.inf)).flatten(1).argmin(-1)
        start=eligible.flatten(1).any(-1)
        new_slot=choice//4;new_wheel=choice%4
        self.slot=torch.where(start,new_slot,self.slot)
        self.target_obstacle_id=torch.where(start,ids[rows,new_slot],self.target_obstacle_id)
        self.inner.target_wheel=torch.where(start,new_wheel,self.inner.target_wheel)
        self.last_contact_bottom[start]=float('nan')
        self.prelift_bottom_high_water[start]=float('nan')
        self.prelift_high_water[start]=0
        self.used[rows[start],new_slot[start],new_wheel[start]]=True
        enabled=self.slot>=0
        slot=self.slot.clamp_min(0)
        selected=self.inner.target_wheel.clamp_min(0)
        selected_center=centers[rows,slot]
        delta=wheel_pos_w[:,:,:2]-selected_center[:,None,:2]
        local_pos=wheel_pos_w.clone()
        local_pos[:,:,0]=(delta*self.heading[:,None]).sum(-1)
        local_pos[:,:,1]=(delta*side[:,None]).sum(-1)
        # No event: never let the delegated tracker select a phantom obstacle.
        local_pos[:,:,0]=torch.where(enabled[:,None],local_pos[:,:,0],torch.full_like(local_pos[:,:,0],-1e6))
        near=-hx[rows,slot]
        before=local_pos[rows,selected,0]+wheel_horizontal_radius<=near
        grounded=wheel_grounded[rows,selected]
        bottom=wheel_bottom_z_w[rows,selected]
        # Track the last loaded wheel-bottom location, not the ground beneath
        # the future obstacle. Rolling uphill while loaded is not an air lift.
        contact_update=enabled&before&grounded&torch.isfinite(bottom)
        self.last_contact_bottom=torch.where(contact_update,bottom,self.last_contact_bottom)
        loaded_high_water=torch.where(torch.isfinite(self.prelift_bottom_high_water),
            torch.maximum(self.prelift_bottom_high_water,bottom),bottom)
        self.prelift_bottom_high_water=torch.where(contact_update,loaded_high_water,
                                                   self.prelift_bottom_high_water)
        lifted=(~grounded & torch.isfinite(self.last_contact_bottom)
                & (bottom>=self.last_contact_bottom+.02))
        single_support = wheel_grounded.sum(-1) == 3
        self.early_lift |= enabled&before&lifted&single_support
        self.inner.failed |= enabled & self.early_lift & ~grounded & ~single_support
        single_prelift = (enabled & before & lifted & (wheel_grounded.sum(-1) == 3)
                          & ~self.inner.failed & ~collision & ~self.prelift_rewarded)
        self.prelift_rewarded |= single_prelift
        overlap = (enabled & (local_pos[rows,selected,0]+wheel_horizontal_radius >= near)
            & (local_pos[rows,selected,0]-wheel_horizontal_radius <= hx[rows,slot])
            & (local_pos[rows,selected,1].abs() <= hy[rows,slot]+widths[rows,selected]))
        bottom_clearance = bottom-selected_center[:,2]
        # Every sampled overlap must clear the top, not merely one lucky frame.
        self.inner.failed |= overlap & (~torch.isfinite(bottom_clearance)
                                        | (bottom_clearance < required_clearance))
        self.inner.failed |= enabled&~before&~self.early_lift
        fully_past=(local_pos[rows,selected,0]-wheel_horizontal_radius
                    >=hx[rows,slot]+required_far_margin)
        self.inner.failed |= (enabled&self.early_lift&grounded&~fully_past
                              &~self.inner.awaiting_recovery)
        obstacle=wheel_pos_w.new_zeros(b,1,3);obstacle[:,0,2]=selected_center[:,2]
        projected=torch.stack((hx[rows,slot],hy[rows,slot]),-1).clamp_min(1e-6)
        # All four wheel envelopes need free XY support space, including large
        # obstacles. This is a conservative runtime gate, not a route planner.
        landing_centers=course.get('landing_centers_top',centers)
        landing_extents=course.get('landing_half_extents',extents)
        landing_valid=course.get('landing_valid',valid)
        offset=(wheel_pos_w[:,:,None,:2]-landing_centers[:,None,:,:2]).abs()-landing_extents[:,None]
        distance=torch.linalg.vector_norm(offset.clamp_min(0),dim=-1)
        landing_free=~((distance<wheel_horizontal_radius)&landing_valid[:,None]).any(-1).any(-1)
        out=self.inner.update(wheel_pos_w=local_pos,obstacle_centers_top_w=obstacle,
            support_safe=support_safe&enabled,touchdown_safe=touchdown_safe&enabled&self.early_lift&landing_free,
            collision=collision&enabled,wheel_horizontal_radius=wheel_horizontal_radius,
            wheel_vertical_radius=wheel_vertical_radius,wheel_lateral_half_width=widths,
            wheel_bottom_z_w=wheel_bottom_z_w,obstacle_half_extents=projected,
            required_clearance=required_clearance,required_far_margin=required_far_margin,
            stable_frames=stable_frames,approach_distance=approach_distance)
        self.crossing_count+=out['event_complete'].long()
        out['attempt_started']=start
        out['crossing_count']=self.crossing_count.clone()
        out['episode_complete']=torch.zeros_like(start)
        out['target_obstacle_id']=self.target_obstacle_id.clone()
        out['single_prelift_event']=single_prelift
        # Reward newly measured rise before the obstacle, while retaining the
        # >=2cm event as telemetry and as a separate strict crossing gate.
        # The world-bottom high-water mark survives bobbing and lower loaded
        # references. Loaded uphill motion advances it without reward. The
        # normalized budget caps all increments at one per encounter.
        matches_lane=local_pos[rows,selected,1].abs()<=hy[rows,slot]+widths[rows,selected]
        progress_safe=(enabled & before & matches_lane & ~grounded & single_support
                       & ~out['failed'] & ~collision & torch.isfinite(bottom)
                       & torch.isfinite(self.last_contact_bottom)
                       & torch.isfinite(self.prelift_bottom_high_water))
        rise=((bottom-self.prelift_bottom_high_water)/.02).clamp(0.,1.)
        progress_delta=torch.minimum(rise,1.-self.prelift_high_water)
        out['prelift_progress_delta']=torch.where(progress_safe,progress_delta,
                                                 torch.zeros_like(progress_delta))
        self.prelift_high_water+=out['prelift_progress_delta']
        self.prelift_bottom_high_water=torch.where(progress_safe,
            torch.maximum(self.prelift_bottom_high_water,bottom),self.prelift_bottom_high_water)
        out['overlap_sample']=overlap & torch.isfinite(bottom_clearance)
        out['bottom_clearance']=torch.where(out['overlap_sample'], bottom_clearance,
                                           torch.full_like(bottom_clearance, float('nan')))
        # Failed attempts stay counted, but must not suppress every later
        # encounter. Release only once the target wheel leaves this vicinity.
        outside=(local_pos[rows,selected,0].abs()>hx[rows,slot]+wheel_horizontal_radius+approach_distance)
        outside |= local_pos[rows,selected,1].abs()>hy[rows,slot]+widths[rows,selected]+approach_distance
        abandoned=enabled&outside&~self.inner.awaiting_recovery
        out['failed'] |= abandoned
        released=out['recovery_complete'] | abandoned
        if released.any():
            self.inner.reset(released)
            self.slot[released]=-1;self.target_obstacle_id[released]=-1;self.early_lift[released]=False
            self.prelift_rewarded[released]=False
            self.prelift_high_water[released]=0
            self.last_contact_bottom[released]=float('nan')
            self.prelift_bottom_high_water[released]=float('nan')
        return out
