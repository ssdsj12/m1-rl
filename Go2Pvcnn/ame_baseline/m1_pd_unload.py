"""Bounded PD-only diagnostic UNLOAD, not WBC or a crossing controller.

The caller owns episode lifetime, fresh physics stepping and fail-stop. Reuses
the prepared last executed reference, shortens one leg at <=1cm/s, <=2cm total.
Only measured contact/pose evidence may certify unloading. No fake allocation
validity or effort-error inputs are supplied to the distinct effort-owned gate.
"""
import math
import torch
from extension.parallelism.m1_kinematics import (
    m1_ik,m1_fk,m1_joint_limit_mask,M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES)
from .m1_unload_reference import unload_height
from .m1_ame_contract import M1_LEG_ACTION_SCALE_RAD


def tracking_diagnostics(*,reference_root,reference_rpy,live_root,live_rpy,
                         command,actual_joint,wheel):
    """Read-only decomposition, all [B,4,3] world-coordinate wheel deltas.

Uses the LAST EXECUTED command, never the about-to-be-issued proposal. Actual
native wheel positions minus analytic FK expose model/axis error separately.
The deltas add to wheel - nominal_command_fk, but are not causal dynamics proof.
"""
    nominal=m1_fk(reference_root,reference_rpy,command).foot_pos_w
    commanded=m1_fk(live_root,live_rpy,command).foot_pos_w
    actual=m1_fk(live_root,live_rpy,actual_joint).foot_pos_w
    return dict(nominal_command_fk=nominal,live_command_fk=commanded,
                actual_joint_fk=actual,pose_delta=commanded-nominal,
                joint_tracking_delta=actual-commanded,fk_error=wheel-actual)


def production_pd_valid(stiffness,damping,feedforward):
    if stiffness.ndim!=2 or stiffness.shape[1]!=16:
        raise ValueError('canonical16 native drive tensors required')
    if any(x.shape!=stiffness.shape or x.device!=stiffness.device for x in (damping,feedforward)):
        raise ValueError('aligned native drive tensors required')
    k=torch.full_like(stiffness,800.);d=torch.full_like(damping,40.)
    k[:,3::4]=0.;d[:,3::4]=5.
    return (torch.isfinite(stiffness).all(-1)&torch.isfinite(damping).all(-1)
        &torch.isfinite(feedforward).all(-1)&(stiffness==k).all(-1)
        &(damping==d).all(-1)&(feedforward==0).all(-1))


