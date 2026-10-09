"""Joint-rate-limited Cartesian motion without post-IK joint distortion."""
from __future__ import annotations

import torch

from extension.parallelism.m1_kinematics import m1_fk, m1_ik


def cartesian_joint_step(root_pos, root_rpy, current_q, target_w, lower, upper, max_step):
    """Return [B,4,3] joints and per-leg *full target* validity.

    Rate limiting interpolates the Cartesian segment, not each joint
    independently. Unreachable endpoints stay invalid even if an intermediate
    point is reachable. Bounds include the downstream action decoder range.
    """
    current = current_q.reshape(-1, 4, 3)
    origin = m1_fk(root_pos, root_rpy, current_q.reshape(-1, 12)).foot_pos_w
    goal_q, goal_valid = m1_ik(root_pos, root_rpy, target_w)
    goal_valid = (goal_valid & torch.isfinite(goal_q).all(-1)
                  & (goal_q >= lower).all(-1) & (goal_q <= upper).all(-1)
                  & torch.isfinite(current).all(-1))
    direct = goal_valid & ((goal_q - current).abs() <= max_step).all(-1)
    lo = torch.zeros_like(goal_valid, dtype=current.dtype)
    hi = torch.ones_like(lo)
    result = current.clone()
    # Each leg has its own progress fraction, but coordinated hip/knee IK.
    for _ in range(16):
        fraction = (lo + hi) * 0.5
        point = origin + fraction.unsqueeze(-1) * (target_w - origin)
        candidate, reachable = m1_ik(root_pos, root_rpy, point)
        feasible = (reachable & torch.isfinite(candidate).all(-1)
                    & (candidate >= lower).all(-1) & (candidate <= upper).all(-1)
                    & ((candidate - current).abs() <= max_step).all(-1)
                    & goal_valid)
        result = torch.where(feasible.unsqueeze(-1), candidate, result)
        lo = torch.where(feasible, fraction, lo)
        hi = torch.where(feasible, hi, fraction)
    result = torch.where(direct.unsqueeze(-1), goal_q, result)
    return result, goal_valid
