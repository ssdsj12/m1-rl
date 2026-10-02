#!/usr/bin/env python3
"""Direct PhysX probe for the M1 single-leg lift contract.

The probe deliberately bypasses PPO and the MPC manager.  It sends the same
16-column action contract used by the M1 AME task and records actual PhysX
wheel body positions, support contact forces, root roll/pitch, and joint
targets for each leg through a lift/hold/lower sequence.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for p in (ROOT, ROOT / "rsl_rl"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def parse_args():
    from isaaclab.app import AppLauncher

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num_envs", type=int, default=1)
    parser.add_argument("--steps_per_phase", type=int, default=30)
    parser.add_argument("--settle_steps", type=int, default=120)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--lift_hip", type=float, default=-0.30)
    parser.add_argument("--lift_knee", type=float, default=0.50)
    AppLauncher.add_app_launcher_args(parser)
    return parser.parse_args()


def main() -> int:
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    args = parse_args()
    from isaaclab.app import AppLauncher

    launcher = AppLauncher(args)
    app = launcher.app
    env = None
    try:
        import torch
        from isaaclab.envs import ManagerBasedRLEnv

        from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
        from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
        from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES
        from extension.parallelism.rl_adapter import resolve_named_indices, select_named_joint_state
        from extension.convention import extract_roll_pitch_batch

        torch.manual_seed(args.seed)
        cfg = M1AmeCrossLargeComplexEnvCfg()
        cfg.scene.num_envs = args.num_envs
        cfg.sim.device = str(args.device)
        cfg.seed = args.seed
        # Keep the normal semantic-course importer and terrain generator.  The
        # spawn tile has a protected flat center; replacing it with a plain
        # TerrainImporter would break the course importer's terrain movement
        # contract before the articulation is created.
        cfg.scene.env_spacing = 8.0
        cfg.events.push_robot = None
        cfg.events.reset_base.params["pose_range"] = {"x": (0., 0.), "y": (0., 0.), "yaw": (0., 0.)}
        cfg.events.reset_robot_joints.params["velocity_range"] = (0., 0.)
        if "M1_PROBE_LEG_STIFFNESS" in os.environ:
            cfg.scene.robot.actuators["legs"].stiffness = float(os.environ["M1_PROBE_LEG_STIFFNESS"])
        if "M1_PROBE_LEG_DAMPING" in os.environ:
            cfg.scene.robot.actuators["legs"].damping = float(os.environ["M1_PROBE_LEG_DAMPING"])
        cfg.commands.base_velocity.ranges.lin_vel_x = (0., 0.)
        cfg.commands.base_velocity.ranges.lin_vel_y = (0., 0.)
        cfg.commands.base_velocity.ranges.ang_vel_z = (0., 0.)
        cfg.commands.base_velocity.rel_standing_envs = 1.0

        env = ManagerBasedRLEnv(cfg=cfg)
        robot = env.scene["robot"]
        contact_sensor = env.scene["contact_forces"]
        env.reset()
        action_term = env.action_manager.get_term("JointPositionAction")
        asset_indices = resolve_named_indices(tuple(robot.joint_names), M1_ASSET_JOINT_NAMES)
        leg_cols = resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES)
        wheel_body_ids = list(resolve_named_indices(tuple(robot.body_names), M1_SUPPORT_BODY_NAMES))
        sensor_wheel_ids = list(resolve_named_indices(tuple(contact_sensor.body_names), M1_SUPPORT_BODY_NAMES))
        if len(wheel_body_ids) != 4 or len(sensor_wheel_ids) != 4:
            raise RuntimeError(
                f"expected 4 M1 support bodies, got robot={wheel_body_ids} sensor={sensor_wheel_ids}"
            )
        print("M1_PROBE_CONTRACT", json.dumps({
            "asset_joint_names": list(M1_ASSET_JOINT_NAMES),
            "robot_joint_names": list(robot.joint_names),
            "planner_joint_names": list(M1_PLANNER_JOINT_NAMES),
            "leg_columns": list(leg_cols),
            "wheel_body_names": [robot.body_names[i] for i in wheel_body_ids],
            "wheel_body_ids": wheel_body_ids,
            "contact_sensor_wheel_ids": sensor_wheel_ids,
            "fixed_base": bool(robot.is_fixed_base),
        }), flush=True)
        if robot.is_fixed_base:
            raise RuntimeError("M1 probe requires floating base")

        def snapshot(label: str, leg: int, phase_step: int):
            root = robot.data.root_pos_w.detach()
            roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
            wheel_pos = robot.data.body_pos_w[:, wheel_body_ids]
            wheel_vel = robot.data.body_vel_w[:, wheel_body_ids, :3]
            joint_pos = select_named_joint_state(
                robot.data.joint_pos,
                source_names=tuple(robot.joint_names),
                selected_names=M1_PLANNER_JOINT_NAMES,
            )
            # processed_actions are kept in the explicit 16-column asset
            # order; using the articulation's lexicographic order here would
            # report the wrong leg even though PhysX receives the right IDs.
            joint_target = select_named_joint_state(
                env.action_manager.get_term("JointPositionAction").processed_actions,
                source_names=M1_ASSET_JOINT_NAMES,
                selected_names=M1_PLANNER_JOINT_NAMES,
            )
            # The articulation and contact sensor maintain different body
            # orders.  Always use the sensor's own name-resolved indices for
            # forces; robot body IDs are only valid for robot.data positions.
            force = contact_sensor.data.net_forces_w[:, sensor_wheel_ids]
            force_norm = torch.linalg.vector_norm(force, dim=-1)
            out = {
                "label": label,
                "leg": int(leg),
                "phase_step": int(phase_step),
                "root_z_m": float(root[0, 2]),
                "root_xy_m": root[0, :2].tolist(),
                "roll_rad": float(roll[0]),
                "pitch_rad": float(pitch[0]),
                "wheel_z_m": wheel_pos[0, :, 2].tolist(),
                "wheel_xy_m": wheel_pos[0, :, :2].tolist(),
                "wheel_vz_mps": wheel_vel[0, :, 2].tolist(),
                "support_force_norm_n": force_norm[0].tolist(),
                "support_contact": (force_norm[0] > 1.0).tolist(),
                "joint_pos_rad": joint_pos[0].tolist(),
                "joint_target_rad": joint_target[0].tolist(),
            }
            if label == "settled":
                out["env_origin_m"] = env.scene.env_origins[0].detach().cpu().tolist()
                out["contact_sensor_body_names"] = list(contact_sensor.body_names)
            print("M1_PROBE_SAMPLE " + json.dumps(out), flush=True)
            return out

        zero = torch.zeros(args.num_envs, 16, device=cfg.sim.device)
        all_records = []
        for leg in range(4):
            # Each leg is a standalone trial.  Resetting here avoids a
            # previous leg's root drift contaminating the next leg's lift
            # height or posture verdict.
            env.reset()
            for settle in range(args.settle_steps):
                env.step(zero)
            baseline = snapshot("settled", leg, 0)
            # Asset order is [abad, hip, knee, foot] per leg.  At the M1
            # standing pose, hip -0.30 + knee +0.50 raises the wheel center
            # by about 8.4 cm in native M1 FK; the other three legs remain at
            # their default targets to keep a support polygon.
            lift = torch.zeros_like(zero)
            base = 4 * leg
            lift[:, base + 1] = float(args.lift_hip)
            lift[:, base + 2] = float(args.lift_knee)
            stance_knee = float(os.environ.get("M1_PROBE_STANCE_KNEE_ACTION", "0"))
            stance_hip = float(os.environ.get("M1_PROBE_STANCE_HIP_ACTION", "0"))
            if stance_knee or stance_hip:
                for stance_leg in range(4):
                    if stance_leg == leg:
                        continue
                    stance_base = 4 * stance_leg
                    lift[:, stance_base + 1] = stance_hip
                    lift[:, stance_base + 2] = stance_knee
            opposite_knee = float(os.environ.get("M1_PROBE_OPPOSITE_KNEE_ACTION", "0"))
            if opposite_knee:
                opposite_leg = (3, 2, 1, 0)[leg]
                lift[:, 4 * opposite_leg + 2] = opposite_knee
            trial_records = []
            for phase, label in (("lift", "lift"), ("hold", "hold"), ("lower", "lower")):
                count = args.steps_per_phase
                for step in range(count):
                    if phase == "lift":
                        cmd = lift * min(1.0, float(step + 1) / max(1, count // 2))
                    elif phase == "hold":
                        cmd = lift
                    else:
                        cmd = lift * max(0.0, 1.0 - float(step + 1) / max(1, count))
                    env.step(cmd)
                    if step in (0, count // 2, count - 1):
                        record = snapshot(label, leg, step)
                        all_records.append(record)
                        trial_records.append(record)
            # Give the body one short settling window before the next leg.
            for _ in range(max(15, args.settle_steps // 3)):
                env.step(zero)
            active_records = [r for r in trial_records if r["label"] in ("lift", "hold")]
            active_z = [float(r["wheel_z_m"][leg]) for r in active_records]
            active_tilt = [max(abs(float(r["roll_rad"])), abs(float(r["pitch_rad"]))) for r in active_records]
            active_support = [sum(bool(v) for i, v in enumerate(r["support_contact"]) if i != leg) for r in active_records]
            print("M1_PROBE_TRIAL " + json.dumps({
                "leg": leg,
                "baseline_wheel_z_m": float(baseline["wheel_z_m"][leg]),
                "max_lift_or_hold_wheel_z_m": max(active_z) if active_z else None,
                "max_lift_or_hold_delta_m": max(active_z) - float(baseline["wheel_z_m"][leg]) if active_z else None,
                "max_abs_root_tilt_rad": max(active_tilt) if active_tilt else None,
                "min_supporting_wheels_contact": min(active_support) if active_support else None,
            }), flush=True)

        print("M1_PROBE_DONE " + json.dumps({"samples": len(all_records)}), flush=True)
        return 0
    finally:
        if env is not None:
            env.close()
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
