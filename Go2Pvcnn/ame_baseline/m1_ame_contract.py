"""Tensor-only M1 action and observation contract."""
from __future__ import annotations

import torch
from math import atan2, sin, cos, isfinite
from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES,
    M1_WHEEL_RADIUS_M, M1_ABAD_LOWER, M1_ABAD_UPPER,
    M1_HIP_LOWER, M1_HIP_UPPER, M1_KNEE_LOWER, M1_KNEE_UPPER,
)
from extension.parallelism.rl_adapter import resolve_named_indices, select_named_joint_state

# The previous 0.25 rad envelope only raised the wheel centre by a few cm,
# so the learned policy could not clear even the small 3--6 cm obstacles.
# Keep the action head at 16 dimensions, but give hip/knee targets enough
# authority for the MPC teacher's 18--20 cm wheel-centre swing.  A 0.65 rad
# envelope clipped a reachable 0.20 m lift (about 0.91 rad at the knee) and
# made the teacher slide. Joint limits still bound the resulting target.
# Keep the policy head in [-1, 1] while retaining the full M1 IK target
# range; the previous 1.0 rad scale clipped the knee lift for 10 cm boxes.
M1_LEG_ACTION_SCALE_RAD = 1.50
# One wheel action unit requests 1 m/s at the tire. The 2 m/s cap includes
# headroom for the existing 1 m/s translation plus yaw command.
M1_WHEEL_ACTION_SCALE_RAD_S = 1.0 / M1_WHEEL_RADIUS_M
M1_WHEEL_SPEED_LIMIT_RAD_S = 2.0 / M1_WHEEL_RADIUS_M
# Center each wheel below its hip mount using the M1 0.26/0.28 m links.
# User-approved Climb reference: 585 mm TOTAL source-mesh height, not root Z.
# Joint angles are calibrated from this asset, not vendor-published presets.
# See scripts/audit_m1_standing_height.py for independent mesh FK verification.
_TRAIN_KNEE = 1.6824843873167417
_TRAIN_HIP = -atan2(.28 * sin(_TRAIN_KNEE), .26 + .28 * cos(_TRAIN_KNEE))
M1_TRAINING_JOINT_POS = (0., _TRAIN_HIP, _TRAIN_KNEE, 0.) * 4
# Ground the lowest collision mesh; the analytic tire differs by 0.21 mm.
M1_TRAINING_ROOT_Z_M = 0.45600081145762916


def m1_last_leg_action(env):
    if getattr(env.cfg, 'm1_fixed_wheel_speed_m_s', None) is not None:
        action = env.action_manager.action
        if action.shape[-1] != 12:
            raise ValueError('fixed-wheel policy must have 12 leg actions')
        return action
    return select_named_joint_state(
        env.action_manager.action,
        source_names=env.cfg.asset_joint_names,
        selected_names=M1_PLANNER_JOINT_NAMES,
    )


def m1_last_action(env):
    """M1 policy history includes all 12 leg and 4 wheel commands."""
    speed = getattr(env.cfg, 'm1_fixed_wheel_speed_m_s', None)
    if speed is not None:
        return expand_fixed_wheel_actions(env.action_manager.action, speed)
    return select_named_joint_state(
        env.action_manager.action,
        source_names=env.cfg.asset_joint_names,
        selected_names=M1_ASSET_JOINT_NAMES,
    )


def m1_wheel_surface_velocity(env):
    """Named wheel speeds in m/s; omit unbounded integrated wheel angles."""
    robot = env.scene["robot"]
    return select_named_joint_state(
        robot.data.joint_vel,
        source_names=tuple(robot.joint_names),
        selected_names=M1_WHEEL_JOINT_NAMES,
    ) * M1_WHEEL_RADIUS_M


def validate_fixed_wheel_speed(speed_m_s):
    speed = float(speed_m_s)
    if not isfinite(speed) or not 0.0 < speed <= 2.0:
        raise ValueError('fixed wheel surface speed must be finite and in (0, 2] m/s')
    return speed


def expand_fixed_wheel_actions(actions, speed_m_s=.30):
    """Executed 16-slot history/decoder input; never a PPO action distribution."""
    if actions.ndim != 2 or actions.shape[-1] != 12:
        raise ValueError('fixed-wheel policy actions must have shape [B,12]')
    speed = validate_fixed_wheel_speed(speed_m_s)
    legs = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    wheels = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES))
    executed = actions.new_zeros((actions.shape[0], 16))
    executed[:, legs] = actions
    executed[:, wheels] = speed / (M1_WHEEL_RADIUS_M * M1_WHEEL_ACTION_SCALE_RAD_S)
    return executed


def m1_action_targets(actions, default_joint_pos):
    """Interleaved leg position (rad) and wheel velocity (rad/s) targets."""
    if actions.shape[-1] != 16 or default_joint_pos.shape != actions.shape:
        raise ValueError("M1 actions/default_joint_pos must share shape [B,16]")
    legs = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    wheels = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES))
    lower = actions.new_tensor(tuple(v for triple in zip(M1_ABAD_LOWER, M1_HIP_LOWER, M1_KNEE_LOWER) for v in triple))
    upper = actions.new_tensor(tuple(v for triple in zip(M1_ABAD_UPPER, M1_HIP_UPPER, M1_KNEE_UPPER) for v in triple))
    targets = torch.empty_like(actions)
    targets[:, legs] = (default_joint_pos[:, legs] + M1_LEG_ACTION_SCALE_RAD * actions[:, legs]).clamp(lower, upper)
    targets[:, wheels] = (M1_WHEEL_ACTION_SCALE_RAD_S * actions[:, wheels]).clamp(-M1_WHEEL_SPEED_LIMIT_RAD_S, M1_WHEEL_SPEED_LIMIT_RAD_S)
    return targets
