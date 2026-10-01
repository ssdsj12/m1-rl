"""M1-specific AME reward terms with explicit planner/wheel joint selection."""

from __future__ import annotations

import torch
from torch import Tensor

from extension.parallelism.m1_kinematics import (
    M1_ABAD_LOWER,
    M1_ABAD_UPPER,
    M1_ASSET_JOINT_NAMES,
    M1_HIP_LOWER,
    M1_HIP_UPPER,
    M1_KNEE_LOWER,
    M1_KNEE_UPPER,
    M1_PLANNER_JOINT_NAMES,
    M1_WHEEL_JOINT_NAMES,
    M1_WHEEL_RADIUS_M,
    M1_WHEEL_HORIZONTAL_ENVELOPE_M,
)
from extension.parallelism.rl_adapter import resolve_named_indices, select_named_joint_state


_WHEEL_SQUARED_MOTION_SCALE = M1_WHEEL_RADIUS_M**2
M1_SUPPORT_BODY_NAMES = tuple(name.replace("_JOINT", "_LINK") for name in M1_WHEEL_JOINT_NAMES)
_PLANNER_LOWER = tuple(
    value
    for values in zip(M1_ABAD_LOWER, M1_HIP_LOWER, M1_KNEE_LOWER)
    for value in values
)
_PLANNER_UPPER = tuple(
    value
    for values in zip(M1_ABAD_UPPER, M1_HIP_UPPER, M1_KNEE_UPPER)
    for value in values
)


def _robot(env, asset_cfg=None):
    return env.scene[getattr(asset_cfg, "name", "robot")]


def _select(values: Tensor, source_names, selected_names) -> Tensor:
    return select_named_joint_state(
        values,
        source_names=tuple(source_names),
        selected_names=tuple(selected_names),
    )


def _split_squared_motion(values: Tensor, source_names) -> Tensor:
    planner = _select(values, source_names, M1_PLANNER_JOINT_NAMES)
    wheels = _select(values, source_names, M1_WHEEL_JOINT_NAMES)
    return planner.square().sum(dim=-1) + _WHEEL_SQUARED_MOTION_SCALE * wheels.square().sum(dim=-1)


def m1_joint_vel_l2(env, asset_cfg=None) -> Tensor:
    robot = _robot(env, asset_cfg)
    return _split_squared_motion(robot.data.joint_vel, robot.joint_names)


def m1_joint_acc_l2(env, asset_cfg=None) -> Tensor:
    robot = _robot(env, asset_cfg)
    return _split_squared_motion(robot.data.joint_acc, robot.joint_names)


def m1_joint_torques_l2(env, asset_cfg=None) -> Tensor:
    robot = _robot(env, asset_cfg)
    planner = _select(robot.data.applied_torque, robot.joint_names, M1_PLANNER_JOINT_NAMES)
    wheels = _select(robot.data.applied_torque, robot.joint_names, M1_WHEEL_JOINT_NAMES)
    return planner.square().sum(dim=-1) + wheels.square().sum(dim=-1)


def m1_action_rate_l2(env) -> Tensor:
    source_names = tuple(getattr(env.cfg, "asset_joint_names", M1_ASSET_JOINT_NAMES))
    delta = env.action_manager.action - env.action_manager.prev_action
    planner = _select(delta, source_names, M1_PLANNER_JOINT_NAMES)
    wheels = _select(delta, source_names, M1_WHEEL_JOINT_NAMES)
    wheel_scale = float(getattr(env.cfg, "wheel_action_scale", 1.0))
    return planner.square().sum(-1) + (M1_WHEEL_RADIUS_M * wheel_scale)**2 * wheels.square().sum(-1)


def m1_energy(env, asset_cfg=None) -> Tensor:
    robot = _robot(env, asset_cfg)
    planner_torque = _select(robot.data.applied_torque, robot.joint_names, M1_PLANNER_JOINT_NAMES)
    planner_velocity = _select(robot.data.joint_vel, robot.joint_names, M1_PLANNER_JOINT_NAMES)
    wheel_torque = _select(robot.data.applied_torque, robot.joint_names, M1_WHEEL_JOINT_NAMES)
    wheel_velocity = _select(robot.data.joint_vel, robot.joint_names, M1_WHEEL_JOINT_NAMES)
    return (planner_torque * planner_velocity).abs().sum(dim=-1) + (
        wheel_torque * wheel_velocity
    ).abs().sum(dim=-1)


def m1_joint_pos_limits(env, asset_cfg=None) -> Tensor:
    robot = _robot(env, asset_cfg)
    planner = _select(robot.data.joint_pos, robot.joint_names, M1_PLANNER_JOINT_NAMES)
    lower = planner.new_tensor(_PLANNER_LOWER)
    upper = planner.new_tensor(_PLANNER_UPPER)
    return (torch.relu(lower - planner) + torch.relu(planner - upper)).sum(dim=-1)


def m1_failure_termination_penalty(env) -> Tensor:
    """Return a one-step penalty signal for physical failure terminations.

    Isaac Lab computes the termination manager before the reward manager.  Reading
    its per-term done buffers therefore assigns the penalty on the same step as a
    bad-orientation or base-contact reset, preventing early failure from becoming
    an attractor through shorter episode sums.
    """
    # RewardManager multiplies every term by dt. Cancel that integration for
    # this discrete event cost. Pure timeouts are excluded by `terminated`;
    # simultaneous timeout + physical failure still incurs the failure cost.
    if float(env.step_dt) <= 0:
        raise ValueError("step_dt must be positive")
    return env.termination_manager.terminated.to(torch.float32) / float(env.step_dt)


