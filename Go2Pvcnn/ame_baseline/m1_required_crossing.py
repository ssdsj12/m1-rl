"""Reward-only crossing contract. Never changes actions or success counters."""
from __future__ import annotations
import torch


def required_crossing_zone(root_pos, course):
    """World-X route slab; lateral bypass cannot turn the reward gate off.

    The .9m half-window covers the M1 front/rear wheel offsets plus lookahead.
    Only progressive, world-X courses consume this mask. Mixed terrain keeps
    free lateral avoidance. Empty flat stage has no valid obstacles.
    """
    dx = (root_pos[:, None, 0] - course['centers_top'][..., 0]).abs()
    return (course['valid'] & (dx <= course['half_extents'][..., 0] + .9)).any(-1)


def progressive_required_wheels(course, route_y):
    """Authored straight-route wheel lanes, NOT the drifting policy's lanes.

    M1 support order is FBL/FAR/RBL/RAR. Both front and rear wheels on the
    obstacle's side must earn separate strict recovery receipts. This helper
    is scoped to the flat-first world-X rows, not freely routed mixed terrain.
    """
    tracks = route_y[:, None] + route_y.new_tensor([.215, -.215, .215, -.215])
    distance = (course['centers_top'][..., 1, None] - tracks[:, None]).abs()
    required = course['valid'][..., None] & (distance <= course['half_extents'][..., 1, None] + .02325)
    if (course['valid'] & ~required.any(-1)).any():
        raise ValueError('progressive obstacle has no authored M1 wheel track')
    return required


class RequiredCrossingRewardGate:
    """Keep an episode obligation after bypass/retreat until strict recovery.

    Receipts must already be identity-aligned by EncounterCrossingTracker.
    Attempts and first touchdowns are not accepted as completion. No control
    or success counter is modified; this only gates positive reward shaping.
    """
    def __init__(self, num_envs, capacity, device):
        self.started = torch.zeros(num_envs, capacity, dtype=torch.bool, device=device)
        self.ids = torch.full((num_envs, capacity), -2, dtype=torch.long, device=device)

    def reset(self, rows):
        self.started[rows] = False
        self.ids[rows] = -2

    @torch.no_grad()
    def update(self, root_pos, course, required_wheels, recovered):
        if required_wheels.shape != (*self.started.shape, 4) or recovered.shape != required_wheels.shape:
            raise ValueError('required/recovered wheels must be bool [B,C,4]')
        if required_wheels.dtype != torch.bool or recovered.dtype != torch.bool:
            raise ValueError('required/recovered wheels must be bool [B,C,4]')
        changed = (self.ids != course['ids']).any(-1)
        self.started[changed] = False
        self.ids.copy_(course['ids'])
        near = course['centers_top'][..., 0] - course['half_extents'][..., 0] - .9
        self.started |= course['valid'] & (root_pos[:, None, 0] >= near)
        complete = required_wheels.any(-1) & (recovered | ~required_wheels).all(-1)
        return (self.started & course['valid'] & ~complete).any(-1)


def required_crossing_reward(reward, step_terms, dt, *, blocked, collision,
                             done, prelift, recovery, prelift_progress_delta=None):
    """Strip positive shaping in a required-crossing zone, preserve all costs.

    Isaac RewardManager._step_reward holds weighted reward rates, whereas
    reward is their dt integral. Event bonuses are discrete, NOT dt-scaled.
    Prelift progress is a measured high-water increment in 2cm units from the
    physical tracker, capped there at obstacle top+clearance. The >=2cm prelift
    event remains telemetry and is not added again. Legacy callers without
    progress retain their one-shot event API. Recovery remains a single pulse.
    Reset poses and collision frames never grant bonuses. Flat locomotion is unchanged.
    """
    if dt <= 0:
        raise ValueError('reward dt must be positive')
    removed = torch.where(blocked | collision,
        step_terms.clamp_min(0).sum(-1) * dt, torch.zeros_like(reward))
    safe = ~collision & ~done
    if prelift_progress_delta is None:
        progress = prelift.to(reward.dtype)
    else:
        progress = torch.where(torch.isfinite(prelift_progress_delta),
            prelift_progress_delta.clamp_min(0.),torch.zeros_like(prelift_progress_delta)).to(reward.dtype)
    bonus = safe.to(reward.dtype) * (.3 * progress * blocked.to(reward.dtype) + 2. * recovery.to(reward.dtype))
    return reward - removed + bonus, removed, bonus


def aggregate_metric(key, values):
    """Iteration aggregation: preserve worst measured clearance and counts."""
    if key == 'RequiredCrossing/min_bottom_clearance_m':
        finite=values[torch.isfinite(values)]
        return finite.min() if finite.numel() else values.new_tensor(float('nan'))
    if key in {'RequiredCrossing/clearance_samples', 'RequiredCrossing/prelift_events',
               'RequiredCrossing/stable_landings', 'RequiredCrossing/collision_frames'}:
        return values.sum()
    return values.mean()
