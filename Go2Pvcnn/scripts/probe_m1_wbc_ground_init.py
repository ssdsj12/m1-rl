#!/usr/bin/env python3
"""Observe reset-time M1 wheel/ground contacts; this is not a stance or crossing test."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(PACKAGE / "rsl_rl"))

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--max_ticks", type=int, choices=range(1, 33), default=32)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()

launcher = AppLauncher(args)
env = None
try:
    import torch
    from isaaclab.envs import ManagerBasedRLEnv
    from isaaclab.terrains import MeshPlaneTerrainCfg

    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices

    cfg = M1AmeCrossLargeComplexEnvCfg()
    cfg.scene.num_envs = 1
    cfg.scene.env_spacing = 8.0
    cfg.scene.terrain.terrain_generator.sub_terrains = {
        "flat": MeshPlaneTerrainCfg(proportion=1.0)
    }
    cfg.scene.terrain.terrain_generator.num_rows = 1
    cfg.scene.terrain.terrain_generator.num_cols = 1
    cfg.scene.terrain.max_init_terrain_level = 0
    cfg.sim.device = str(args.device)
    cfg.sim.dt = 0.001
    cfg.decimation = 1
    cfg.seed = 7
    cfg.events.push_robot = None
    cfg.events.reset_base.params["pose_range"] = {
        "x": (0.0, 0.0), "y": (0.0, 0.0), "yaw": (0.0, 0.0)
    }
    cfg.events.reset_robot_joints.params["velocity_range"] = (0.0, 0.0)
    for actuator in cfg.scene.robot.actuators.values():
        actuator.stiffness = 0.0
        actuator.damping = 0.0

    env = ManagerBasedRLEnv(cfg=cfg)
    env.reset()
    robot = env.scene["robot"]
    sensor = env.scene["contact_forces"]
    wheel_names = tuple(M1_SUPPORT_BODY_NAMES)
    robot_wheel_ids = tuple(resolve_named_indices(tuple(robot.body_names), wheel_names))
    sensor_wheel_ids = tuple(resolve_named_indices(tuple(sensor.body_names), wheel_names))
    if len(robot_wheel_ids) != 4 or len(sensor_wheel_ids) != 4:
        raise RuntimeError("M1 wheel body-name mapping did not resolve exactly four wheels")
    if robot.is_fixed_base:
        raise RuntimeError("ground-contact probe requires a floating-base M1")

    dt = float(cfg.sim.dt)
    wheel_contact_views = {
        name: sensor._physics_sim_view.create_rigid_contact_view(
            f"/World/envs/env_0/Robot/{name}",
            filter_patterns=["/World/ground/terrain/mesh"],
            max_contact_data_count=128,
        )
        for name in wheel_names
    }
    native = robot.root_physx_view
    stiffness = native.get_dof_stiffnesses().clone()
    damping = native.get_dof_dampings().clone()
    if torch.count_nonzero(stiffness).item() or torch.count_nonzero(damping).item():
        raise RuntimeError("native implicit stiffness/damping is nonzero")

    zero_effort = torch.zeros_like(robot.data.joint_pos)
    robot.set_joint_effort_target(zero_effort)
    robot.write_data_to_sim()
    effort_readback = native.get_dof_actuation_forces().clone()
    if not torch.equal(effort_readback, zero_effort):
        raise RuntimeError("native explicit zero-effort initialization readback mismatch")

    def sample(label: str) -> dict:
        wheel_force = []
        contact_pair_count = []
        raw_normal_force = []
        minimum_separation = []
        for name in wheel_names:
            view = wheel_contact_views[name]
            force = view.get_net_contact_forces(dt=dt)
            nf, points, normals, separation, counts, starts = view.get_contact_data(dt=dt)
            wheel_force.append(torch.as_tensor(force).reshape(-1, 3)[0].detach().cpu().tolist())
            count_values = torch.as_tensor(counts).reshape(-1)
            contact_pair_count.append(int(count_values.sum().item()))
            normal_values = torch.as_tensor(nf).reshape(-1)
            separation_values = torch.as_tensor(separation).reshape(-1)
            raw_normal_force.append(float(normal_values.sum().item()))
            minimum_separation.append(
                float(separation_values.min().item()) if separation_values.numel() else None
            )
        force_norm = [sum(x * x for x in force) ** 0.5 for force in wheel_force]
        root_pos = robot.data.root_pos_w[0].detach().cpu().tolist()
        root_quat = robot.data.root_quat_w[0].detach().cpu().tolist()
        wheel_pos = robot.data.body_pos_w[0, list(robot_wheel_ids)].detach().cpu().tolist()
        return {
            "label": label,
            "sim_step": int(env.sim.current_time_step_index),
            "sim_time_s": float(env.sim.current_time),
            "wheel_names": list(wheel_names),
            "native_pair_count": contact_pair_count,
            "raw_normal_force_sum_n": raw_normal_force,
            "minimum_separation_m": minimum_separation,
            "native_pair_net_force_xyz_n": wheel_force,
            "native_pair_force_norm_n": force_norm,
            "cached_sensor_force_norm_n": torch.linalg.vector_norm(
                sensor.data.net_forces_w[0, list(sensor_wheel_ids)], dim=-1
            ).detach().cpu().tolist(),
            "root_pos_w_m": root_pos,
            "root_quat_wxyz": root_quat,
            "wheel_pos_w_m": wheel_pos,
        }

    before = sample("post_reset_before_physics_tick")
    trace = []
    after = before
    for tick in range(1, args.max_ticks + 1):
        env.sim.step(render=False)
        env.scene.update(dt)
        after = sample("after_raw_physics_tick")
        trace.append({
            "tick": tick,
            "force_norm_n": after["native_pair_force_norm_n"],
            "wheel_z_m": [position[2] for position in after["wheel_pos_w_m"]],
            "pair_count": after["native_pair_count"],
        })
        observed = sum(force > 1.0 for force in after["native_pair_force_norm_n"])
        if observed == 4:
            break
    if not all(torch.isfinite(torch.tensor(after["native_pair_net_force_xyz_n"])).flatten().tolist()):
        raise RuntimeError("nonfinite native wheel contact force")
    observed = sum(force > 1.0 for force in after["native_pair_force_norm_n"])
    print("M1_WBC_GROUND_INIT " + json.dumps({
        "scope": "initial_contact_observability_not_stance_or_crossing",
        "env_count": int(env.num_envs),
        "dt_s": dt,
        "native_pd_stiffness_max": float(stiffness.abs().max().item()),
        "native_pd_damping_max": float(damping.abs().max().item()),
        "explicit_zero_effort_readback_max_nm": float(effort_readback.abs().max().item()),
        "observed_wheel_count_over_1n": observed,
        "ticks_until_all_wheels_observed": tick if observed == 4 else None,
        "max_ticks": args.max_ticks,
        "before": before,
        "after": after,
        "trace": trace,
    }), flush=True)
    if observed != 4:
        raise RuntimeError(f"reset contact observability failed: only {observed}/4 wheels > 1 N")
finally:
    if env is not None:
        env.close()
    launcher.app.close()