class M1PdUnloadController:
    def __init__(self,prepared,*,world_height=False):
        if type(world_height) is not bool:
            raise ValueError('world_height must be a bool diagnostic opt-in')
        if not prepared.ready.all() or prepared.failed.any():
            raise ValueError('all diagnostic rows must have fresh prepared evidence')
        for key in ('root','rpy','joint','anchors','selected','episode','obstacle'):
            setattr(self,key,getattr(prepared,key).clone())
        self.height=torch.zeros_like(self.root[:,0])
        self.last_step=torch.full_like(self.selected,-1)
        self.count=torch.zeros_like(self.selected)
        self.failed=torch.zeros_like(prepared.failed)
        self.ready=self.failed.clone()
        self.reason=torch.zeros_like(self.selected)
        self.world_height=world_height
        self.frame=dict(root=self.root.clone(),rpy=self.rpy.clone())
        self.entry_wheel=m1_fk(self.root,self.rpy,self.joint).foot_pos_w.detach()

    def update(self,*,observed,step,collision,actuator_ok,dt,advance_reference=True,
               live_root=None,live_rpy=None):
        if not math.isfinite(dt) or not 0<dt<=.02 or type(advance_reference) is not bool:
            raise ValueError('bounded control dt and bool reference ownership required')
        b=len(self.root)
        for x,dtype in ((step,torch.long),(collision,torch.bool),(actuator_ok,torch.bool)):
            if x.shape!=(b,) or x.dtype!=dtype or x.device!=self.root.device:
                raise ValueError('aligned per-row evidence required')
        for key,shape in (('force',(b,4)),('tilt',(b,2)),('tilt_rate',(b,2)),('margin',(b,))):
            if observed[key].shape!=shape or observed[key].device!=self.root.device:
                raise ValueError('invalid measured support layout')
        force=observed['force']
        selected=torch.arange(4,device=self.root.device)[None]==self.selected[:,None]
        selected_force=force.gather(1,self.selected[:,None]).squeeze(1)
        finite=observed['valid'].clone()
        for key in ('force','tilt','tilt_rate','margin'):
            finite &= torch.isfinite(observed[key]).reshape(b,-1).all(-1)
        finite &= (force>=0).all(-1)
        pose=(observed['tilt'].abs()<=.15).all(-1)&(observed['tilt_rate'].abs()<=.20).all(-1)
        support=((force>10.)|selected).all(-1)
        reserve=((force>=30.)|selected).all(-1)
        safe=finite&pose&support&(observed['margin']>=.02)&~collision
        fresh=(step>=0)&(step==self.last_step+1)
        within=(step<100)|((step==100)&(not advance_reference))
        reason=torch.zeros_like(self.reason)
        reason=torch.where(actuator_ok,reason,6)
        reason=torch.where(safe,reason,7)
        reason=torch.where(fresh,reason,8)
        reason=torch.where(within,reason,9)
        measured_ready=safe&reserve&(selected_force<=5.)&actuator_ok&fresh&within
        self.count=torch.where(measured_ready,self.count+1,0).clamp_max(5)
        candidate=self.height
        joint=self.joint
        frame=self.frame
        if advance_reference:
            proposal=unload_height(self.height,selected_force,dt,target_force=0.,min_contact_speed=.003)
            progress=reserve&safe&(selected_force>5.)&~self.failed
            candidate=torch.where(progress,proposal['height'],self.height)
            target=self.anchors.clone()
            target[torch.arange(b,device=self.root.device),self.selected,2]+=candidate
            q,reachable=m1_ik(self.root,self.rpy,target)
            q=q.reshape(b,12)
            # Keep exact last executed commands in held rows; don't introduce
            # another numerical IK projection while observing readiness.
            joint=torch.where(progress[:,None],q,self.joint)
            world_valid=torch.ones_like(safe)
            if self.world_height:
                if live_root is None or live_rpy is None:
                    raise ValueError('world height needs fresh measured root and rpy')
                from .m1_selected_world import selected_world_target
                corrected=selected_world_target(root=self.root,rpy=self.rpy,
                    live_root=live_root,live_rpy=live_rpy,target=target,
                    nominal=q,previous=self.joint,selected=self.selected,dt=dt,
                    previous_frame=self.frame,height_only=True)
                # On the fifth measured-ready frame the caller may hand off
                # without another action. Preserve the last executed command.
                correct=(self.count<5)&~self.failed
                joint=torch.where(correct[:,None],corrected['joint'],self.joint)
                frame={k:torch.where(correct[:,None],corrected['frame'][k],v)
                       for k,v in self.frame.items()}
                world_valid=~correct|corrected['valid']
            ref_ok=proposal['valid']&reachable.all(-1)&m1_joint_limit_mask(joint)&world_valid
            # This is the bounded 2cm UNLOAD diagnostic, NOT the obstacle LIFT
            # stage. Frame compensation may not silently expand its envelope.
            nominal_wheel=m1_fk(self.root,self.rpy,joint).foot_pos_w
            shortening=(nominal_wheel-self.entry_wheel)[torch.arange(b,device=self.root.device),self.selected,2]
            ref_ok &= shortening<=.02+1e-7
            ref_ok &= ((joint-self.joint).abs()<=.5*dt+1e-7).all(-1)
            reason=torch.where((reason==0)&~ref_ok,5,reason)
        self.reason=torch.where(self.failed,self.reason,reason)
        self.failed |= reason!=0
        accepted=~self.failed
        self.height=torch.where(accepted,candidate,self.height).detach()
        self.joint=torch.where(accepted[:,None],joint,self.joint).detach()
        self.frame={k:torch.where(accepted[:,None],frame[k],v).detach() for k,v in self.frame.items()}
        self.ready=(self.count>=5)&accepted
        self.last_step=step.clone()
        return dict(accepted=accepted.clone(),failed=self.failed.clone(),ready=self.ready.clone(),
                    reason=self.reason.clone(),height=self.height.clone(),joint=self.joint.clone())

    def position_action(self,default_asset_joint):
        if default_asset_joint.shape!=(len(self.root),16) or default_asset_joint.device!=self.root.device:
            raise ValueError('canonical16 defaults required')
        cols=[M1_ASSET_JOINT_NAMES.index(n) for n in M1_PLANNER_JOINT_NAMES]
        action=torch.zeros_like(default_asset_joint)
        action[:,cols]=(self.joint-default_asset_joint[:,cols])/M1_LEG_ACTION_SCALE_RAD
        eligible=~self.failed&torch.isfinite(action).all(-1)&(action.abs()<=1.).all(-1)
        return action,eligible

    def finish(self,*,step):
        fresh=(step==self.last_step)&(step>=0)
        bad=~fresh|~self.ready
        self.reason=torch.where(~self.failed&bad,torch.where(fresh,9,8),self.reason)
        self.failed |= bad
        self.ready &= ~self.failed
        return dict(ready=self.ready.clone(),failed=self.failed.clone(),reason=self.reason.clone())
