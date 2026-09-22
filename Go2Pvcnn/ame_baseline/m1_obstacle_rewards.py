"""Planner-free M1 small-obstacle shaping from actual link motion.

These are local shaping signals, not crossing-success metrics. They do not
replace body/semantic2 collision penalties or failure terminations.
"""
from __future__ import annotations

import torch
from torch import Tensor

from extension.parallelism.m1_kinematics import (
    M1_WHEEL_HORIZONTAL_ENVELOPE_M,
    M1_WHEEL_RADIUS_M,
)
from extension.parallelism.rl_adapter import resolve_named_indices
from extension.parallelism.terrain import query_height_semantic_valid
from extension.parallelism.types import ParallelismTerrain
from .m1_ame_rewards import M1_SUPPORT_BODY_NAMES


def wheel_obstacle_reward_terms(
    command_xy_b: Tensor,
    root_pos_w: Tensor,
    root_quat_w: Tensor,
    root_lin_vel_w: Tensor,
    root_ang_vel_w: Tensor,
    wheel_pos_w: Tensor,
    wheel_lin_vel_w: Tensor,
    terrain: ParallelismTerrain,
    return_presence: bool = False,
) -> tuple[Tensor, ...]:
    """Return bounded signed progress and nonnegative articulated lift [B].

    All positions/linear velocities must be LINK-origin quantities, quaternion
    is wxyz, and angular velocity is world-frame. No wheel spin, contact timer,
    planner target or persistent state is used. Statelessness avoids stale
    episode/command caches and double integration by separate reward terms.
    """
    batch = command_xy_b.shape[0]
    states = (command_xy_b, root_pos_w, root_quat_w, root_lin_vel_w,
              root_ang_vel_w, wheel_pos_w, wheel_lin_vel_w)
    finite = torch.stack([torch.isfinite(value).reshape(batch, -1).all(-1)
                          for value in states]).all(0)
    command, root_pos, quat, root_vel, root_omega, wheel_pos, wheel_vel = (
        torch.nan_to_num(value, nan=0., posinf=0., neginf=0.) for value in states
    )
    quat_norm = quat.norm(dim=-1)
    quat = quat / quat_norm[:, None].clamp_min(1e-6)
    qw, qx, qy, qz = quat.unbind(-1)
    yaw = torch.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy.square() + qz.square()))
    cosine, sine = yaw.cos(), yaw.sin()
    speed = command.norm(dim=-1)
    direction_b = command / speed[:, None].clamp_min(.1)
    direction = torch.stack((cosine * direction_b[:, 0] - sine * direction_b[:, 1],
                             sine * direction_b[:, 0] + cosine * direction_b[:, 1]), -1)
    lateral = torch.stack((-direction[:, 1], direction[:, 0]), -1)

    radius = M1_WHEEL_HORIZONTAL_ENVELOPE_M
    offsets = command.new_tensor([(x, y)
        for x in (-radius, 0., radius, radius + .15, radius + .30)
        for y in (-radius, 0., radius)])
    patch_xy = (wheel_pos[:, :, None, :2]
                + direction[:, None, None] * offsets[None, None, :, :1]
                + lateral[:, None, None] * offsets[None, None, :, 1:])
    query = query_height_semantic_valid(terrain, patch_xy.reshape(batch, -1, 2))
    height = query.height.reshape(batch, 4, -1)
    semantic = query.semantic.reshape(batch, 4, -1)
    valid = query.valid.reshape(batch, 4, -1) & torch.isfinite(height)
    small = valid & (semantic == 1)
    active_wheel = valid.all(-1) & small.any(-1)
    large_near = ((semantic == 2) & valid).any(dim=(1, 2))
    upright = 1 - 2 * (qx.square() + qy.square()) > .5
    enabled = (finite & torch.isfinite(speed) & (quat_norm > .5)
               & (speed > .1) & upright & active_wheel.any(-1) & ~large_near)

    root_forward = (root_vel[:, :2] * direction).sum(-1)
    progress = (root_forward / speed.clamp_min(.1)).clamp(-1., 1.)
    progress = torch.where(enabled & (root_forward.abs() > .02), progress, 0.)

    wheel_forward = (wheel_vel[..., :2] * direction[:, None]).sum(-1)
    coupled_forward = torch.minimum(root_forward[:, None], wheel_forward)
    forward_factor = (coupled_forward / speed[:, None].clamp_min(.1)).clamp(0., 1.)
    forward_factor = torch.where(coupled_forward > .02, forward_factor, 0.)
    # Remove both translation and rigid-body rotation. Root pitch/heave is
    # not articulated wheel lifting. Also require actual upward wheel motion,
    # so a chassis sinking above fixed/descending wheels earns no lift bonus.
    arm = wheel_pos - root_pos[:, None]
    rigid_velocity = root_vel[:, None] + torch.linalg.cross(
        root_omega[:, None].expand_as(arm), arm, dim=-1,
    )
    relative_up = wheel_vel[..., 2] - rigid_velocity[..., 2]
    lift_speed = torch.minimum(wheel_vel[..., 2], relative_up).clamp(0., .2)
    target_top = torch.where(small, height, -torch.inf).amax(-1)
    # Keep the normal gait unchanged.  When a semantic-small obstacle is
    # actually under a wheel, reward an adaptive clearance band: 5--10 cm
    # above the obstacle top.  The band is a gate, not a fixed swing target.
    clearance_low = target_top + 0.05
    clearance_high = target_top + 0.10
    height_gate = ((clearance_high - wheel_pos[..., 2]) /
                   (clearance_high - clearance_low).clamp_min(1e-6)).clamp(0., 1.)
    needs_lift = wheel_pos[..., 2] < clearance_high
    climb = (forward_factor * (lift_speed / .2) * active_wheel
             * needs_lift * height_gate).mean(-1)
    climb = torch.where(enabled, climb, 0.)
    # The existing nonfinite-state termination remains the owner of failures;
    # invalid data must not inject NaN into the PPO reward sum before reset.
    result = (torch.nan_to_num(progress, nan=0., posinf=0., neginf=0.),
              torch.nan_to_num(climb, nan=0., posinf=0., neginf=0.))
    if return_presence:
        return result + (active_wheel.any(-1), large_near)
    return result


