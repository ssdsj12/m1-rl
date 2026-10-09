"""Run bounded physical M1 reward/drive probes without training a policy."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from train_m1_cross_large_complex_ame import _parse_args


def main():
    args = _parse_args()
    from isaaclab.app import AppLauncher
    launcher = AppLauncher(args)
    env = None
    try:
        import torch
        import isaaclab.sim as sim_utils
        from isaaclab.assets import RigidObjectCfg
        from isaaclab.envs import ManagerBasedRLEnv
        from isaaclab.terrains import TerrainImporter
        from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
        from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
        from ame_baseline import m1_ame_rewards as m1_rewards
        from extension.parallelism.m1_kinematics import M1_WHEEL_JOINT_NAMES
        from extension.parallelism.rl_adapter import resolve_named_indices
        from extension.parallelism.rl_adapter import select_named_joint_state
        from extension.parallelism.robot_backend import get_robot_backend
        from extension.convention import extract_roll_pitch_batch, extract_yaw_batch
        from tracking.mdp.policy_geometry_rewards import _terrain_from_scanner, _expand_geometry_for_collision
        from pxr import Usd, UsdPhysics, UsdGeom
        cfg = M1AmeCrossLargeComplexEnvCfg()
        cfg.scene.num_envs = args.num_envs
        # Match evaluation: the 600-step path must not reach a neighbor's
        # scanner-visible but cross-environment collision-filtered obstacle.
        cfg.scene.env_spacing = 8.0
        cfg.sim.device = args.device
        cfg.seed = args.seed
        if "PROBE_WHEEL_DAMPING" in os.environ:
            cfg.scene.robot.actuators["wheels"].damping = float(os.environ["PROBE_WHEEL_DAMPING"])
        # Isolate rolling from the training-time external push disturbance.
        cfg.events.push_robot = None
        cfg.events.reset_base.params["pose_range"] = {"x": (0., 0.), "y": (0., 0.), "yaw": (0., 0.)}
        cfg.events.reset_robot_joints.params["velocity_range"] = (0., 0.)
        # Optional signal calibration: match the commanded velocity to this
        # probe's forward wheel actions, not a random training-time command.
        if "PROBE_COMMAND_X" in os.environ:
            probe_command_x = float(os.environ["PROBE_COMMAND_X"])
            if not .1 < probe_command_x <= 1.:
                raise ValueError("PROBE_COMMAND_X must be finite and in (0.1, 1.0]")
            cfg.curriculum.lin_vel_cmd_levels = None
            cfg.commands.base_velocity.ranges.lin_vel_x = (probe_command_x, probe_command_x)
            cfg.commands.base_velocity.ranges.lin_vel_y = (0., 0.)
            cfg.commands.base_velocity.ranges.ang_vel_z = (0., 0.)
            cfg.commands.base_velocity.rel_standing_envs = 0.
            cfg.commands.base_velocity.resampling_time_range = (1000., 1000.)
        scenario = os.environ.get("PROBE_SCENARIO", "flat")
        obstacle_height = float(os.environ.get("PROBE_OBSTACLE_HEIGHT_M", "0.05"))
        if not 0.0 < obstacle_height <= 0.30:
            raise ValueError("PROBE_OBSTACLE_HEIGHT_M must be in (0, 0.30]")
        if scenario in ("flat", "small_contact"):
            cfg.scene.terrain.class_type = TerrainImporter
            cfg.scene.terrain.terrain_type = "plane"
            cfg.scene.terrain.terrain_generator = None
            paths = ["/World/ground"]
            semantic_ids = {"/World/ground": 0}
            if scenario == "small_contact":
                cfg.scene.probe_obstacle = RigidObjectCfg(
                    prim_path="{ENV_REGEX_NS}/ProbeObstacle",
                    spawn=sim_utils.CuboidCfg(
                        size=(.20, 1.20, obstacle_height),
                        rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
                        collision_props=sim_utils.CollisionPropertiesCfg(),
                    ),
                    init_state=RigidObjectCfg.InitialStateCfg(pos=(1.0, 0.0, obstacle_height / 2)),
                )
                for index in range(args.num_envs):
                    path = f"/World/envs/env_{index}/ProbeObstacle"
                    paths.append(path)
                    semantic_ids[path] = 1
            cfg.scene.semantic_height_scanner.mesh_prim_paths = paths
            cfg.scene.semantic_height_scanner.mesh_semantic_ids = semantic_ids
        env = ManagerBasedRLEnv(cfg=cfg)
        wrapped = AmeRslRlEnvWrapper(env)
        robot = env.scene["robot"]
        print("M1_PHYSICS fixed_base=" + str(robot.is_fixed_base), flush=True)
        print("M1_MASS_KG", robot.root_physx_view.get_masses().sum(-1).tolist(), flush=True)
        assert not robot.is_fixed_base, "M1 training requires a floating base"
        for prim in env.sim.stage.Traverse():
            if "env_0/Robot" in str(prim.GetPath()) and (prim.GetTypeName() == "PhysicsFixedJoint" or prim.GetName() == "BASE_LINK"):
                print("M1_PHYSICS_PRIM", str(prim.GetPath()), [(a.GetName(), str(a.Get())) for a in prim.GetAttributes() if "kinematic" in a.GetName().lower() or "enabled" in a.GetName().lower()], flush=True)
        policy, extras = wrapped.get_observations()
        assert policy.shape == (args.num_envs, 1589), policy.shape
        assert extras["observations"]["critic"].shape == (args.num_envs, 1592)
        assert wrapped.num_actions == 16
        term = env.action_manager.get_term("JointPositionAction")
        assert tuple(term._joint_names) == cfg.asset_joint_names
        assert len(term._leg_ids) == 12 and len(term._wheel_ids) == 4
        print("M1_CONTRACT " + json.dumps({"policy": list(policy.shape), "critic": list(extras["observations"]["critic"].shape), "actions": wrapped.num_actions, "leg_ids": term._leg_ids, "wheel_ids": term._wheel_ids, "joint_names": robot.joint_names, "body_names": robot.body_names}), flush=True)
        print("M1_DRIVE " + json.dumps({"wheel_effort_limits": robot.data.joint_effort_limits[0, term._wheel_ids].tolist(), "wheel_velocity_limits": robot.data.joint_vel_limits[0, term._wheel_ids].tolist()}), flush=True)
        for prim in env.sim.stage.Traverse():
            if prim.GetName() in M1_WHEEL_JOINT_NAMES and "env_0/" in str(prim.GetPath()):
                joint = UsdPhysics.RevoluteJoint(prim)
                print("M1_WHEEL_AXIS", prim.GetName(), joint.GetAxisAttr().Get(), joint.GetLocalRot0Attr().Get(), flush=True)
                print("M1_WHEEL_PROPERTIES", prim.GetName(), [(a.GetName(), str(a.Get())) for a in prim.GetAttributes() if any(key in a.GetName().lower() for key in ("friction", "damping", "stiffness", "armature", "maxforce", "type"))], flush=True)
        print("M1_ACTUATOR_PROPERTIES", {name: {key: getattr(actuator, key).tolist() for key in ("stiffness", "damping", "friction")} for name, actuator in robot.actuators.items()}, flush=True)
        print("M1_PHYSX_DRIVE", robot.root_physx_view.get_dof_stiffnesses()[0].tolist(), robot.root_physx_view.get_dof_dampings()[0].tolist(), flush=True)
        bbox_cache = UsdGeom.BBoxCache(0, ["default", "render", "proxy"])
        for prim in Usd.PrimRange.Stage(env.sim.stage, Usd.TraverseInstanceProxies()):
            if "env_0/Robot" in str(prim.GetPath()) and "FOOT_LINK" in str(prim.GetPath()) and prim.HasAPI(UsdPhysics.CollisionAPI):
                print("M1_WHEEL_COLLIDER", str(prim.GetPath()), prim.GetTypeName(), str(bbox_cache.ComputeLocalBound(prim).GetRange()), [(a.GetName(), str(a.Get())) for a in prim.GetAttributes() if any(key in a.GetName().lower() for key in ("approximation", "axis", "radius", "height", "xformop"))], flush=True)
                if prim.IsA(UsdGeom.Mesh):
                    import numpy as np
                    points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get())
                    print("M1_WHEEL_MESH", str(prim.GetPath()), points.shape, points.min(axis=0).tolist(), points.max(axis=0).tolist(), str(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)), flush=True)
        print("M1_INERTIAS", robot.root_physx_view.get_inertias()[0].tolist(), flush=True)
        records, progress, resets = [], [], 0
        backend = get_robot_backend("m1")
        shape_collision_counts = torch.zeros(len(backend.cfg.official_collision_shapes), device=args.device)
        geometry_column = env.reward_manager.active_terms.index("parallelism_geometry_collision")
        event_records = []
        event_limit = int(os.environ.get("PROBE_EVENT_LIMIT", "0"))
        sensor = env.scene["contact_forces"]
        sensor_body_indices = {str(name): index for index, name in enumerate(sensor.body_names)}
        stage_reporter_thresholds = {}
        for prim in env.sim.stage.Traverse():
            path = str(prim.GetPath())
            if not event_limit or "env_0/Robot" not in path or not any(name in path for name in ("FBL_KNEE_LINK", "FAR_KNEE_LINK")):
                continue
            attrs = {}
            for attr in prim.GetAttributes():
                if "threshold" in attr.GetName().lower() or "contact" in attr.GetName().lower():
                    value = attr.Get()
                    if value is not None:
                        attrs[attr.GetName()] = str(value)
            if attrs:
                stage_reporter_thresholds[path] = attrs
        wheel_body_ids = list(resolve_named_indices(robot.body_names, m1_rewards.M1_SUPPORT_BODY_NAMES))
        max_wheel_center_z = float(robot.data.body_pos_w[:, wheel_body_ids, 2].max())
        small_near_steps = 0
        torch.manual_seed(args.seed)
        action_noise_std = float(os.environ.get("PROBE_ACTION_STD", "0"))
        start_pos = robot.data.root_pos_w.clone()
        for step in range(args.max_iterations):
            # Roll forward with all four wheels; legs hold M1 default pose.
            action = torch.zeros(args.num_envs, 16, device=args.device)
            action[:, term._wheel_columns] = min(.4, .4 * step / 100.)
            if action_noise_std:
                action += action_noise_std * torch.randn_like(action)
            obs, reward, done, _ = wrapped.step(action)
            assert bool(torch.isfinite(obs).all()) and bool(torch.isfinite(reward).all()), "nonfinite probe observation/reward"
            values = env.reward_manager._step_reward.clone()
            assert bool(torch.isfinite(values).all()), "nonfinite per-term reward"
            records.append(values)
            if scenario == "small_contact" and bool((values[:, geometry_column] != 0).any()):
                # Diagnose remaining proxy collisions without weakening the reward.
                scanner = env.scene["semantic_height_scanner"]
                terrain = _terrain_from_scanner(scanner, robot.data.root_pos_w, resolution=float(scanner.cfg.pattern_cfg.resolution))
                roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
                rpy = torch.stack((roll, pitch, extract_yaw_batch(robot.data.root_quat_w)), dim=-1)
                joints = select_named_joint_state(robot.data.joint_pos, source_names=tuple(robot.joint_names), selected_names=backend.planner_joint_names)
                geometry = backend.fk(robot.data.root_pos_w, rpy, joints, capsule_samples=int(backend.cfg.capsule_samples))
                _, bits = backend.collision_mask(terrain, _expand_geometry_for_collision(geometry), backend.cfg)
                shape_collision_counts += bits.flatten(1, 2).any(dim=1).sum(dim=0)
                if len(event_records) < event_limit:
                    from m1_probe_diagnostics import knee_hit_records
                    assert not bool(done.any()), "Event snapshots must not mix auto-reset states"
                    event_records.extend(knee_hit_records(
                        robot, sensor, geometry, terrain, backend, bits,
                        step=step, env_origins=env.scene.env_origins,
                        limit=event_limit - len(event_records),
                    ))
            resets += int(done.sum().item())
            progress.append((robot.data.root_pos_w[:, 0] - start_pos[:, 0]).mean().item())
            max_wheel_center_z = max(
                max_wheel_center_z,
                float(robot.data.body_pos_w[:, wheel_body_ids, 2].max()),
            )
            if scenario == "small_contact":
                small_near_steps += int(m1_rewards._small_obstacle_wheels(env).any(dim=-1).sum())
        stacked = torch.stack(records)
        # Root progress alone can leave the rear wheels before the obstacle.
        # Report all-wheel clearance independently of the historical contact gate.
        wheel_x = robot.data.body_pos_w[:, wheel_body_ids, 0] - env.scene.env_origins[:, None, 0]
        min_wheel_x = wheel_x.amin(dim=-1)
        all_wheels_past = min_wheel_x > 1.10 + cfg.wheel_radius_m
        print("M1_PROBE_CROSSING " + json.dumps({
            "scenario": scenario, "obstacle_height_m": obstacle_height,
            "min_wheel_center_x_m": min_wheel_x.tolist(),
            "all_wheels_past_obstacle_rate": float(all_wheels_past.float().mean()),
            "resets": resets,
        }), flush=True)
        print("M1_PROBE_COLLISION_SHAPES " + json.dumps({
            spec.name: int(count) for spec, count in zip(backend.cfg.official_collision_shapes, shape_collision_counts)
            if int(count) > 0
        }), flush=True)
        print("M1_PROBE_EVENT_DIAGNOSTICS " + json.dumps({
            "event_limit": event_limit,
            "records": event_records,
            "sensor_body_names": list(sensor.body_names),
            "sensor_selected_body_indices": sensor_body_indices,
            "sensor_history_length": int(sensor.cfg.history_length),
            "sensor_update_period_s": float(sensor.cfg.update_period),
            "physics_dt_s": float(cfg.sim.dt), "decimation": int(cfg.decimation),
            "env_spacing_m": float(cfg.scene.env_spacing),
            "filter_collisions": bool(cfg.scene.filter_collisions),
            "stage_reporter_thresholds": stage_reporter_thresholds,
        }), flush=True)
        summary = {name: {"mean": float(stacked[..., i].mean()), "p95_abs": float(stacked[..., i].abs().quantile(.95)), "nonzero": int((stacked[..., i] != 0).sum())} for i, name in enumerate(env.reward_manager.active_terms)}
        print("M1_PROBE " + json.dumps({"scenario": scenario, "steps": args.max_iterations, "resets": resets, "command_x_override": os.environ.get("PROBE_COMMAND_X"), "mean_forward_displacement_m": progress[-1], "max_wheel_center_z_m": max_wheel_center_z, "small_near_env_steps": small_near_steps, "rewards": summary}), flush=True)
        print("M1_END_STATE", robot.data.root_pos_w.tolist(), "wheel_vel", robot.data.joint_vel[:, term._wheel_ids].tolist(), flush=True)
        print("M1_END_JOINTS", robot.data.joint_pos[0].tolist(), "torques", robot.data.applied_torque[0].tolist(), "effort_limits", robot.data.joint_effort_limits[0].tolist(), flush=True)
        print("M1_END_BODIES", robot.data.body_pos_w[0].tolist(), "contact_forces", env.scene["contact_forces"].data.net_forces_w[0].tolist(), flush=True)
        print("M1_END_LIMITS", robot.data.joint_pos_limits[0].tolist(), flush=True)
        if scenario == "flat" and args.max_iterations >= 300:
            assert resets == 0 and progress[-1] > .2, "M1 failed the flat forward rolling gate"
            for name in ("undesired_contacts", "parallelism_geometry_collision"):
                column = env.reward_manager.active_terms.index(name)
                assert float((stacked[100:, :, column] != 0).float().mean()) < .05, f"M1 drags body parts on flat ground: {name}"
        if scenario == "small_contact" and args.max_iterations >= 300:
            assert resets == 0 and progress[-1] > 1.2, "M1 failed to roll past the small contact probe"
            assert max_wheel_center_z > .12 and small_near_steps > 0, "M1 never reached/climbed the small obstacle"
            column = env.reward_manager.active_terms.index("parallelism_geometry_collision")
            assert float((stacked[..., column] != 0).float().mean()) < .05, "support-wheel contact was scored as body collision"
        print("M1_PROBE_COMPLETE", flush=True)
    except BaseException:
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        raise
    finally:
        if env is not None:
            env.close()
        launcher.app.close()


if __name__ == "__main__":
    main()