def m1_joint_position_penalty(
    env,
    asset_cfg=None,
    stand_still_scale: float = 5.0,
    velocity_threshold: float = 0.3,
) -> Tensor:
    robot = _robot(env, asset_cfg)
    planner = _select(robot.data.joint_pos, robot.joint_names, M1_PLANNER_JOINT_NAMES)
    default = _select(robot.data.default_joint_pos, robot.joint_names, M1_PLANNER_JOINT_NAMES)
    error = torch.linalg.vector_norm(planner - default, dim=-1)
    command_speed = torch.linalg.vector_norm(
        env.command_manager.get_command("base_velocity"), dim=-1
    )
    body_speed = torch.linalg.vector_norm(robot.data.root_lin_vel_b[:, :2], dim=-1)
    moving = (command_speed > 0.0) | (body_speed > velocity_threshold)
    return torch.where(moving, error, float(stand_still_scale) * error)


def m1_wheel_rolling_residual_l2(env, asset_cfg=None, sensor_cfg=None) -> Tensor:
    """Squared tangential contact-point speed (m²/s²) for M1 wheels.

    Uses link-origin velocity and total wheel-body angular velocity, including
    parent-link motion. The lowest point on the wheel disk approximates the
    contact point; vertical gravity is the reference normal on rough terrain.
    Unlike speed magnitudes, this also detects lateral slip and reversed spin.
    """
    robot = _robot(env, asset_cfg)
    sensor = env.scene[getattr(sensor_cfg, "name", "contact_forces")]
    body_ids = list(resolve_named_indices(robot.body_names, M1_SUPPORT_BODY_NAMES))
    sensor_ids = list(resolve_named_indices(sensor.body_names, M1_SUPPORT_BODY_NAMES))
    linear = robot.data.body_link_lin_vel_w[:, body_ids]
    angular = robot.data.body_ang_vel_w[:, body_ids]
    quat = robot.data.body_quat_w[:, body_ids]
    # Rotate the local wheel axle (+Y) into world coordinates (wxyz).
    w, x, y, z = quat.unbind(dim=-1)
    axle = torch.stack((2 * (x * y - w * z), 1 - 2 * (x*x + z*z), 2 * (y*z + w*x)), dim=-1)
    down = torch.zeros_like(axle)
    down[..., 2] = -1.0
    radial = down - (down * axle).sum(dim=-1, keepdim=True) * axle
    radial = M1_WHEEL_RADIUS_M * radial / radial.norm(dim=-1, keepdim=True).clamp_min(1e-6)
    contact_velocity = linear + torch.linalg.cross(angular, radial, dim=-1)
    forces = sensor.data.net_forces_w_history[:, :, sensor_ids]
    contact = forces.norm(dim=-1).amax(dim=1) > 1.0
    return (contact_velocity[..., :2].square().sum(dim=-1) * contact).sum(dim=-1)


def _small_obstacle_wheels(env) -> Tensor:
    # Planner-free AME selects swing rewards from observed small obstacles
    # within each wheel's horizontal collision envelope.
    from tracking.mdp.policy_geometry_rewards import _terrain_from_scanner
    from extension.parallelism.terrain import query_height_semantic_valid
    robot = env.scene["robot"]
    scanner = env.scene["semantic_height_scanner"]
    terrain = _terrain_from_scanner(scanner, robot.data.root_pos_w, resolution=float(scanner.cfg.pattern_cfg.resolution))
    ids = list(resolve_named_indices(robot.body_names, M1_SUPPORT_BODY_NAMES))
    xy = robot.data.body_pos_w[:, ids, :2]
    radius = M1_WHEEL_HORIZONTAL_ENVELOPE_M
    offsets = xy.new_tensor([(x, y) for x in (-radius, 0., radius) for y in (-radius, 0., radius)])
    query = query_height_semantic_valid(terrain, (xy[:, :, None] + offsets).reshape(xy.shape[0], -1, 2))
    return ((query.semantic == 1) & query.valid).reshape(xy.shape[0], 4, -1).any(-1)


def m1_obstacle_air_time(env, sensor_cfg=None, command_name="base_velocity", threshold=.5) -> Tensor:
    sensor = env.scene[getattr(sensor_cfg, "name", "contact_forces")]
    ids = list(resolve_named_indices(sensor.body_names, M1_SUPPORT_BODY_NAMES))
    contact = sensor.compute_first_contact(env.step_dt)[:, ids]
    air_time = sensor.data.last_air_time[:, ids]
    moving = env.command_manager.get_command(command_name)[:, :2].norm(dim=-1) > .1
    return ((air_time - threshold) * contact * _small_obstacle_wheels(env)).sum(-1) * moving


def m1_obstacle_air_time_variance(env, sensor_cfg=None) -> Tensor:
    sensor = env.scene[getattr(sensor_cfg, "name", "contact_forces")]
    ids = list(resolve_named_indices(sensor.body_names, M1_SUPPORT_BODY_NAMES))
    active = _small_obstacle_wheels(env)
    count = active.sum(-1)
    reward = torch.zeros_like(count, dtype=sensor.data.last_air_time.dtype)
    for values in (sensor.data.last_air_time[:, ids], sensor.data.last_contact_time[:, ids]):
        values = values.clamp(max=.5)
        mean = (values * active).sum(-1) / count.clamp_min(1)
        variance = ((values - mean[:, None]).square() * active).sum(-1) / (count - 1).clamp_min(1)
        reward += torch.where(count > 1, variance, torch.zeros_like(variance))
    return reward


__all__ = [
    "m1_obstacle_air_time",
    "m1_obstacle_air_time_variance",
    "m1_action_rate_l2",
    "m1_energy",
    "m1_joint_acc_l2",
    "m1_joint_pos_limits",
    "m1_joint_position_penalty",
    "m1_joint_torques_l2",
    "m1_joint_vel_l2",
    "m1_wheel_rolling_residual_l2",
]