def _terms_from_env(env, command_name, return_presence=False):
    from tracking.mdp.policy_geometry_rewards import _terrain_from_scanner

    robot = env.scene['robot']
    scanner = env.scene['semantic_height_scanner']
    data = robot.data
    body_ids = list(resolve_named_indices(robot.body_names, M1_SUPPORT_BODY_NAMES))
    terrain = _terrain_from_scanner(
        scanner, data.root_pos_w, resolution=float(scanner.cfg.pattern_cfg.resolution),
    )
    terms = wheel_obstacle_reward_terms(
        command_xy_b=env.command_manager.get_command(command_name)[:, :2],
        root_pos_w=data.root_pos_w, root_quat_w=data.root_quat_w,
        root_lin_vel_w=data.root_link_lin_vel_w, root_ang_vel_w=data.root_ang_vel_w,
        wheel_pos_w=data.body_link_pos_w[:, body_ids],
        wheel_lin_vel_w=data.body_link_lin_vel_w[:, body_ids], terrain=terrain,
        return_presence=return_presence,
    )
    return terms


def m1_small_obstacle_progress(env, command_name='base_velocity') -> Tensor:
    return _terms_from_env(env, command_name)[0]


def m1_small_obstacle_climb(env, command_name='base_velocity') -> Tensor:
    return _terms_from_env(env, command_name)[1]


def m1_obstacle_presence(env, command_name='base_velocity') -> tuple[Tensor, Tensor]:
    """Return semantic-small and semantic-large candidate masks."""
    terms = _terms_from_env(env, command_name, return_presence=True)
    return terms[2], terms[3]
