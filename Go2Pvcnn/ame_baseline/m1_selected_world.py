"""Diagnostic selected-leg frame correction, no stance/effort ownership.

Caller supplies freshly measured pose and owns contact/pose/phase guards.
Nominal nine stance joints are never modified. Interpolating the IK frame
backtracks correction under joint slew; scale<1 is not exact world tracking.
"""
import math
import torch
from extension.parallelism.m1_kinematics import m1_ik, m1_fk, m1_joint_limit_mask


def selected_world_target(*, root, rpy, live_root, live_rpy, target,
                          nominal, previous, selected, dt, previous_frame=None, vertical_only=False,
                          height_only=False,height_mask=None):
    if vertical_only and height_only:
        raise ValueError('select only one height correction mode')
    if not math.isfinite(dt) or not 0 < dt <= .1:
        raise ValueError('dt must be in (0,.1]')
    batch=root.shape[0]
    if height_mask is not None and (not height_only or height_mask.shape!=(batch,)
            or height_mask.dtype!=torch.bool or height_mask.device!=root.device):
        raise ValueError('height mask requires bool [B] in height-only mode')
    values=((root,(batch,3)),(rpy,(batch,3)),(live_root,(batch,3)),
            (live_rpy,(batch,3)),(target,(batch,4,3)),
            (nominal,(batch,12)),(previous,(batch,12)))
    if any(x.shape!=shape or x.device!=root.device or x.dtype!=root.dtype
           or not x.is_floating_point() for x,shape in values):
        raise ValueError('invalid floating tensor layout')
    if selected.shape!=(batch,) or selected.dtype!=torch.long or selected.device!=root.device:
        raise ValueError('selected must be long [B]')
    finite=torch.ones(batch,dtype=torch.bool,device=root.device)
    for x,_ in values:
        finite &= torch.isfinite(x).reshape(batch,-1).all(-1)
    dr=live_root-root
    da=torch.atan2(torch.sin(live_rpy-rpy),torch.cos(live_rpy-rpy))
    safe=finite & (selected>=0) & (selected<4) & (dr.norm(dim=-1)<=.025) & (da.abs()<=.08).all(-1)
    old_root,old_rpy=root,rpy
    if previous_frame is not None:
        if set(previous_frame)!= {'root','rpy'}:
            raise ValueError('previous_frame requires root and rpy')
        old_root,old_rpy=previous_frame['root'],previous_frame['rpy']
        if any(v.shape!=root.shape or v.dtype!=root.dtype or v.device!=root.device for v in (old_root,old_rpy)):
            raise ValueError('invalid previous frame layout')
        safe &= torch.isfinite(old_root).all(-1) & torch.isfinite(old_rpy).all(-1)
        safe &= ((old_root-root).norm(dim=-1)<=.025)
        old_angle=torch.atan2(torch.sin(old_rpy-rpy),torch.cos(old_rpy-rpy))
        safe &= (old_angle.abs()<=.08).all(-1)
    frame_root,frame_rpy=old_root.clone(),old_rpy.clone()
    desired_root,desired_rpy=live_root,live_rpy
    if vertical_only:
        desired_root=root.clone()
        desired_root[:,2]=live_root[:,2]
        desired_rpy=rpy
    if height_only:
        desired_root=root.clone()
        desired_root[:,2]=live_root[:,2]
        zero=torch.zeros_like(root)
        nominal_body=m1_fk(zero,zero,nominal).foot_pos_w
        # ZYX rotation's world-Z row. Avoid near-horizontal body-Z axes.
        safe &= (live_rpy[:,0].cos()*live_rpy[:,1].cos()).abs()>.5
        if height_mask is not None:
            desired_rpy=torch.where(height_mask[:,None],live_rpy,rpy)
    advance_angle=torch.atan2(torch.sin(desired_rpy-old_rpy),torch.cos(desired_rpy-old_rpy))
    mask=(torch.arange(12,device=root.device)[None]//3)==selected[:,None]
    joint=previous.clone(); found=torch.zeros_like(safe)
    scale_out=torch.zeros(batch,device=root.device,dtype=root.dtype)
    for scale in (1.,.5,.25,.125,.0625):
        trial_root=old_root+scale*(desired_root-old_root)
        trial_rpy=old_rpy+scale*advance_angle
        if height_only:
            body_target=nominal_body.clone()
            cr,sr=trial_rpy[:,0].cos(),trial_rpy[:,0].sin()
            cp,sp=trial_rpy[:,1].cos(),trial_rpy[:,1].sin()
            vertical_axis=cp*cr
            safe_axis=vertical_axis.abs()>.5
            denominator=torch.where(safe_axis,vertical_axis,torch.ones_like(vertical_axis))
            body_target[:,:,2]=(target[:,:,2]-trial_root[:,None,2]
                +sp[:,None]*body_target[:,:,0]-cp[:,None]*sr[:,None]*body_target[:,:,1])/denominator[:,None]
            q,reach=m1_ik(zero,zero,body_target)
            reach &= safe_axis[:,None]
            if height_mask is not None:
                vertical_q,vertical_reach=m1_ik(trial_root,trial_rpy,target)
                q=torch.where(height_mask[:,None,None],q,vertical_q)
                reach=torch.where(height_mask[:,None],reach,vertical_reach)
        else:
            q,reach=m1_ik(trial_root,trial_rpy,target)
        candidate=torch.where(mask,q.reshape(batch,12),nominal)
        reachable=reach.gather(1,selected.clamp(0,3)[:,None]).squeeze(1)
        limits=m1_joint_limit_mask(candidate) & m1_joint_limit_mask(previous)
        max_delta, max_joint=(candidate-previous).abs().max(-1)
        slew=max_delta<=.5*dt+1e-7
        if scale == 1.:
            full=dict(safe=safe.clone(),reachable=reachable,limits=limits,
                      slew=slew,max_delta=max_delta,max_joint=max_joint,
                      root_error=dr,angle_error=da,previous_root_error=old_root-root,
                      previous_angle_error=torch.atan2(torch.sin(old_rpy-rpy),torch.cos(old_rpy-rpy)))
        ok=safe & reachable & limits & slew
        use=ok & ~found
        joint=torch.where(use[:,None],candidate,joint)
        scale_out=torch.where(use,scale,scale_out)
        frame_root=torch.where(use[:,None],trial_root,frame_root)
        frame_rpy=torch.where(use[:,None],trial_rpy,frame_rpy)
        found |= ok
    return dict(joint=joint,valid=found,scale=scale_out,full=full,
                frame=dict(root=frame_root,rpy=frame_rpy))
