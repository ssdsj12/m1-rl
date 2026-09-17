"""M1-specific AME termination predicates."""

from __future__ import annotations

import torch


_STATE_ABS_LIMITS = (
    ("root_state_w", 1.0e3),
    ("body_state_w", 1.0e3),
    ("joint_pos", 1.0e2),
    ("joint_vel", 1.0e3),
    ("joint_acc", 1.0e5),
    ("applied_torque", 1.0e4),
)


def nonfinite_robot_state(env, asset_cfg) -> torch.Tensor:
    """Mark environments with non-finite or numerically exploded articulation state."""
    robot = env.scene[asset_cfg.name]
    first_state = robot.data.root_state_w

    invalid = torch.zeros(first_state.shape[0], dtype=torch.bool, device=first_state.device)
    for state_name, abs_limit in _STATE_ABS_LIMITS:
        state = getattr(robot.data, state_name)
        valid = torch.isfinite(state) & (torch.abs(state) <= abs_limit)
        invalid |= ~valid.reshape(state.shape[0], -1).all(dim=1)
    return invalid


__all__ = ["nonfinite_robot_state"]
