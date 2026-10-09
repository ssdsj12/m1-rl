#!/usr/bin/env python3
"""Short M1 teacher-driven PhysX probe for the 10 cm obstacle profile."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from isaaclab.app import AppLauncher

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


THIS_FILE = Path(__file__).resolve()
PACKAGE_ROOT = THIS_FILE.parent.parent
RSL_RL_ROOT = PACKAGE_ROOT / "rsl_rl"
for path in (PACKAGE_ROOT, RSL_RL_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from ame_baseline.m1_runtime_defaults import apply_m1_runtime_defaults
apply_m1_runtime_defaults()

parser = argparse.ArgumentParser()
parser.add_argument("--num_steps", type=int, default=320)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
_PROBE_STARTED_AT = time.perf_counter()
_PROGRESS_EVERY = max(1, int(os.environ.get("M1_PROBE_PROGRESS_EVERY", "8")))


def _emit_probe_progress(stage: str, **fields) -> None:
    payload = {"stage": stage, "elapsed_s": round(time.perf_counter() - _PROBE_STARTED_AT, 3)}
    payload.update(fields)
    print("M1_TEACHER_PHYSX_PROGRESS " + json.dumps(payload, separators=(",", ":")), flush=True)


if str(args.device).startswith("cuda"):
    import torch
    torch.cuda.set_device(int(str(args.device).split(":")[-1]))
launcher = AppLauncher(args)
app = launcher.app
_emit_probe_progress("app_started")
env = None
try:
    import torch
    from isaaclab.envs import ManagerBasedRLEnv

    from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES, M1_WHEEL_RADIUS_M
    from extension.trajectory_manager_factory import attach_trajectory_manager
    from extension.convention import extract_roll_pitch_batch, extract_yaw_batch
    from extension.parallelism.robot_backend import get_robot_backend
    from tracking.mdp.policy_geometry_rewards import _expand_geometry_for_collision, _terrain_from_scanner

    cfg = M1AmeCrossLargeComplexEnvCfg()
    cfg.scene.num_envs = 1
    cfg.scene.env_spacing = 8.0
    cfg.sim.device = str(args.device)
    # Probe-only actuator sweep: production training keeps the calibrated
    # values from M1AmeCrossLargeComplexEnvCfg unless these variables are
    # explicitly supplied by a bounded physics experiment.
    if "M1_PROBE_LEG_STIFFNESS" in os.environ:
        cfg.scene.robot.actuators["legs"].stiffness = float(os.environ["M1_PROBE_LEG_STIFFNESS"])
    if "M1_PROBE_LEG_DAMPING" in os.environ:
        cfg.scene.robot.actuators["legs"].damping = float(os.environ["M1_PROBE_LEG_DAMPING"])
    probe_seed = os.environ.get("M1_PROBE_SEED")
    if probe_seed:
        cfg.seed = int(probe_seed)
    cfg.events.push_robot = None
    # Optional start offset lets the physics gate exercise the actual
    # pre-contact single-leg trajectory instead of spending the whole probe
    # approaching the first 10 cm block.
    start_x = float(os.environ.get("M1_PROBE_START_X", "0.0"))
    cfg.events.reset_base.params["pose_range"] = {"x": (start_x, start_x), "y": (0., 0.), "yaw": (0., 0.)}
    cfg.events.reset_robot_joints.params["velocity_range"] = (0., 0.)
    # Match the obstacle warmup stage speed; 0.5 m/s would test a different
    # regime and overstate collision/tilt failures of the crossing sequence.
    probe_speed = float(os.environ.get("M1_PROBE_SPEED", "0.10"))
    cfg.commands.base_velocity.ranges.lin_vel_x = (probe_speed, probe_speed)
    cfg.commands.base_velocity.ranges.lin_vel_y = (0., 0.)
    cfg.commands.base_velocity.ranges.ang_vel_z = (0., 0.)
    cfg.commands.base_velocity.rel_standing_envs = 0.0
    env = ManagerBasedRLEnv(cfg=cfg)
    _emit_probe_progress("environment_created")
    attach_trajectory_manager(env, cfg, device=str(args.device))
    _emit_probe_progress("trajectory_manager_attached")
    wrapped = AmeRslRlEnvWrapper(env, clip_actions=100.0)
    wrapped.reset()
    policy_obs, obs_extra = wrapped.get_observations()
    critic_obs = obs_extra["observations"]["critic"]
    if policy_obs.shape != (1, 1589) or critic_obs.shape != (1, 1592):
        raise RuntimeError(f"M1 observation mismatch: {policy_obs.shape}, {critic_obs.shape}")
    _emit_probe_progress("observation_contract", policy_dim=1589, critic_dim=1592)
    _emit_probe_progress("wrapper_reset_complete")

    # Actual authored collision geometry, not the nominal course template.
    # Static world bounds survive episode resets; samples carry their origin.
    obstacle_collision_bounds_w = []
    obstacle_geometry_error = None
    try:
        import omni.usd
        from pxr import Usd, UsdGeom, UsdPhysics
        stage = omni.usd.get_context().get_stage()
        course = stage.GetPrimAtPath('/World/semantic_course')
        if not course.IsValid():
            raise RuntimeError('semantic course prim is missing')
        bounds_cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render,
                                    UsdGeom.Tokens.proxy], useExtentsHint=False,
        )
        for prim in Usd.PrimRange(course):
            if not prim.HasAPI(UsdPhysics.CollisionAPI):
                continue
            if not UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get():
                continue
            bounds = bounds_cache.ComputeWorldBound(prim).ComputeAlignedRange()
            if bounds.IsEmpty():
                raise RuntimeError(f'empty collision bounds: {prim.GetPath()}')
            obstacle_collision_bounds_w.append({
                'prim_path': str(prim.GetPath()),
                'minimum': list(bounds.GetMin()), 'maximum': list(bounds.GetMax()),
            })
    except Exception as exc:
        obstacle_geometry_error = f'{type(exc).__name__}: {exc}'

    robot = env.scene["robot"]
    wheel_ids = list(resolve_named_indices(tuple(robot.body_names), M1_SUPPORT_BODY_NAMES))
    # The teacher action is in M1 asset order; Isaac joint names are alphabetical.
    planner_cols = resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES)
    asset_ids = list(resolve_named_indices(tuple(robot.joint_names), M1_ASSET_JOINT_NAMES))
    from ame_baseline.m1_ame_contract import m1_action_targets
    valid_steps = 0
    reference_valid_steps = 0
    max_swing_legs = 0
    strict_target_checked_steps = 0
    strict_target_mismatch_steps = 0
    serial_sequence_trace = []
    max_wheel_bottom_m = float("-inf")
    max_tilt_rad = 0.0
    geometry_collision_steps = 0
    geometry_collision_trace = []
    non_support_force_max_n = 0.0
    non_support_contact_steps = 0
    non_support_force_by_body = {}
    samples = []
    episode_id = 0
    for step in range(int(args.num_steps)):
        _step_started_at = time.perf_counter()
        leg_groups = torch.zeros((1, 4), dtype=torch.bool, device=cfg.sim.device)
        serial_phase_before_action = int(wrapped._m1_teacher_age[0].item())
        strict_target_before_action = wrapped._m1_strict_crossing.target_wheel.detach().clone()
        recovery_before_action = wrapped._m1_strict_crossing.awaiting_recovery.detach().clone()
        failed_before_action = wrapped._m1_strict_crossing.failed.detach().clone()
        action, valid = wrapped.get_mpc_teacher_action()
        reference_valid = getattr(wrapped, "_m1_teacher_reference_valid", valid)
        if reference_valid is not None:
            reference_valid_steps += int(reference_valid.sum().item())
        selected_leg_tensor = getattr(wrapped, "_m1_teacher_selected_leg", None)
        if selected_leg_tensor is None:
            selected_leg = -1
        else:
            selected_leg = int(torch.as_tensor(selected_leg_tensor).reshape(-1)[0].item())
        from ame_baseline.m1_probe_metrics import strict_target_leg_mismatch_mask
        strict_leg_mismatch = strict_target_leg_mismatch_mask(
            selected_leg=torch.full_like(strict_target_before_action, selected_leg),
            target_wheel=strict_target_before_action,
            awaiting_recovery=recovery_before_action,
            failed=failed_before_action,
        )
        strict_target_checked_steps += int((
            (strict_target_before_action >= 0)
            & ~recovery_before_action
            & ~failed_before_action
        ).sum().item())
        strict_target_mismatch_steps += int(strict_leg_mismatch.sum().item())
        if selected_leg >= 0 and (not serial_sequence_trace or serial_sequence_trace[-1] != selected_leg):
            serial_sequence_trace.append(selected_leg)
        reference = env._trajectory_manager.current_reference(frame_offset=1)
        if action is None:
            action = torch.zeros((1, 16), device=cfg.sim.device)
            valid = torch.zeros(1, dtype=torch.bool, device=cfg.sim.device)
        # Preserve the teacher wheel action returned by the M1 wrapper.
        # It already contains phase slowdown and approach-speed limiting;
        # replacing it with full probe_speed would hide the real behavior.
        # The wrapper deliberately keeps a finite, measured-pose teacher action
        # (including reduced wheel drive) while a crossing is active but one
        # planner frame is invalid.  Zeroing those wheel commands here stalls
        # the base and makes this physical probe unlike the runtime controller.
        from ame_baseline.m1_teacher_phase import gate_probe_invalid_wheel_actions
        wheel_cols = resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES)
        teacher_active = torch.as_tensor(
            getattr(wrapped, "_m1_teacher_active", torch.zeros(1, dtype=torch.bool)),
            device=action.device, dtype=torch.bool,
        )
        action = gate_probe_invalid_wheel_actions(
            action, valid=valid, teacher_active=teacher_active, wheel_cols=wheel_cols,
        )
        selected_leg_action_max = 0.0
        other_nonzero_leg_action_count = 0
        if bool(valid.any().item()):
            valid_steps += 1
            leg_groups = action[:, planner_cols].reshape(1, 4, 3).abs().amax(dim=-1) > 1.0e-4
            selected_leg_action_max = float(leg_groups[0, selected_leg].item()) if 0 <= selected_leg < 4 else 0.0
            other_nonzero_leg_action_count = int(leg_groups.sum(dim=-1).max().item()) - (1 if selected_leg_action_max else 0)
            # Action magnitudes describe targets, not physical lift. The
            # single-swing gate is computed after PhysX from wheel height and
            # measured contact force below.
        measured_joint_before = robot.data.joint_pos[:, asset_ids].detach().clone()
        decoded_target = m1_action_targets(action, robot.data.default_joint_pos[:, asset_ids])
        held_target = wrapped._m1_teacher_hold_pose.detach().clone()
        _, _, done, _ = wrapped.step(action)
        roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
        tilt = torch.maximum(roll.abs(), pitch.abs())
        max_tilt_rad = max(max_tilt_rad, float(tilt[0].item()))
        wheel_z = robot.data.body_pos_w[:, wheel_ids, 2]
        max_wheel_bottom_m = max(max_wheel_bottom_m, float((wheel_z - float(M1_WHEEL_RADIUS_M)).max().item()))
        from ame_baseline.m1_probe_metrics import crossing_attempt_mask
        crossing_tracker = wrapped._m1_strict_crossing
        crossing_attempt = crossing_attempt_mask(
            teacher_active=teacher_active,
            selected_leg=torch.full_like(
                wrapped._m1_teacher_selected_leg, selected_leg,
            ),
            target_wheel=crossing_tracker.target_wheel,
            awaiting_recovery=crossing_tracker.awaiting_recovery,
            failed=crossing_tracker.failed,
        )
        names = list(env.reward_manager.active_terms)
        collision = None
        if "parallelism_geometry_collision" in names:
            collision = env.reward_manager._step_reward[:, names.index("parallelism_geometry_collision")] != 0
            geometry_collision_steps += int(collision.sum().item())
            if bool(collision.any().item()) and os.environ.get("M1_PROBE_SKIP_GEOMETRY", "0") != "1":
                collision_item = {
                    "step": step,
                    "phase_index": int(torch.as_tensor(reference.get("phase_index", [0])).reshape(-1)[0].item()),
                    "root_x_m": float(robot.data.root_pos_w[0, 0].item()),
                    "wheel_z_m": wheel_z[0].tolist(),
                }
                # Decode the live geometry collision into named M1 shapes.
                # This distinguishes a wheel/obstacle contact from a thigh,
                # hip, or calf envelope intersecting the same semantic cell.
                try:
                    root_pos = torch.as_tensor(robot.data.root_pos_w, dtype=torch.float32, device=cfg.sim.device)
                    roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
                    yaw = extract_yaw_batch(robot.data.root_quat_w)
                    root_rpy = torch.stack((roll, pitch, yaw), dim=-1)
                    joint_cols = resolve_named_indices(tuple(robot.joint_names), M1_PLANNER_JOINT_NAMES)
                    planner_joint = robot.data.joint_pos[:, joint_cols]
                    backend = get_robot_backend("m1")
                    geometry = backend.fk(root_pos, root_rpy, planner_joint, capsule_samples=int(backend.cfg.capsule_samples))
                    expanded = _expand_geometry_for_collision(geometry)
                    scanner = env.scene["semantic_height_scanner"]
                    resolution = float(getattr(getattr(scanner, "cfg", None).pattern_cfg, "resolution", 0.01))
                    terrain = _terrain_from_scanner(scanner, root_pos, resolution=resolution)
                    obstacle_mask = terrain.semantic_id > 0
                    from extension.parallelism.types import ParallelismTerrain
                    terrain = ParallelismTerrain(
                        height_w=torch.where(obstacle_mask, terrain.height_w, torch.full_like(terrain.height_w, -torch.inf)),
                        semantic_id=terrain.semantic_id,
                        valid_mask=terrain.valid_mask & obstacle_mask,
                        origin_w=terrain.origin_w,
                        yaw_w=terrain.yaw_w,
                        resolution=terrain.resolution,
                    )
                    _, bits = backend.collision_mask(terrain, expanded, backend.cfg)
                    hit = bits[0].any(dim=(0, 1))
                    collision_item["collision_shapes"] = [name for name, flag in zip((s.name for s in backend.collision_shapes), hit.tolist()) if flag]
                except Exception as exc:  # diagnostics must never change probe behavior
                    collision_item["collision_shapes_error"] = type(exc).__name__
                geometry_collision_trace.append(collision_item)
        small, large = wrapped.get_obstacle_presence()
        # Keep invalid and no-candidate frames too: those are exactly where
        # a swing can be interrupted or a support foot can lose contact.
        if True:
            actual_force = None
            contact_error = None
            measured_swing_count = 4  # fail closed when physical sensing is unavailable
            try:
                sensor = env.scene['contact_forces']
                sensor_forces = sensor.data.net_forces_w[0]
                contact_ids = list(resolve_named_indices(tuple(sensor.body_names), M1_SUPPORT_BODY_NAMES))
                wheel_force = sensor_forces[contact_ids]
                actual_force = wheel_force.detach().cpu().tolist()
                from ame_baseline.m1_probe_metrics import measured_swing_leg_count
                measured_swing_count = int(measured_swing_leg_count(
                    wheel_center_z=wheel_z,
                    wheel_force_norm=torch.linalg.vector_norm(wheel_force, dim=-1).unsqueeze(0),
                    ground_z=env.scene.env_origins[:, 2],
                    wheel_radius=float(M1_WHEEL_RADIUS_M),
                    minimum_lift_m=float(os.environ.get(
                        "M1_PROBE_MIN_LIFT_ABOVE_GROUND_M", "0.02"
                    )),
                    unload_force_n=float(os.environ.get(
                        "M1_PROBE_SWING_UNLOAD_FORCE_N", "10.0"
                    )),
                )[0].item())
                support_set = set(contact_ids)
                non_support_ids = [i for i in range(int(sensor_forces.shape[0])) if i not in support_set]
                if non_support_ids:
                    non_support_norm = torch.linalg.vector_norm(sensor_forces[non_support_ids], dim=-1)
                    non_support_max = float(non_support_norm.max().item())
                    non_support_force_max_n = max(non_support_force_max_n, non_support_max)
                    for body_id, force_norm in zip(non_support_ids, non_support_norm.detach().cpu().tolist()):
                        body_name = str(sensor.body_names[body_id])
                        non_support_force_by_body[body_name] = max(
                            float(non_support_force_by_body.get(body_name, 0.0)),
                            float(force_norm),
                        )
                    if non_support_max > 8.0:
                        non_support_contact_steps += 1
            except Exception as exc:
                contact_error = f'{type(exc).__name__}: {exc}'
            if bool(crossing_attempt[0].item()):
                max_swing_legs = max(max_swing_legs, measured_swing_count)
            articulation_com = None
            articulation_com_error = None
            try:
                # Use current PhysX masses, including randomized payloads,
                # and link COM positions rather than the root-link origin.
                com_positions = robot.data.body_com_pos_w[0]
                masses = robot.root_physx_view.get_masses()[0].to(com_positions)
                if not bool(torch.isfinite(masses).all()) or bool((masses < 0).any()) or float(masses.sum()) <= 0:
                    raise ValueError('invalid articulation masses')
                com = (masses[:, None] * com_positions).sum(dim=0) / masses.sum()
                if not bool(torch.isfinite(com).all()):
                    raise ValueError('nonfinite articulation COM')
                articulation_com = com.detach().cpu().tolist()
            except Exception as exc:
                articulation_com_error = f'{type(exc).__name__}: {exc}'
            samples.append({
                "env_origin_w_m": env.scene.env_origins[0].detach().cpu().tolist(),
                "geometry_collision": None if collision is None else bool(collision[0].item()),
                "episode_id": episode_id,
                "serial_phase_before_action": serial_phase_before_action,
                "step": step,
                "teacher_valid": bool(valid[0].item()),
                "teacher_reference_valid": bool(reference_valid[0].item()) if reference_valid is not None else False,
                "teacher_invalid_swing_fallback": bool(
                    getattr(wrapped, "_m1_invalid_swing_fallback", torch.zeros(1, dtype=torch.bool))[0].item()
                ),
                "teacher_active": bool(getattr(wrapped, "_m1_teacher_active", torch.zeros(1, dtype=torch.bool))[0].item()),
                "teacher_age": int(getattr(wrapped, "_m1_teacher_age", torch.zeros(1, dtype=torch.long))[0].item()),
                "teacher_elapsed": int(getattr(wrapped, "_m1_teacher_elapsed", torch.zeros(1, dtype=torch.long))[0].item()),
                "teacher_obstacle_hold": bool(getattr(wrapped, "_m1_teacher_obstacle_hold", torch.zeros(1, dtype=torch.bool))[0].item()),
                "teacher_obstacle_hold_steps": int(getattr(wrapped, "_m1_teacher_obstacle_hold_steps", torch.zeros(1, dtype=torch.long))[0].item()),
                "teacher_selected_collision": bool(getattr(wrapped, "_m1_teacher_selected_collision", torch.zeros(1, dtype=torch.bool))[0].item()),
                "strict_crossing_count": int(wrapped._m1_strict_crossing.crossing_count[0].item()),
                "strict_failed": bool(wrapped._m1_strict_crossing.failed[0].item()),
                "strict_recovery_pending": bool(wrapped._m1_strict_crossing.awaiting_recovery[0].item()),
                "strict_recovery_stable_steps": int(wrapped._m1_strict_crossing.stable_steps[0].item()),
                "strict_target_wheel": int(wrapped._m1_strict_crossing.target_wheel[0].item()),
                "strict_target_wheel_before_action": int(strict_target_before_action[0].item()),
                "strict_leg_target_mismatch": bool(strict_leg_mismatch[0].item()),
                "crossing_attempt_active": bool(crossing_attempt[0].item()),
                "debug_large_candidate": bool(getattr(wrapped, "_m1_debug_large_candidate", torch.zeros(1, dtype=torch.bool))[0].item()),
                "debug_expired": bool(getattr(wrapped, "_m1_debug_expired", torch.zeros(1, dtype=torch.bool))[0].item()),
                "action_max": float(action.abs().max().item()),
                "measured_joint_before_rad": measured_joint_before[0].cpu().tolist(),
                "decoded_joint_target_rad": decoded_target[0].detach().cpu().tolist(),
                "held_joint_target_rad": held_target[0].cpu().tolist(),
                "measured_joint_after_rad": robot.data.joint_pos[0, asset_ids].detach().cpu().tolist(),
                "leg_action_max": action[:, planner_cols].reshape(1, 4, 3).abs().amax(dim=-1)[0].tolist(),
                "measured_swing_leg_count": measured_swing_count,
                "selected_leg_action_max": selected_leg_action_max,
                "other_nonzero_leg_action_count": other_nonzero_leg_action_count,
                "serial_selected_leg": selected_leg,
                "phase_index": int(torch.as_tensor(reference.get("phase_index", [0])).reshape(-1)[0].item()),
                "contact_state": torch.as_tensor(reference.get("contact_state", [[True, True, True, True]])).reshape(-1, 4)[0].tolist(),
                "small_candidate": bool(small[0].item()),
                "large_candidate": bool(large[0].item()),
                "root_z_m": float(robot.data.root_pos_w[0, 2].item()),
                "root_x_m": float(robot.data.root_pos_w[0, 0].item()),
                "tilt_rad": float(tilt[0].item()),
                "roll_rad": float(roll[0].item()),
                "pitch_rad": float(pitch[0].item()),
                "articulation_com_w_m": articulation_com,
                "articulation_com_error": articulation_com_error,
                "wheel_z_m": wheel_z[0].tolist(),
                "wheel_xyz_w_m": robot.data.body_pos_w[0, wheel_ids].detach().cpu().tolist(),
                "actual_wheel_net_force_w_n": actual_force,
                "contact_measurement_error": contact_error,
                "done": bool(done[0].item()),
            })
            # Preserve failure evidence even if a bounded run times out.
            if os.environ.get("M1_PROBE_EMIT_SAMPLES", "0") == "1":
                print("M1_TEACHER_PHYSX_SAMPLE " + json.dumps(samples[-1], separators=(",", ":")), flush=True)
        if bool(done.any().item()):
            episode_id += 1
            wrapped.reset()
        if step % _PROGRESS_EVERY == 0 or step + 1 == int(args.num_steps):
            _emit_probe_progress(
                "control_step",
                step=step + 1,
                step_elapsed_s=round(time.perf_counter() - _step_started_at, 3),
                teacher_valid=bool(torch.as_tensor(valid).any().item()),
                strict_crossings=int(wrapped._m1_strict_crossing.crossing_count[0].item()),
                strict_failed=bool(wrapped._m1_strict_crossing.failed[0].item()),
            )

    # Verify the physical contract from measured force/geometry samples, not
    # from the configured leg sequence alone.  Each leg must unload, reach a
    # wheel-bottom clearance of obstacle-top + 5 cm, and regain contact after
    # that clearance while the command changes only one leg at a time.
    verified_legs = []
    for leg in range(4):
        leg_indices = [
            index for index, sample in enumerate(samples)
            if sample["serial_selected_leg"] == leg
            and sample["teacher_reference_valid"]
            and sample["crossing_attempt_active"]
            and sample["measured_swing_leg_count"] == 1
        ]
        leg_samples = [samples[index] for index in leg_indices]
        unloaded = any(
            sample["actual_wheel_net_force_w_n"] is not None
            and sum(value * value for value in sample["actual_wheel_net_force_w_n"][leg]) ** 0.5 <= 10.0
            for sample in leg_samples
        )
        clear_indices = [
            index for index, sample in enumerate(leg_samples)
            if sample["wheel_z_m"][leg] - float(M1_WHEEL_RADIUS_M) >= 0.15
        ]
        cleared = bool(clear_indices)
        touchdown = False
        if clear_indices:
            # Touchdown commonly lands on the first frame after the serial
            # handoff, when ``serial_selected_leg`` already names the next
            # leg. Scan a short global window instead of dropping that valid
            # contact from the preceding leg's evidence.
            last_clear_global = leg_indices[clear_indices[-1]]
            touchdown_window = max(
                9, int(os.environ.get("M1_PROBE_TOUCHDOWN_WINDOW_STEPS", "16"))
            )
            for sample in samples[last_clear_global + 1:last_clear_global + 1 + touchdown_window]:
                force = sample["actual_wheel_net_force_w_n"]
                if force is not None:
                    force_norm = sum(value * value for value in force[leg]) ** 0.5
                    touchdown |= force_norm > 10.0 and sample["tilt_rad"] <= float(os.environ.get("M1_STRICT_MAX_TILT_RAD", "0.30"))
        verified_legs.append(unloaded and cleared and touchdown)
    physical_single_leg_swing_verified = (
        max_swing_legs <= 1
        and strict_target_checked_steps > 0
        and strict_target_mismatch_steps == 0
        and set(serial_sequence_trace) >= {0, 1, 2, 3}
        and all(verified_legs)
    )
    print("M1_TEACHER_PHYSX_PROBE " + json.dumps({
        # Strict crossing event and safe balance recovery are reported as
        # separate outcomes; a crossing is not withheld because recovery is
        # still pending.
        "strict_any_crossing_verified": bool(
            wrapped._m1_strict_crossing.crossing_count[0].item() > 0
            and not wrapped._m1_strict_crossing.failed[0].item()
        ),
        "strict_crossing_count": wrapped._m1_strict_crossing.crossing_count.detach().cpu().tolist(),
        "strict_course_progress": wrapped._m1_strict_crossing.progress.detach().cpu().tolist(),
        "strict_recovery_pending": wrapped._m1_strict_crossing.awaiting_recovery.detach().cpu().tolist(),
        "strict_recovery_frames": wrapped._m1_strict_crossing.recovery_elapsed_frames.detach().cpu().tolist(),
        "strict_recovery_stable_steps": wrapped._m1_strict_crossing.stable_steps.detach().cpu().tolist(),
        "strict_failed": wrapped._m1_strict_crossing.failed.detach().cpu().tolist(),
        "obstacle_collision_bounds_w": obstacle_collision_bounds_w,
        "obstacle_geometry_error": obstacle_geometry_error,
        "verification_scope": "strict_crossing_event_and_recovery_are_separate",
        "effective_environment": {
            key: value for key, value in sorted(os.environ.items())
            if key.startswith(("M1_TEACHER_", "M1_PROBE_", "M1_STRICT_"))
        },
        "configured_seed": cfg.seed,
        "seed_explicitly_requested": probe_seed is not None,
        "steps": int(args.num_steps),
        "wheel_radius_m": float(M1_WHEEL_RADIUS_M),
        "wheel_names": list(M1_SUPPORT_BODY_NAMES),
        "probe_speed_m_s": probe_speed,
        "teacher_valid_steps": valid_steps,
        "teacher_reference_valid_steps": reference_valid_steps,
        "max_measured_swing_leg_count": max_swing_legs,
        "strict_target_checked_steps": strict_target_checked_steps,
        "strict_target_mismatch_steps": strict_target_mismatch_steps,
        "serial_sequence_trace": serial_sequence_trace,
        "single_leg_swing_sequence_verified": (
            max_swing_legs <= 1 and set(serial_sequence_trace) >= {0, 1, 2, 3}
        ),
        "all_legs_lift_clearance_touchdown_verified": physical_single_leg_swing_verified,
        "strict_target_and_teacher_leg_aligned": (
            strict_target_checked_steps > 0 and strict_target_mismatch_steps == 0
        ),
        "verified_legs": verified_legs,
        "max_wheel_bottom_m": max_wheel_bottom_m,
        "max_tilt_rad": max_tilt_rad,
        "geometry_collision_steps": geometry_collision_steps,
        "geometry_collision_trace": geometry_collision_trace[:40],
        "non_support_force_max_n": non_support_force_max_n,
        "non_support_contact_steps": non_support_contact_steps,
        "non_support_force_by_body": dict(sorted(non_support_force_by_body.items(), key=lambda item: item[1], reverse=True)[:12]),
        "strict_tracker": {
            key: getattr(wrapped._m1_strict_crossing, key).detach().cpu().tolist()
            for key in ("progress", "crossing_count", "recovery_elapsed_frames",
                        "awaiting_recovery", "failed")
        } if getattr(wrapped, "_m1_strict_crossing", None) is not None else None,
        "samples": samples,
    }), flush=True)
finally:
    if env is not None:
        env.close()
    app.close()
