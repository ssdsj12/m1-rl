"""Direction-latched, per-wheel encounters for an unordered mixed course.

This adapter supplies one real encountered obstacle to the legacy physical
clearance/landing/recovery gate. It never calls a random tile 'completed'.
"""
from __future__ import annotations
import torch
from .m1_strict_crossing import StrictCrossingTracker, m1_wheel_lateral_half_width_from_quat


def autonomous_lift_stage_mask(levels, done, *, flat_first):
    """Select current progressive rows, never an auto-reset terminal pose."""
    if (levels.ndim != 1 or levels.shape != done.shape or done.dtype != torch.bool
            or levels.device != done.device or levels.dtype not in (torch.int32, torch.int64)):
        raise ValueError('levels/done must be aligned integer/bool [B] on the same device')
    return ((levels >= 1) & (levels <= 3) & ~done) if flat_first else torch.zeros_like(done)


class EncounterCrossingTracker:
    def __init__(self,num_envs,device,*,obstacle_count):
        self.inner=StrictCrossingTracker(num_envs,device,obstacle_count=1)
        self.device=torch.device(device)
        self.capacity=obstacle_count
        self.slot=torch.full((num_envs,),-1,device=device,dtype=torch.long)
        self.target_obstacle_id=torch.full_like(self.slot,-1)
        self.heading=torch.zeros(num_envs,2,device=device);self.heading[:,0]=1
        self.early_lift=torch.zeros(num_envs,device=device,dtype=torch.bool)
        # Autonomous timing is opt-in per row. Historical 2cm telemetry must
        # not serve as the flight/overlap lifecycle for progressive stages.
        self.flight_active=torch.zeros_like(self.early_lift)
        self.crossing_started=torch.zeros_like(self.early_lift)
        self.autonomous_mode=torch.zeros_like(self.early_lift)
        self.mode_known=torch.zeros_like(self.early_lift)
        self.prelift_rewarded=torch.zeros_like(self.early_lift)
        self.prelift_high_water=torch.zeros(num_envs,device=device)
        self.last_contact_bottom=torch.full((num_envs,),float('nan'),device=device)
        self.prelift_bottom_high_water=torch.full_like(self.last_contact_bottom,float('nan'))
        self.prelift_target_bottom=torch.full_like(self.last_contact_bottom,float('nan'))
        self.prelift_budget=torch.zeros_like(self.prelift_high_water)
        self.used=torch.zeros(num_envs,obstacle_count,4,device=device,dtype=torch.bool)
        self.recovered=torch.zeros_like(self.used)
        self.known_ids=torch.full((num_envs,obstacle_count),-2,device=device,dtype=torch.long)
        self.crossing_count=torch.zeros_like(self.slot)
        from .m1_learning_progress import LearningProgress
        self.learning_progress=LearningProgress(num_envs,device)

    def __getattr__(self,name):
        return getattr(self.inner,name)

    def reset(self,rows):
        self.inner.reset(rows)
        self.learning_progress.reset(rows)
        self.slot[rows]=-1;self.target_obstacle_id[rows]=-1
        self.early_lift[rows]=False;self.used[rows]=False
        self.flight_active[rows]=False;self.crossing_started[rows]=False
        self.autonomous_mode[rows]=False;self.mode_known[rows]=False
        self.recovered[rows]=False
        self.prelift_rewarded[rows]=False
        self.prelift_high_water[rows]=0
        self.last_contact_bottom[rows]=float('nan')
        self.prelift_bottom_high_water[rows]=float('nan')
        self.prelift_target_bottom[rows]=float('nan')
        self.prelift_budget[rows]=0
        self.crossing_count[rows]=0;self.known_ids[rows]=-2

    @torch.no_grad()
    def recovered_for_course(self,course):
        """Return strict receipts only for the same current registry identities.

        This read-only snapshot is safe to query before the next update notices
        a terrain change. Unknown, replaced and invalid slots have no receipt.
        """
        ids,valid=course['ids'],course['valid']
        if ids.shape!=self.known_ids.shape or valid.shape!=ids.shape:
            raise ValueError('course registry capacity/batch mismatch')
        matches=(self.known_ids==ids)&(self.known_ids>=0)&valid
        return (self.recovered&matches[:,:,None]).clone()

    @torch.no_grad()
    def update(self,*,wheel_pos_w,wheel_quat_w,course,direction_w,wheel_bottom_z_w,wheel_grounded,
               support_safe,touchdown_safe,collision,wheel_horizontal_radius,
               wheel_vertical_radius,wheel_thickness,required_clearance=.03,
               required_far_margin=.04,stable_frames=5,approach_distance=.25,
               autonomous_lift=None, cylinder_geometry=False,
               wheel_forces=None, robot_weight=None, attitude_safe=None):
        b=wheel_pos_w.shape[0];rows=torch.arange(b,device=self.device)
        mode = torch.zeros(b, device=self.device, dtype=torch.bool) if autonomous_lift is None else autonomous_lift
        if (not isinstance(mode, torch.Tensor) or mode.shape != (b,)
                or mode.dtype != torch.bool or mode.device != self.device):
            raise ValueError('autonomous_lift must be bool [B] on tracker device')
        mode_changed = self.mode_known & (mode != self.autonomous_mode)
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
        changed |= mode_changed
        if changed.any(): self.reset(changed)
        self.known_ids.copy_(ids)
        self.autonomous_mode.copy_(mode);self.mode_known[:]=True
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
        self.prelift_target_bottom[start]=float('nan')
        self.prelift_budget[start]=0
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
        # Freeze the target and maximum payable rise at the first measured
        # loaded reference. Lower recontacts must never replenish the budget.
        first_contact=contact_update&~torch.isfinite(self.prelift_target_bottom)
        target_bottom=selected_center[:,2]+float(required_clearance)
        self.prelift_target_bottom=torch.where(first_contact,target_bottom,
                                               self.prelift_target_bottom)
        self.prelift_budget=torch.where(first_contact,((target_bottom-bottom)/.02).clamp_min(0.),
                                        self.prelift_budget)
        self.last_contact_bottom=torch.where(contact_update,bottom,self.last_contact_bottom)
        observed_high_water=torch.where(torch.isfinite(self.prelift_bottom_high_water),
            torch.maximum(self.prelift_bottom_high_water,bottom),bottom)
        self.prelift_bottom_high_water=torch.where(contact_update,observed_high_water,
                                                   self.prelift_bottom_high_water)
        lifted=(~grounded & torch.isfinite(self.last_contact_bottom)
                & (bottom>=self.last_contact_bottom+.02))
        single_support = wheel_grounded.sum(-1) == 3
        self.early_lift |= enabled&before&lifted&single_support
        self.inner.failed |= enabled & ~mode & self.early_lift & ~grounded & ~single_support
        single_prelift = (enabled & before & lifted & (wheel_grounded.sum(-1) == 3)
                          & ~self.inner.failed & ~collision & ~self.prelift_rewarded)
        self.prelift_rewarded |= single_prelift
        overlap = (enabled & (local_pos[rows,selected,0]+wheel_horizontal_radius >= near)
            & (local_pos[rows,selected,0]-wheel_horizontal_radius <= hx[rows,slot])
            & (local_pos[rows,selected,1].abs() <= hy[rows,slot]+widths[rows,selected]))
        xy_witness=None
        if cylinder_geometry:
            from .m1_reference_geometry import cylinder_box_xy_witness
            xy_witness=cylinder_box_xy_witness(wheel_pos_w,wheel_quat_w,selected_center,
                extents[rows,slot],radius=wheel_vertical_radius,thickness=wheel_thickness)
            overlap &= xy_witness[rows,selected]
        # Observe flight without an arbitrary minimum rise. A wheel already
        # unloaded at encounter entry has no loaded reference; it still needs
        # the other three contacts, but cannot earn unmeasured height credit.
        observed_flight=(~grounded & torch.isfinite(bottom)
            & (~torch.isfinite(self.last_contact_bottom) | (bottom>self.last_contact_bottom)))
        self.flight_active = enabled & mode & ~grounded & (self.flight_active | observed_flight)
        self.crossing_started |= mode & overlap & ~self.inner.awaiting_recovery
        self.inner.failed |= enabled & mode & (
            ((self.flight_active | self.crossing_started) & ~grounded & ~single_support)
            | (overlap & grounded))
        bottom_clearance = bottom-selected_center[:,2]
        shape_clear=None
        if cylinder_geometry:
            from .m1_reference_geometry import cylinder_clears_box
            raised=selected_center.clone(); raised[:,2]+=float(required_clearance)
            # Empty flat-stage rows contain zero-sized padding, not a box.
            # Supply harmless positive placeholders only for disabled rows;
            # enabled geometry is still validated above and cannot be masked.
            shape_extents=torch.where(enabled[:,None],extents[rows,slot],torch.ones_like(extents[rows,slot]))
            shape_clear=cylinder_clears_box(wheel_pos_w,wheel_quat_w,raised,shape_extents,
                radius=wheel_vertical_radius,thickness=wheel_thickness)
        measured_clear=(bottom_clearance>=required_clearance) if shape_clear is None else shape_clear[rows,selected]
        # Every sampled overlap must clear the top, not merely one lucky frame.
        self.inner.failed |= overlap & (~torch.isfinite(bottom_clearance) | ~measured_clear)
        self.inner.failed |= enabled&~mode&~before&~self.early_lift
        fully_past=(local_pos[rows,selected,0]-wheel_horizontal_radius
                    >=hx[rows,slot]+required_far_margin)
        matches_lane=local_pos[rows,selected,1].abs()<=hy[rows,slot]+widths[rows,selected]
        # One valid edge sample is not permission to divert around the block
        # and rejoin on the far side using stale clearance evidence.
        self.inner.failed |= (enabled & mode & self.crossing_started & ~fully_past
                              & ~matches_lane & ~self.inner.awaiting_recovery)
        landing_phase=torch.where(mode,self.crossing_started,self.early_lift)
        self.inner.failed |= (enabled&landing_phase&grounded&~fully_past
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
        touchdown_eligible=torch.where(mode,
            self.crossing_started & grounded & wheel_grounded.all(-1),self.early_lift)
        out=self.inner.update(wheel_pos_w=local_pos,obstacle_centers_top_w=obstacle,
            support_safe=support_safe&enabled,touchdown_safe=touchdown_safe&enabled&touchdown_eligible&landing_free,
            collision=collision&enabled,wheel_horizontal_radius=wheel_horizontal_radius,
            wheel_vertical_radius=wheel_vertical_radius,wheel_lateral_half_width=widths,
            wheel_bottom_z_w=wheel_bottom_z_w,obstacle_half_extents=projected,
            required_clearance=required_clearance,required_far_margin=required_far_margin,
            stable_frames=stable_frames,approach_distance=approach_distance,clearance_safe=shape_clear,
            overlap_witness=xy_witness)
        # The inner tracker clears target_wheel on recovery. Preserve the
        # selected slot/wheel from before its update, and certify only after
        # its full consecutive nominal-support recovery gate passes.
        completed=enabled&out['recovery_complete']
        self.recovered[rows[completed],slot[completed],selected[completed]]=True
        self.crossing_count+=out['event_complete'].long()
        out['attempt_started']=start
        out['crossing_count']=self.crossing_count.clone()
        out['episode_complete']=torch.zeros_like(start)
        out['target_obstacle_id']=self.target_obstacle_id.clone()
        out['single_prelift_event']=single_prelift
        # Failed attempts stay counted, but must not suppress every later
        # encounter. Decide abandonment before rewarding this observation so
        # retreating outside the encounter cannot pay a final height increment.
        outside=(local_pos[rows,selected,0].abs()>hx[rows,slot]+wheel_horizontal_radius+approach_distance)
        outside |= local_pos[rows,selected,1].abs()>hy[rows,slot]+widths[rows,selected]+approach_distance
        abandoned=enabled&outside&~self.inner.awaiting_recovery
        out['failed'] |= abandoned
        # Reward newly measured rise before the obstacle, while retaining the
        # >=2cm event as telemetry (and a gate only for legacy-mode rows).
        # The world-bottom high-water mark survives bobbing and lower loaded
        # references. Loaded and unsafe motion advances it without reward. The
        # same 2cm units continue only up to the actual top+clearance target.
        progress_safe=(enabled & before & matches_lane & ~grounded & single_support
                       & ~out['failed'] & ~collision & torch.isfinite(bottom)
                       & torch.isfinite(self.last_contact_bottom)
                       & torch.isfinite(self.prelift_bottom_high_water)
                       & torch.isfinite(self.prelift_target_bottom))
        rewarded_bottom=torch.minimum(bottom,self.prelift_target_bottom)
        rise=((rewarded_bottom-self.prelift_bottom_high_water)/.02).clamp_min(0.)
        progress_delta=torch.minimum(rise,(self.prelift_budget-self.prelift_high_water).clamp_min(0.))
        out['prelift_progress_delta']=torch.where(progress_safe,progress_delta,
                                                 torch.zeros_like(progress_delta))
        self.prelift_high_water+=out['prelift_progress_delta']
        # An unsafe rise cannot become newly payable when support is restored
        # at the same height; only later, newly measured safe rise can earn.
        measured_before=enabled&before&torch.isfinite(bottom)
        self.prelift_bottom_high_water=torch.where(measured_before,
            observed_high_water,self.prelift_bottom_high_water)
        out['overlap_sample']=overlap & torch.isfinite(bottom_clearance)
        out['bottom_clearance']=torch.where(out['overlap_sample'], bottom_clearance,
                                           torch.full_like(bottom_clearance, float('nan')))
        if wheel_forces is not None:
            if robot_weight is None or attitude_safe is None:
                raise ValueError('load feedback needs actual weight and attitude gate')
            key=torch.where(enabled,self.target_obstacle_id*4+selected,-1)
            progress=((local_pos[rows,selected,0]-(near-wheel_horizontal_radius)) /
                (2*hx[rows,slot]+2*wheel_horizontal_radius+required_far_margin).clamp_min(1e-6))
            out.update(self.learning_progress.update(key=key,selected=selected,forces=wheel_forces,
                weight=robot_weight,active=mode&enabled,
                safe=attitude_safe&matches_lane&~out['failed']&~collision&(~overlap|measured_clear)
                    &(local_pos[rows,selected,1].abs()<hy[rows,slot]+widths[rows,selected]-1e-6),
                before=before,airborne=self.flight_active&single_support&self.crossing_started,progress=progress))
        released=out['recovery_complete'] | abandoned
        if released.any():
            self.inner.reset(released)
            self.slot[released]=-1;self.target_obstacle_id[released]=-1;self.early_lift[released]=False
            self.flight_active[released]=False;self.crossing_started[released]=False
            self.prelift_rewarded[released]=False
            self.prelift_high_water[released]=0
            self.last_contact_bottom[released]=float('nan')
            self.prelift_bottom_high_water[released]=float('nan')
            self.prelift_target_bottom[released]=float('nan')
            self.prelift_budget[released]=0
        return out
