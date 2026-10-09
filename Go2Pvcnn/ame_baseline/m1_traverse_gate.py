"""Conservative measured wheel-envelope gate for an aligned box corridor.

All distances are world metres projected onto the same forward corridor axis.
Caller owns obstacle/episode identity, fresh evidence, early-lift verification,
deadline, collision latch and landing-region/corridor validity. `radius` must
bound the actual wheel collision envelope in horizontal AND vertical direction,
not a commanded foot height. This gate has no success counter and does not prove
stability, support friction, swept collision freedom or completed crossing.
It must not be used for arbitrary shapes without a conservative bounding box.
"""
import torch


def traverse_gate(*,wheel_x,wheel_z,radius,near,far,top,support_safe,
                  collision,evidence_fresh,landing_available):
    if wheel_x.ndim!=1 or not wheel_x.is_floating_point():
        raise ValueError('wheel_x must be floating [B]')
    values=(wheel_x,wheel_z,radius,near,far,top)
    flags=(support_safe,collision,evidence_fresh,landing_available)
    if any(x.shape!=wheel_x.shape or x.device!=wheel_x.device
           or not x.is_floating_point() for x in values):
        raise ValueError('geometry must be floating [B] on the same device')
    if any(x.shape!=wheel_x.shape or x.device!=wheel_x.device
           or x.dtype!=torch.bool for x in flags):
        raise ValueError('evidence flags must be bool [B] on the same device')
    valid=torch.stack([torch.isfinite(x) for x in values]).all(0)
    valid &= (radius>0)&(far>near)
    safe=valid&support_safe&evidence_fresh&landing_available&~collision
    clearance=wheel_z-radius-top
    far_margin=wheel_x-radius-far
    beyond=far_margin>=.04
    return dict(advance=safe&~beyond&(clearance>=.05),
                land=safe&beyond,valid=valid,clearance=clearance,
                far_margin=far_margin,before_near=wheel_x+radius<near)
