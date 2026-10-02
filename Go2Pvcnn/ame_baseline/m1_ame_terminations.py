"""M1-specific AME termination predicates."""

from __future__ import annotations

import torch
from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES
from extension.parallelism.rl_adapter import select_named_joint_state


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
        if state_name == "joint_pos":
            # Continuous wheel angles grow normally with distance travelled.
            invalid |= ~torch.isfinite(state).all(dim=-1)
            state = select_named_joint_state(state, source_names=robot.joint_names, selected_names=M1_PLANNER_JOINT_NAMES)
        valid = torch.isfinite(state) & (torch.abs(state) <= abs_limit)
        invalid |= ~valid.reshape(state.shape[0], -1).all(dim=1)
    return invalid


__all__ = ["nonfinite_robot_state"]
