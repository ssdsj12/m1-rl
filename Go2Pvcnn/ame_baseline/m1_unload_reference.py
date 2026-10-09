"""Bounded selected-contact admittance proposal; caller verifies IK/support."""
import math
import torch


def unload_height(height, selected_force, dt, effort_settled=None, target_force=5., min_contact_speed=0.):
    # Tracking target is distinct from the caller's measured <=5 N gate.
    if not math.isfinite(target_force) or not 0 <= target_force <= 5:
        raise ValueError('target_force must be finite in [0,5]')
    if not math.isfinite(min_contact_speed) or not 0 <= min_contact_speed <= .01:
        raise ValueError('min_contact_speed must be finite in [0,.01]')
    if not math.isfinite(dt) or not 0 < dt <= .1:
        raise ValueError('dt must be finite in (0,.1]')
    if (height.ndim != 1 or selected_force.shape != height.shape
            or selected_force.device != height.device or selected_force.dtype != height.dtype
            or not height.is_floating_point()):
        raise ValueError('height and force must share floating [B] layout')
    valid = torch.isfinite(height) & torch.isfinite(selected_force)
    valid &= (height >= 0) & (height <= .02) & (selected_force >= 0)
    speed = ((selected_force-target_force).clamp_min(0.) * .0002).clamp_max(.01)
    speed = torch.where(selected_force > target_force, speed.clamp_min(min_contact_speed), torch.zeros_like(speed))
    proposed = (height + speed*dt).clamp_max(.02)
    if effort_settled is not None:
        if effort_settled.shape != height.shape or effort_settled.dtype != torch.bool or effort_settled.device != height.device:
            raise ValueError('effort_settled must be bool [B] on input device')
        proposed = torch.where(effort_settled, proposed, height)
    return dict(height=torch.where(valid, proposed, height), valid=valid,
                at_limit=valid & (proposed >= .02) & (selected_force > 5.))
