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


def required_crossing_reward(reward, step_terms, dt, *, blocked, collision,
                             done, prelift, recovery, prelift_progress_delta=None):
    """Strip positive shaping in a required-crossing zone, preserve all costs.

    Isaac RewardManager._step_reward holds weighted reward rates, whereas
    reward is their dt integral. Event bonuses are discrete, NOT dt-scaled.
    Prelift progress is a normalized high-water increment from the physical
    encounter tracker, capped there at one per encounter. The >=2cm prelift
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
            prelift_progress_delta.clamp(0.,1.),torch.zeros_like(prelift_progress_delta)).to(reward.dtype)
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
