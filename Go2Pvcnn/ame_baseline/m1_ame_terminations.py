"""M1-specific AME termination predicates."""

from __future__ import annotations

import torch


def nonfinite_robot_state(env, asset_cfg) -> torch.Tensor:
    """Mark environments whose articulation root or joint state contains NaN/Inf."""
    robot = env.scene[asset_cfg.name]
    states = (robot.data.root_state_w, robot.data.joint_pos, robot.data.joint_vel)

    invalid = torch.zeros(states[0].shape[0], dtype=torch.bool, device=states[0].device)
    for state in states:
        invalid |= ~torch.isfinite(state).reshape(state.shape[0], -1).all(dim=1)
    return invalid


__all__ = ["nonfinite_robot_state"]
