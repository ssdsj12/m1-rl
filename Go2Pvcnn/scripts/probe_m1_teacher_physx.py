#!/usr/bin/env python3
"""Short M1 teacher-driven PhysX probe for the 10 cm obstacle profile."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

THIS_FILE = Path(__file__).resolve()
PACKAGE_ROOT = THIS_FILE.parent.parent
RSL_RL_ROOT = PACKAGE_ROOT / "rsl_rl"
for path in (PACKAGE_ROOT, RSL_RL_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


parser = argparse.ArgumentParser()
parser.add_argument("--num_steps", type=int, default=320)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if str(args.device).startswith("cuda"):
    import torch
    torch.cuda.set_device(int(str(args.device).split(":")[-1]))
launcher = AppLauncher(args)
app = launcher.app
env = None
try:
    import torch
    from isaaclab.envs import ManagerBasedRLEnv

    from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_RADIUS_M
    from extension.trajectory_manager_factory import attach_trajectory_manager
    from extension.convention import extract_roll_pitch_batch, extract_yaw_batch
    from extension.parallelism.robot_backend import get_robot_backend
    from tracking.mdp.policy_geometry_rewards import _expand_geometry_for_collision, _terrain_from_scanner

    cfg = M1AmeCrossLargeComplexEnvCfg()
    cfg.scene.num_envs = 1
    cfg.scene.env_spacing = 8.0
    cfg.sim.device = str(args.device)
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
    attach_trajectory_manager(env, cfg, device=str(args.device))
    wrapped = AmeRslRlEnvWrapper(env, clip_actions=100.0)
    wrapped.reset()

    robot = env.scene["robot"]
    wheel_ids = list(resolve_named_indices(tuple(robot.body_names), M1_SUPPORT_BODY_NAMES))
    # The teacher action is in M1 asset order; Isaac joint names are alphabetical.
    planner_cols = resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES)
    valid_steps = 0
    max_swing_legs = 0
    max_wheel_bottom_m = float("-inf")
    max_tilt_rad = 0.0
    geometry_collision_steps = 0
    geometry_collision_trace = []
    samples = []
    for step in range(int(args.num_steps)):
        leg_groups = torch.zeros((1, 4), dtype=torch.bool, device=cfg.sim.device)
        action, valid = wrapped.get_mpc_teacher_action()
        reference = env._trajectory_manager.current_reference(frame_offset=1)
        if action is None:
            action = torch.zeros((1, 16), device=cfg.sim.device)
            valid = torch.zeros(1, dtype=torch.bool, device=cfg.sim.device)
        # Match the runner's executed teacher action: the crossing teacher
        # drives the forward wheel channels from the commanded base velocity.
        # Leaving them at zero only tests a stationary leg lift against a
        # fixed course, not an actual approach/crossing.
        action[:, 3::4] = 0.10
        if bool(valid.any().item()):
            valid_steps += 1
            leg_groups = action[:, planner_cols].reshape(1, 4, 3).abs().amax(dim=-1) > 1.0e-4
            max_swing_legs = max(max_swing_legs, int(leg_groups.sum(dim=-1).max().item()))
        _, _, done, _ = wrapped.step(action)
        roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
        tilt = torch.maximum(roll.abs(), pitch.abs())
        max_tilt_rad = max(max_tilt_rad, float(tilt[0].item()))
        wheel_z = robot.data.body_pos_w[:, wheel_ids, 2]
        max_wheel_bottom_m = max(max_wheel_bottom_m, float((wheel_z - float(M1_WHEEL_RADIUS_M)).max().item()))
        names = list(env.reward_manager.active_terms)
        if "parallelism_geometry_collision" in names:
            collision = env.reward_manager._step_reward[:, names.index("parallelism_geometry_collision")] != 0
            geometry_collision_steps += int(collision.sum().item())
            if bool(collision.any().item()):
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
        if bool(valid.any().item()) or bool(small.any().item()) or step % 80 == 0:
            samples.append({
                "step": step,
                "teacher_valid": bool(valid[0].item()),
                "action_max": float(action.abs().max().item()),
                "leg_action_max": action[:, planner_cols].reshape(1, 4, 3).abs().amax(dim=-1)[0].tolist(),
                "commanded_leg_count": int(leg_groups.sum().item()) if action is not None else 0,
                "phase_index": int(torch.as_tensor(reference.get("phase_index", [0])).reshape(-1)[0].item()),
                "contact_state": torch.as_tensor(reference.get("contact_state", [[True, True, True, True]])).reshape(-1, 4)[0].tolist(),
                "small_candidate": bool(small[0].item()),
                "large_candidate": bool(large[0].item()),
                "root_z_m": float(robot.data.root_pos_w[0, 2].item()),
                "root_x_m": float(robot.data.root_pos_w[0, 0].item()),
                "tilt_rad": float(tilt[0].item()),
                "wheel_z_m": wheel_z[0].tolist(),
                "done": bool(done[0].item()),
            })
        if bool(done.any().item()):
            wrapped.reset()

    print("M1_TEACHER_PHYSX_PROBE " + json.dumps({
        "steps": int(args.num_steps),
        "teacher_valid_steps": valid_steps,
        "max_commanded_leg_count": max_swing_legs,
        "max_wheel_bottom_m": max_wheel_bottom_m,
        "max_tilt_rad": max_tilt_rad,
        "geometry_collision_steps": geometry_collision_steps,
        "geometry_collision_trace": geometry_collision_trace[:40],
        "samples": samples,
    }), flush=True)
finally:
    if env is not None:
        env.close()
    app.close()
