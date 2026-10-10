"""Planner-free M1 small-obstacle shaping from actual link motion.

These are local shaping signals, not crossing-success metrics. They do not
replace body/semantic2 collision penalties or failure terminations.
"""
from __future__ import annotations

import os

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
from .m1_obstacle_profile import (
    M1_DEFAULT_SMALL_OBSTACLE_HEIGHT_M,
    M1_FIXED_SMALL_OBSTACLE_LOCAL_XY,
)


def wheel_obstacle_reward_terms(
    command_xy_b: Tensor,
    root_pos_w: Tensor,
    root_quat_w: Tensor,
    root_lin_vel_w: Tensor,
    root_ang_vel_w: Tensor,
    wheel_pos_w: Tensor,
    wheel_lin_vel_w: Tensor,
    terrain: ParallelismTerrain,
    course_origin_xy: Tensor | None = None,
    return_presence: bool = False,
    return_clearance: bool = False,
    allow_stationary_single_lift: bool = False,
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
    # Keep the existing physical lookahead bounds, but cover the gaps between
    # old15cm samples: authored5cm blocks otherwise starve real pre-lift rewards.
    # Retain original samples so diagnostics at the exact old offsets stay valid.
    longitudinal = sorted(set(
        [-radius, 0., radius, radius+.15, radius+.30, radius+.45, radius+.60]
        + [-radius + .02*i for i in range(int((2*radius+.60)/.02)+1)]
    ))
    offsets = command.new_tensor([(x, y)
        for x in longitudinal
        for y in (-radius, 0., radius)])
    patch_xy = (wheel_pos[:, :, None, :2]
                + direction[:, None, None] * offsets[None, None, :, :1]
                + lateral[:, None, None] * offsets[None, None, :, 1:])
    query = query_height_semantic_valid(terrain, patch_xy.reshape(batch, -1, 2))
    height = query.height.reshape(batch, 4, -1)
    semantic = query.semantic.reshape(batch, 4, -1)
    valid = query.valid.reshape(batch, 4, -1) & torch.isfinite(height)
    small = valid & (semantic == 1)
    # Only a wheel-local patch can mark a specific wheel active.  The
    # forward corridor is an early trigger for the teacher, not evidence that
    # every wheel has already cleared the block.
    wheel_patch_valid = valid.any(-1).any(-1)
    active_wheel = valid.any(-1) & small.any(-1)
    large_near = ((semantic == 2) & valid).any(dim=(1, 2))
    # The M1 serial course also contains fixed collision meshes.  Depending on
    # the Isaac scanner backend those meshes may not carry semantic ids, so a
    # semantic-only reward silently reports zero lift even when the wheel is
    # over a real 10 cm block.  Add a geometry-only fallback tied to the exact
    # authored centers; it is used only for M1's fixed course and never for the
    # generic random terrain.
    fixed_small = torch.zeros(batch, 4, dtype=torch.bool, device=command.device)
    fixed_small_top = torch.zeros(batch, 4, dtype=command.dtype, device=command.device)
    if course_origin_xy is not None and os.environ.get("M1_OBSTACLE_STAGE", "full").strip().lower() != "none":
        fixed_xy = command.new_tensor(M1_FIXED_SMALL_OBSTACLE_LOCAL_XY)
        centers = course_origin_xy[:, None, :2] + fixed_xy[None, :, :]
        dx = wheel_pos[:, :, None, 0] - centers[:, None, :, 0]
        dy = wheel_pos[:, :, None, 1] - centers[:, None, :, 1]
        # Include the wheel envelope and a small scanner tolerance.
        fixed_small = (dx.abs() <= (0.10 + radius)) & (dy.abs() <= (0.10 + radius))
        fixed_small &= (root_pos[:, 1] - course_origin_xy[:, 1]).abs()[:, None, None] < 0.75
        fixed_small = fixed_small.any(-1)
        fixed_height = float(os.environ.get(
            "M1_SMALL_OBSTACLE_HEIGHT_M", str(M1_DEFAULT_SMALL_OBSTACLE_HEIGHT_M),
        ))
        fixed_small_top = torch.where(fixed_small, root_pos.new_full((batch, 4), fixed_height), fixed_small_top)
    active_wheel = active_wheel | fixed_small
    # The wheel-local patch is deliberately supplemented with a forward
    # corridor probe.  A wheel can only see a 10 cm block for a few frames
    # once it is already close to the block; the corridor scan gives MPC the
    # lead time needed to lift one leg before contact, without triggering on
    # obstacles behind the robot or outside the protected foothold corridor.
    # The semantic scanner is discretized at roughly 10 cm.  Sampling only
    # seven exact x locations made a 10 cm block visible for one frame (or
    # missed entirely between samples), starving the pre-lift teacher.  Use a
    # denser forward center corridor while keeping lateral probes narrow so
    # side obstacles do not masquerade as crossable centerline blocks.
    probe_offsets = command.new_tensor([(x, y)
        for x in (round(0.10 + 0.05 * i, 2) for i in range(31))
        for y in (-.15, 0., .15)])
    probe_xy = (root_pos[:, None, :2]
                + direction[:, None] * probe_offsets[None, :, :1]
                + lateral[:, None] * probe_offsets[None, :, 1:])
    probe_query = query_height_semantic_valid(terrain, probe_xy)
    probe_valid = probe_query.valid & torch.isfinite(probe_query.height)
    probe_small = probe_valid & (probe_query.semantic == 1)
    probe_large = probe_valid & (probe_query.semantic == 2)
    probe_small_any = probe_small.any(-1)
    probe_large_any = probe_large.any(-1)
    # The M1 training course is authored on the tile/world +X centerline. If
    # the policy yaws a little before reaching a block, a body-frame probe can
    # turn away from that fixed course and miss the obstacle entirely. Add a
    # narrow world-course probe for small blocks only; large blocks continue
    # to use the command-frame probe so side-avoidance remains available.
    course_small_any = torch.zeros(batch, dtype=torch.bool, device=command.device)
    course_small_top = torch.zeros(batch, dtype=command.dtype, device=command.device)
    if course_origin_xy is not None:
        course_offsets = command.new_tensor([(x, y)
            for x in (round(0.10 + 0.05 * i, 2) for i in range(31))
            for y in (-.10, 0., .10)])
        course_xy = torch.stack((
            root_pos[:, None, 0] + course_offsets[None, :, 0],
            course_origin_xy[:, None, 1] + course_offsets[None, :, 1],
        ), dim=-1)
        course_query = query_height_semantic_valid(terrain, course_xy)
        course_valid = course_query.valid & torch.isfinite(course_query.height)
        course_small = course_valid & (course_query.semantic == 1)
        course_small_any = course_small.any(-1)
        course_small_top = torch.where(
            course_small, course_query.height, -torch.inf,
        ).amax(-1)
        on_course = (root_pos[:, 1] - course_origin_xy[:, 1]).abs() < .75
        course_small_any &= on_course
        course_small_top = torch.where(course_small_any, course_small_top, torch.zeros_like(course_small_top))
    # Presence includes the forward probe so the M1 teacher can pre-lift,
    # while reward/success accounting remains tied to the local wheel patch.
    small_present = active_wheel.any(-1) | probe_small_any | course_small_any
    large_near = large_near | probe_large_any
    upright = 1 - 2 * (qx.square() + qy.square()) > .5
    enabled = (finite & torch.isfinite(speed) & (quat_norm > .5)
               & (speed > .1) & upright & (wheel_patch_valid | fixed_small.any(-1))
               & small_present & ~large_near)

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
    if allow_stationary_single_lift:
        # PPO must be able to discover lifting before forward travel. Only
        # one articulating wheel near a real local small obstacle is eligible;
        # body heave, reverse motion and stationary multi-wheel bouncing are not.
        single_up = (lift_speed > .02).sum(-1) == 1
        waiting = (root_forward.abs() <= .02) & single_up
        forward_factor = torch.where(
            waiting[:, None] & active_wheel & (lift_speed > .02),
            torch.ones_like(forward_factor), forward_factor,
        )
    # wheel_pos is the wheel-link centre, not the contact patch.  Convert to
    # wheel-bottom clearance before both shaping and success accounting.
    target_top = torch.where(small, height, -torch.inf).amax(-1)
    # A forward-only probe has no local top for this wheel. Keep that path
    # finite and inactive so it cannot fabricate a clearance event.
    target_top = torch.where(active_wheel, target_top, torch.zeros_like(target_top))
    target_top = torch.where(fixed_small, fixed_small_top, target_top)
    # During the pre-lift window the obstacle top comes from the fixed-course
    # probe, not from a wheel-local patch yet. Use it only for exploration
    # shaping; strict clearance/success below remains local-patch-only.
    target_top = torch.where(
        (~active_wheel) & course_small_any[:, None],
        course_small_top[:, None].expand_as(target_top),
        target_top,
    )
    wheel_bottom_clearance = wheel_pos[..., 2] - M1_WHEEL_RADIUS_M - target_top
    # Dense progress: at ground level the wheel bottom is roughly 5 cm below
    # a 5 cm obstacle top; at +5 cm it has genuinely cleared the obstacle.
    # This rewards an early visible lift without ever calling a scrape a
    # crossing.  Upward articulated velocity is still required, so a static
    # wheel cannot farm the shaping term.
    lift_progress = ((wheel_bottom_clearance + 0.05) / 0.10).clamp(0., 1.)
    reward_active_wheel = active_wheel | fixed_small | course_small_any[:, None]
    climb = (forward_factor * (lift_speed / .2)
             * (0.25 + 0.75 * lift_progress) * reward_active_wheel).mean(-1)
    climb = torch.where(enabled, climb, 0.)
    # Success accounting is stricter than exploration reward: at least one
    # wheel must be at least 5 cm above the local obstacle top while a small
    # obstacle is present.  This prevents a low scrape from being recorded as
    # a crossing even though low upward motion still receives exploration
    # reward above.
    clearance_seen = (active_wheel & (wheel_bottom_clearance >= 0.05)).any(-1)
    # The existing nonfinite-state termination remains the owner of failures;
    # invalid data must not inject NaN into the PPO reward sum before reset.
    result = (torch.nan_to_num(progress, nan=0., posinf=0., neginf=0.),
              torch.nan_to_num(climb, nan=0., posinf=0., neginf=0.))
    if return_presence:
        return result + (small_present, large_near)
    if return_clearance:
        return result + (clearance_seen,)
    return result


def reward_course_origin(env, scene_origins):
    """Only the fixed diagnostic course may use fixed-six fallback geometry."""
    if getattr(getattr(env, 'cfg', None), 'm1_course_profile', 'fixed') == 'mixed':
        return None
    return scene_origins[:, :2] if scene_origins is not None else None


def _terms_from_env(env, command_name, return_presence=False, return_clearance=False,
                    allow_stationary_single_lift=False):
    from tracking.mdp.policy_geometry_rewards import _terrain_from_scanner

    robot = env.scene['robot']
    scanner = env.scene['semantic_height_scanner']
    data = robot.data
    body_ids = list(resolve_named_indices(robot.body_names, M1_SUPPORT_BODY_NAMES))
    terrain = _terrain_from_scanner(
        scanner, data.root_pos_w, resolution=float(scanner.cfg.pattern_cfg.resolution),
    )
    if getattr(env, "_m1_presence_probe_once", False) is False and __import__("os").environ.get("M1_PRESENCE_PROBE", "0") == "1":
        env._m1_presence_probe_once = True
        print("[M1 presence probe] root0=", data.root_pos_w[0].detach().cpu().tolist(), "origin0=", env.scene.env_origins[0].detach().cpu().tolist(), "semantic_unique=", torch.unique(terrain.semantic_id[0].detach()).cpu().tolist(), "valid=", int(terrain.valid_mask[0].sum().item()), flush=True)
    scene_origins = getattr(env.scene, "env_origins", None)
    if scene_origins is None and isinstance(env.scene, dict):
        scene_origins = env.scene.get("env_origins")
    terms = wheel_obstacle_reward_terms(
        command_xy_b=env.command_manager.get_command(command_name)[:, :2],
        root_pos_w=data.root_pos_w, root_quat_w=data.root_quat_w,
        root_lin_vel_w=data.root_link_lin_vel_w, root_ang_vel_w=data.root_ang_vel_w,
        wheel_pos_w=data.body_link_pos_w[:, body_ids],
        wheel_lin_vel_w=data.body_link_lin_vel_w[:, body_ids], terrain=terrain,
        course_origin_xy=reward_course_origin(env, scene_origins),
        return_presence=return_presence, return_clearance=return_clearance,
        allow_stationary_single_lift=allow_stationary_single_lift,
    )
    return terms


def m1_small_obstacle_progress(env, command_name='base_velocity') -> Tensor:
    return _terms_from_env(env, command_name)[0]


def bounded_stationary_lift_reward(*, reward, stationary, reset, step_id, dt, state):
    """At most .05 unweighted reward-seconds per episode while not progressing.

    With climb weight4 this is <=.2 per episode, well below fall cost20.
    Duplicate metric reads at the same physics state do not spend budget twice.
    Forward crossing shaping is unaffected; no action is changed here.
    """
    if dt <= 0:
        raise ValueError('positive reward timestep required')
    if state.get('step') == step_id:
        return state['reward'].clone()
    remaining = state.get('remaining', torch.full_like(reward, .05))
    remaining = torch.where(reset, torch.full_like(remaining, .05), remaining)
    granted = torch.minimum(reward.clamp_min(0), remaining / dt)
    result = torch.where(stationary, granted, reward)
    state.update(step=step_id, reward=result.detach().clone(),
                 remaining=(remaining-torch.where(stationary, granted*dt, 0.)).clamp_min(0).detach())
    return result


def m1_small_obstacle_climb(env, command_name='base_velocity', allow_stationary_single_lift=True) -> Tensor:
    reward = _terms_from_env(env, command_name,
        allow_stationary_single_lift=allow_stationary_single_lift)[1]
    if allow_stationary_single_lift and hasattr(env, 'common_step_counter'):
        if not hasattr(env, '_m1_stationary_lift_reward_state'):
            env._m1_stationary_lift_reward_state = {}
        # A conservative speed test also budgets sideward shuffling: it must
        # not repeatedly rearm an unlimited stationary-lift bonus.
        command = env.command_manager.get_command(command_name)[:, :2]
        direction = command / command.norm(dim=-1, keepdim=True).clamp_min(.1)
        forward = (env.scene['robot'].data.root_lin_vel_b[:, :2] * direction).sum(-1)
        stationary = forward <= .02
        reward = bounded_stationary_lift_reward(reward=reward, stationary=stationary,
            reset=env.reset_buf.bool(), step_id=int(env.common_step_counter),
            dt=float(env.step_dt), state=env._m1_stationary_lift_reward_state)
    return reward


def m1_obstacle_presence(env, command_name='base_velocity') -> tuple[Tensor, Tensor]:
    """Return semantic-small and semantic-large candidate masks."""
    terms = _terms_from_env(env, command_name, return_presence=True)
    return terms[2], terms[3]


def m1_teacher_obstacle_presence(
    env, command_name='base_velocity', max_forward_m: float = 0.35,
) -> tuple[Tensor, Tensor]:
    """Return obstacles close enough to activate the M1 crossing teacher.

    ``m1_obstacle_presence`` intentionally scans a long forward corridor for
    reward/metrics.  Feeding that broad mask directly into the teacher made
    the robot start a one-leg swing while the first block was still far away,
    which destabilised the base before contact.  This gate keeps the broad
    presence signal for accounting but limits teacher activation to a short,
    command-frame window immediately in front of the robot.
    """
    from tracking.mdp.policy_geometry_rewards import _terrain_from_scanner

    robot = env.scene["robot"]
    scanner = env.scene["semantic_height_scanner"]
    data = robot.data
    terrain = _terrain_from_scanner(
        scanner, data.root_pos_w,
        resolution=float(scanner.cfg.pattern_cfg.resolution),
    )
    command = env.command_manager.get_command(command_name)[:, :2]
    root = data.root_pos_w
    quat = data.root_quat_w
    qw, qx, qy, qz = quat.unbind(-1)
    yaw = torch.atan2(
        2.0 * (qw * qz + qx * qy),
        1.0 - 2.0 * (qy.square() + qz.square()),
    )
    speed = command.norm(dim=-1)
    direction_b = command / speed[:, None].clamp_min(0.1)
    direction = torch.stack(
        (yaw.cos() * direction_b[:, 0] - yaw.sin() * direction_b[:, 1],
         yaw.sin() * direction_b[:, 0] + yaw.cos() * direction_b[:, 1]),
        dim=-1,
    )
    lateral = torch.stack((-direction[:, 1], direction[:, 0]), dim=-1)
    max_forward = max(float(max_forward_m), 0.05)
    # Include the block envelope and scanner quantisation without rearming
    # the teacher from obstacles behind the body.
    xs = torch.linspace(
        0.05, max_forward, 7, dtype=root.dtype, device=root.device,
    )
    ys = root.new_tensor((-0.15, 0.0, 0.15))
    offsets = torch.stack(
        torch.meshgrid(xs, ys, indexing="ij"), dim=-1,
    ).reshape(1, -1, 2).expand(root.shape[0], -1, -1)
    probe_xy = root[:, None, :2] + direction[:, None] * offsets[..., :1]
    probe_xy = probe_xy + lateral[:, None] * offsets[..., 1:]
    query = query_height_semantic_valid(terrain, probe_xy)
    valid = query.valid & torch.isfinite(query.height)
    small_trigger = (valid & (query.semantic == 1)).any(dim=-1)
    large_trigger = (valid & (query.semantic == 2)).any(dim=-1)
    # The authored M1 course is placed relative to each tile origin.  A
    # command-frame probe can miss that world-aligned strip when the body has
    # drifted or yawed slightly, while the broad presence mask still sees it.
    # Probe the same short x-window in the world course frame so each of the
    # six serial blocks creates its own re-armable teacher event.
    scene_origins = getattr(env.scene, "env_origins", None)
    if scene_origins is None and isinstance(env.scene, dict):
        scene_origins = env.scene.get("env_origins")
    if scene_origins is not None:
        course_offsets = torch.stack(
            torch.meshgrid(xs, ys, indexing="ij"), dim=-1,
        ).reshape(1, -1, 2).expand(root.shape[0], -1, -1)
        course_xy = torch.stack(
            (root[:, None, 0] + course_offsets[..., 0],
             scene_origins[:, None, 1] + course_offsets[..., 1]), dim=-1,
        )
        course_query = query_height_semantic_valid(terrain, course_xy)
        course_valid = course_query.valid & torch.isfinite(course_query.height)
        on_course = (root[:, 1] - scene_origins[:, 1]).abs() < 0.75
        small_trigger |= on_course & (course_valid & (course_query.semantic == 1)).any(dim=-1)
        large_trigger |= (course_valid & (course_query.semantic == 2)).any(dim=-1)
    return small_trigger, large_trigger


def m1_small_obstacle_corridor_penalty(env, command_name='base_velocity') -> Tensor:
    """Penalize lateral detours around small obstacles, but not large ones.

    The M1 course puts small obstacles on the forward centerline.  Without a
    route constraint, PPO can obtain forward-velocity reward by walking a
    metre or more around the block, which is collision-free but is not a
    crossing.  Keep a 22 cm center corridor (enough for the 8 cm lateral
    command band and wheel envelope) and leave the large-obstacle branch free
    to perform the required side-step avoidance.
    """
    small, large = m1_obstacle_presence(env, command_name)
    root = env.scene["robot"].data.root_pos_w
    origins = getattr(env.scene, "env_origins", None)
    if origins is None:
        local_y = root[:, 1]
    else:
        local_y = (root - origins)[:, 1]
    overflow = (local_y.abs() - 0.22).clamp_min(0.0) / 0.30
    return torch.where(small & ~large, overflow.clamp_max(1.0), torch.zeros_like(overflow))


def m1_small_obstacle_clearance(env, command_name='base_velocity') -> Tensor:
    """Return the strict 5 cm top-clearance observation for success metrics."""
    return _terms_from_env(env, command_name, return_clearance=True)[2]


def m1_obstacle_collision_penalty(env, asset_cfg=None, scanner_cfg=None) -> Tensor:
    """Return a positive M1 obstacle-collision event for a negative reward term.

    The event is computed from the live M1 FK geometry against the semantic
    scanner map. It deliberately stays separate from lift/crossing shaping:
    a wheel can earn an early-lift signal, but any M1 body/leg geometry that
    intersects a semantic obstacle is penalized by the reward weight.
    """
    from tracking.mdp.policy_geometry_rewards import m1_policy_geometry_collision_penalty

    if asset_cfg is None and scanner_cfg is None:
        event = m1_policy_geometry_collision_penalty(env)
    else:
        event = m1_policy_geometry_collision_penalty(
            env,
            asset_cfg=asset_cfg,
            scanner_cfg=scanner_cfg,
        )
    return torch.nan_to_num(event, nan=0.0, posinf=1.0, neginf=0.0).clamp(0.0, 1.0)


def m1_non_support_obstacle_contact(env, sensor_cfg=None, command_name="base_velocity") -> Tensor:
    """Penalize leg/body contact while a semantic small obstacle is nearby.

    A kinematic rigid-object face can be missed by the semantic FK query even
    though PhysX reports the contact. Foot contact is expected while rolling;
    contact on the base, abad, hip, or knee in the small-obstacle corridor is
    a scrape/body hit and must be exposed to PPO as a separate penalty.
    """
    sensor = env.scene[getattr(sensor_cfg, "name", "contact_forces")]
    forces = sensor.data.net_forces_w
    support = set(M1_SUPPORT_BODY_NAMES)
    non_support = [i for i, name in enumerate(tuple(sensor.body_names)) if name not in support]
    if not non_support:
        return torch.zeros(forces.shape[0], device=forces.device, dtype=forces.dtype)
    force = forces[:, non_support].norm(dim=-1).amax(dim=-1)
    small, large = m1_obstacle_presence(env, command_name)
    speed = env.command_manager.get_command(command_name)[:, :2].norm(dim=-1)
    active = small & ~large & (speed > 0.05)
    return (active & (force > 8.0)).to(dtype=forces.dtype)
