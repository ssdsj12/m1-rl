"""Opt-in damped COM-offset reference; NOT a dynamic stability controller.

Controls reference acceleration only. Contact loads, IK, complete prepared-root
displacement and finite action deadline must still be checked by the caller.
Invalid proposals require recovery, not treating previous output as safe hold.
"""
import math
import torch


def root_step(entry,previous,velocity,target,*,dt,max_speed=.04):
    """Apply the existing bounded reference to fixed-entry world root XY."""
    if entry.ndim!=2 or entry.shape[-1]!=3:
        raise ValueError('root reference must be [B,3]')
    if any(x.shape!=entry.shape or x.dtype!=entry.dtype or x.device!=entry.device
           for x in (previous,target)):
        raise ValueError('root inputs must share shape, dtype, device')
    result=com_step(previous[:,:2]-entry[:,:2],velocity,target[:,:2]-entry[:,:2],dt=dt,max_speed=max_speed)
    valid=result['valid'] & torch.isfinite(entry).all(-1)
    valid &= torch.isfinite(previous).all(-1)&torch.isfinite(target).all(-1)
    valid &= (previous[:,2]-entry[:,2]).abs()<=1e-7
    valid &= (target[:,2]-entry[:,2]).abs()<=1e-7
    root=entry.clone()
    root[:,:2]+=result['position']
    return dict(root=torch.where(valid[:,None],root,previous),
                velocity=torch.where(valid[:,None],result['velocity'],velocity),valid=valid)


def com_step(position,velocity,target,*,dt,max_speed=.04):
    if not math.isfinite(dt) or not 0<dt<=.02:
        raise ValueError('dt must be in (0,.02]')
    if not math.isfinite(max_speed) or not 0<max_speed<=.04:
        raise ValueError('max_speed must be in (0,.04] m/s')
    if position.ndim!=2 or position.shape[-1]!=2:
        raise ValueError('COM offsets must be [B,2]')
    if any(x.shape!=position.shape or x.device!=position.device or x.dtype!=position.dtype
           for x in (velocity,target)) or not position.is_floating_point():
        raise ValueError('COM inputs must share floating shape, dtype, device')
    finite=(torch.isfinite(position)&torch.isfinite(velocity)&torch.isfinite(target)).all(-1)
    p=torch.where(finite[:,None],position,0.)
    v=torch.where(finite[:,None],velocity,0.)
    goal=torch.where(finite[:,None],target,0.)
    # Damped approach brakes as position error vanishes, rather than snapping
    # velocity to zero when the instantaneous load proposal stops changing.
    acceleration=36.*(goal-p)-12.*v
    acceleration*= (.05/acceleration.norm(dim=-1).clamp_min(1e-12)).clamp(max=1)[:,None]
    next_v=v+dt*acceleration
    next_v*= (max_speed/next_v.norm(dim=-1).clamp_min(1e-12)).clamp(max=1)[:,None]
    next_p=p+dt*next_v
    valid=finite & (velocity.norm(dim=-1)<=max_speed+1e-7)
    valid &= (position.norm(dim=-1)<=.08)&(target.norm(dim=-1)<=.08)&(next_p.norm(dim=-1)<=.08)
    return dict(position=torch.where(valid[:,None],next_p,position),
                velocity=torch.where(valid[:,None],next_v,velocity),valid=valid)
