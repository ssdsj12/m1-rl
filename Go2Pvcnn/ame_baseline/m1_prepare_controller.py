"""Per-environment PREPARE owner for the M1 leg-position execution path.

Reuses measured COM transfer and the five-frame gate. Returned root is an IK
reference, NEVER a simulation-state write. This stage keeps four wheel anchors
on the ground. It cannot authorize lift: measured UNLOAD and the actuator-effort
contract are separate subsequent stages. Failed rows require caller fail-stop or
verified recovery; the held output is not a certified recovery controller.
"""
import torch
from .m1_load_transfer import transfer_target
from .m1_prepare_gate import PrepareGate
from .m1_com_trajectory import root_step
from extension.parallelism.m1_kinematics import m1_ik,m1_joint_limit_mask


class M1PrepareController:
    def __init__(self, *, root, rpy, joint, anchors, selected, episode, obstacle,
                 total_weight, timeout_steps=200):
        if type(timeout_steps) is not int or timeout_steps < 5:
            raise ValueError('timeout_steps must allow five measured frames')
        if root.ndim != 2 or root.shape[1] != 3 or not root.is_floating_point():
            raise ValueError('root must be floating [B,3]')
        b = len(root)
        self.entry = torch.zeros_like(root)
        self.rpy = torch.zeros_like(root)
        self.root = torch.zeros_like(root)
        self.joint = torch.zeros((b,12),device=root.device,dtype=root.dtype)
        self.anchors = torch.zeros((b,4,3),device=root.device,dtype=root.dtype)
        self.selected = torch.zeros(b,device=root.device,dtype=torch.long)
        self.episode = self.selected.clone()
        self.obstacle = self.selected.clone()
        self.last_step = torch.full_like(self.selected,-1)
        self.elapsed = torch.zeros_like(self.selected)
        self.velocity = torch.zeros((b,2),device=root.device,dtype=root.dtype)
        self.ready = torch.zeros(b,device=root.device,dtype=torch.bool)
        self.failed = torch.zeros(b,device=root.device,dtype=torch.bool)
        self.reason = torch.zeros_like(self.selected)
        self.gate = PrepareGate(b,root.device)
        if (total_weight.shape != (b,) or total_weight.device != root.device
                or not torch.isfinite(total_weight).all() or (total_weight<105.).any()):
            raise ValueError('finite physical total weight [B] in N required')
        self.weight = total_weight.to(root).clone()
        self.timeout_steps = timeout_steps
        self.reset_rows(torch.arange(b,device=root.device),root=root,rpy=rpy,joint=joint,
                        anchors=anchors,selected=selected,episode=episode,obstacle=obstacle)

    def reset_rows(self, rows, *, root, rpy, joint, anchors, selected, episode, obstacle):
        if (rows.ndim != 1 or rows.dtype != torch.long or rows.device != self.root.device
                or len(rows.unique())!=len(rows) or (rows<0).any() or (rows>=len(self.root)).any()):
            raise ValueError('unique in-range row ids required')
        n=len(rows)
        for x,shape in ((root,(n,3)),(rpy,(n,3)),(joint,(n,12)),(anchors,(n,4,3))):
            if x.shape!=shape or x.device!=self.root.device or x.dtype!=self.root.dtype or not torch.isfinite(x).all():
                raise ValueError('finite aligned entry tensors required')
        for x in (selected,episode,obstacle):
            if x.shape!=(n,) or x.dtype!=torch.long or x.device!=self.root.device or (x<0).any():
                raise ValueError('nonnegative integer event identities required')
        if (selected>3).any():
            raise ValueError('selected M1 leg must be0..3')
        self.entry[rows]=root.clone(); self.root[rows]=root.clone()
        self.rpy[rows]=rpy.clone(); self.joint[rows]=joint.clone()
        self.anchors[rows]=anchors.clone(); self.selected[rows]=selected.clone()
        self.episode[rows]=episode.clone(); self.obstacle[rows]=obstacle.clone()
        self.last_step[rows]=-1; self.elapsed[rows]=0
        self.velocity[rows]=0.; self.ready[rows]=False
        self.failed[rows]=False; self.reason[rows]=0
        for value in (self.gate.episode,self.gate.obstacle,self.gate.leg,self.gate.step):
            value[rows]=-1
        self.gate.count[rows]=0; self.gate.poisoned[rows]=False

    def update(self, *, observed, live_root, collision, step, dt, advance_reference=True):
        """Consume one fresh frame; final observation must not propose a new action."""
        if type(advance_reference) is not bool:
            raise ValueError('advance_reference must be a bool')
        b=len(self.root)
        for x,dtype in ((collision,torch.bool),(step,torch.long)):
            if x.shape!=(b,) or x.dtype!=dtype or x.device!=self.root.device:
                raise ValueError('step/collision must be aligned per-environment evidence')
        fresh=(step>=0)&((self.last_step<0)|(step==self.last_step+1))
        finite=(torch.isfinite(observed['force']).all(-1)
                & torch.isfinite(observed['tilt']).all(-1)
                & torch.isfinite(observed['tilt_rate']).all(-1))
        safe=(finite & observed['valid'] & ~collision
              & (observed['force']>10.).all(-1)
              & (observed['tilt'].abs()<=.30).all(-1))
        proposal=transfer_target(entry_root=self.entry,entry_rpy=self.rpy,
            anchor_w=self.anchors,support_w=observed['wheel_pos_w'],live_root=live_root,
            live_com=observed['com_w'],selected_leg=self.selected,
            previous_root=self.root,previous_joint=self.joint,dt=dt,
            root_speed=.04,max_root_shift=.08,total_weight=self.weight,support_floor=35.)
        if advance_reference:
            ramp=root_step(self.entry,self.root,self.velocity,proposal['desired_root'],
                           dt=dt,max_speed=.04)
            joint,reachable=m1_ik(ramp['root'],self.rpy,self.anchors)
            joint=joint.reshape(b,12)
            reference_valid=(ramp['valid'] & reachable.all(-1) & m1_joint_limit_mask(joint)
                             & ((joint-self.joint).abs()<=.5*dt+1e-7).all(-1))
        else:
            # Keep the command actually sent before this measured frame. In
            # particular, do not brake a virtual extra step before handoff.
            ramp=dict(root=self.root,velocity=self.velocity)
            joint=self.joint
            reference_valid=torch.isfinite(joint).all(-1)&m1_joint_limit_mask(joint)
        settled=ramp['velocity'].norm(dim=-1)<=.001
        reason=proposal['reason'].clone()
        reason=torch.where(reference_valid,reason,torch.full_like(reason,5))
        reason=torch.where(safe,reason,torch.full_like(reason,7))
        reason=torch.where(fresh,reason,torch.full_like(reason,8))
        reason=torch.where(self.elapsed<self.timeout_steps,reason,torch.full_like(reason,9))
        self.reason=torch.where(self.failed,self.reason,reason)
        self.failed |= reason!=0
        accepted=~self.failed
        ready=self.gate.update(episode=self.episode,obstacle=self.obstacle,leg=self.selected,
            step=step,force=observed['force'],tilt=observed['tilt'],
            tilt_rate=observed['tilt_rate'],margin=observed['margin'],
            ik_valid=accepted&proposal['post_lift_load_ready']&settled,collision=collision|self.failed)
        self.root=torch.where(accepted[:,None],ramp['root'],self.root).detach()
        self.joint=torch.where(accepted[:,None],joint,self.joint).detach()
        self.velocity=torch.where(accepted[:,None],ramp['velocity'],self.velocity).detach()
        self.ready=ready&accepted
        self.elapsed+=fresh.long()
        self.last_step=step.clone()
        return dict(root=self.root.clone(),joint=self.joint.clone(),accepted=accepted.clone(),
                    ready=self.ready.clone(),failed=self.failed.clone(),reason=self.reason.clone(),
                    post_lift_load_ready=proposal['post_lift_load_ready']&accepted,
                    lift_authorized=torch.zeros_like(ready))

    def position_action(self, default_asset_joint):
        """Encode exact12leg targets and zero wheel speed; caller must gate eligibility."""
        from .m1_ame_contract import M1_LEG_ACTION_SCALE_RAD
        from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES
        cols=[M1_ASSET_JOINT_NAMES.index(name) for name in M1_PLANNER_JOINT_NAMES]
        if (default_asset_joint.shape!=(len(self.root),16)
                or default_asset_joint.device!=self.root.device
                or default_asset_joint.dtype!=self.root.dtype
                or not torch.isfinite(default_asset_joint).all()):
            raise ValueError('finite canonical M1 default joints [B,16] required')
        action=torch.zeros_like(default_asset_joint)
        action[:,cols]=(self.joint-default_asset_joint[:,cols])/M1_LEG_ACTION_SCALE_RAD
        eligible=(~self.failed & torch.isfinite(action).all(-1) & (action.abs()<=1.).all(-1))
        return action,eligible

    def finish(self, *, step):
        """Bounded test/caller closure after its final fresh measured update."""
        if step.shape!=self.last_step.shape or step.dtype!=torch.long or step.device!=self.root.device:
            raise ValueError('final evidence clock must match controller rows')
        fresh=(step>=0)&(step==self.last_step)
        bad=~fresh|~self.ready
        self.reason=torch.where(~self.failed&bad,torch.where(fresh,9,8),self.reason)
        self.failed |= bad
        self.ready &= ~self.failed
        return dict(ready=self.ready.clone(),failed=self.failed.clone(),reason=self.reason.clone())
