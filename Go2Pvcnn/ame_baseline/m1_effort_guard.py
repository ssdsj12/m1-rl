"""Pure bounded feedforward proposal, not an actuator writer or recovery policy.

Caller supplies a name-resolved twelve-leg-joint mask in articulation order,
fresh PD estimate, and explicitly writes zeros on reset/rejection/exit. Returned
zero is an abort request, not proof that dropping feedforward preserves balance.
Implicit PD estimate is approximate: actual contact/pose guards remain required.
"""
import math
import torch


def position_pd_effort(next_position, position, next_velocity, velocity, stiffness, damping):
    """Estimate PD for the command being proposed, not last step's target."""
    values = (position, next_velocity, velocity, stiffness, damping)
    if any(x.shape != next_position.shape or x.device != next_position.device
           or x.dtype != next_position.dtype for x in values):
        raise ValueError('PD tensors must share shape/device/dtype')
    return stiffness * (next_position-position) + damping * (next_velocity-velocity)


def guarded_effort(*, target, previous, pd_effort, limits, leg_mask,
                   enabled, reset, dt):
    if not math.isfinite(dt) or not 0 < dt <= .1:
        raise ValueError('dt must be finite in (0,.1]')
    if target.ndim != 2 or target.shape[1] != 16 or not target.is_floating_point():
        raise ValueError('target must be floating [B,16]')
    batch = target.shape[0]
    for value in (previous, pd_effort, limits):
        if value.shape != target.shape or value.dtype != target.dtype or value.device != target.device:
            raise ValueError('dynamics tensors must share shape/dtype/device')
    for value, shape in ((leg_mask, (16,)), (enabled, (batch,)), (reset, (batch,))):
        if value.shape != shape or value.dtype != torch.bool or value.device != target.device:
            raise ValueError('invalid boolean mask')
    if int(leg_mask.sum()) != 12:
        raise ValueError('exactly twelve named leg joints required')
    finite = torch.ones(batch, dtype=torch.bool, device=target.device)
    for value in (target, previous, pd_effort, limits):
        finite &= torch.isfinite(value).all(-1)
    valid = finite & enabled & ~reset & (limits > 0).all(-1)
    valid &= (previous[:, ~leg_mask] == 0).all(-1)
    requested = torch.where(leg_mask[None], target, 0.)
    valid &= (requested.abs() <= limits).all(-1)
    valid &= (previous.abs() <= limits).all(-1)
    # Rate limit changes, not an out-of-range requested torque. Above limits
    # are rejected rather than silently clipped into a different equilibrium.
    candidate = previous + (requested - previous).clamp(-20.*dt, 20.*dt)
    candidate = torch.where(leg_mask[None], candidate, 0.)
    valid &= ((pd_effort + candidate).abs() <= limits).all(-1)
    return dict(effort=torch.where(valid[:, None], candidate, 0.), valid=valid)
