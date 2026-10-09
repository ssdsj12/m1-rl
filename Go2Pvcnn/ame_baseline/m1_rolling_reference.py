"""Measured forward-only reference transport for a bounded flat rolling probe.

Caller translates frozen root/anchors by shift, previous selected IK frame by
delta. No vertical/lateral error compensation or accumulated position command.
This is not a traction controller, obstacle planner or stability certificate.
"""
import math
import torch


def rolling_shift(origin,live,yaw,previous_progress,dt):
    if not math.isfinite(dt) or not 0<dt<=.1:
        raise ValueError('dt must be finite in (0,.1]')
    batch=origin.shape[0]
    for value,shape in ((origin,(batch,3)),(live,(batch,3)),(yaw,(batch,)),(previous_progress,(batch,))):
        if value.shape!=shape or value.device!=origin.device or not value.is_floating_point():
            raise ValueError('invalid rolling reference shape/device/type')
    heading=torch.stack((yaw.cos(),yaw.sin(),torch.zeros_like(yaw)),-1)
    displacement=live-origin
    progress=(displacement*heading).sum(-1)
    lateral=displacement[:,:2]-progress[:,None]*heading[:,:2]
    finite=torch.isfinite(origin).all(-1)&torch.isfinite(live).all(-1)&torch.isfinite(yaw)&torch.isfinite(previous_progress)
    valid=finite&(progress>=-.02)&(progress<=.5)&(lateral.norm(dim=-1)<=.025)
    valid &= (progress-previous_progress).abs()<=.6*dt
    return dict(shift=progress[:,None]*heading,delta=(progress-previous_progress)[:,None]*heading,
                progress=progress,valid=valid)
