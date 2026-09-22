"""Fixed-seed flat/small-box/large-box policy evaluation, with no training."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from train_m1_cross_large_complex_ame import _parse_args


def main():
    args = _parse_args()
    if not args.checkpoint:
        raise ValueError("Evaluation requires --checkpoint")
    from isaaclab.app import AppLauncher
    launcher = AppLauncher(args)
    simulation_app = launcher.app
    env = None
    try:
        import torch
        import isaaclab.sim as sim_utils
        from isaaclab.assets import RigidObjectCfg
        from isaaclab.terrains import TerrainImporter
        from isaaclab.envs import ManagerBasedRLEnv
        from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
        from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
        from ame_baseline.actor_critic_ame import ActorCriticAME
        from ame_baseline.m1_evaluation_metrics import EpisodeMetrics, collision_from_rewards
        cfg = M1AmeCrossLargeComplexEnvCfg()
        cfg.sim.enable_cameras = True
        cfg.scene.num_envs = args.num_envs
        cfg.scene.env_spacing = 8.0
        cfg.sim.device = args.device
        cfg.seed = args.seed
        cfg.episode_length_s = max(20., args.max_iterations * .02 + 1.)
        cfg.curriculum.lin_vel_cmd_levels = None
        cfg.curriculum.terrain_levels = None
        cfg.events.push_robot = None
        cfg.events.reset_base.params["pose_range"] = {"x": (0., 0.), "y": (0., 0.), "yaw": (0., 0.)}
        cfg.events.reset_robot_joints.params["velocity_range"] = (0., 0.)
        cfg.commands.base_velocity.ranges.lin_vel_x = (.5, .5)
        cfg.commands.base_velocity.ranges.lin_vel_y = (0., 0.)
        cfg.commands.base_velocity.ranges.ang_vel_z = (0., 0.)
        cfg.commands.base_velocity.rel_standing_envs = 0.
        cfg.commands.base_velocity.resampling_time_range = (100., 100.)
        cfg.scene.terrain.class_type = TerrainImporter
        cfg.scene.terrain.terrain_type = "plane"
        cfg.scene.terrain.terrain_generator = None
        scenario = os.environ.get("EVAL_SCENARIO", "small")
        if args.semantic_crossing:
            scenario = "small"
        if scenario not in ("flat", "small", "large"):
            raise ValueError("EVAL_SCENARIO must be flat, small or large")
        paths = ["/World/ground"]
        semantic_ids = {paths[0]: 0}
        if scenario != "flat":
            height = (args.obstacle_threshold if args.obstacle_threshold is not None else .10) if scenario == "small" else .80
            length = .20 if scenario == "small" else .60
            cfg.scene.eval_obstacle = RigidObjectCfg(
                prim_path="{ENV_REGEX_NS}/EvalObstacle",
                spawn=sim_utils.CuboidCfg(size=(length, 1.2, height),
                    rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
                    collision_props=sim_utils.CollisionPropertiesCfg()),
                init_state=RigidObjectCfg.InitialStateCfg(pos=(1.5, 0., height / 2)),
            )
            for i in range(args.num_envs):
                path = f"/World/envs/env_{i}/EvalObstacle"
                paths.append(path)
                semantic_ids[path] = 1 if scenario == "small" else 2
        cfg.scene.semantic_height_scanner.mesh_prim_paths = paths
        cfg.scene.semantic_height_scanner.mesh_semantic_ids = semantic_ids
        env = ManagerBasedRLEnv(cfg=cfg)
        # Give the WebRTC viewport an explicit camera in headless livestream mode.
        env.sim.set_camera_view((4.0, -4.0, 2.8), (1.0, 0.0, 0.45))
        wrapped = AmeRslRlEnvWrapper(env)
        robot = env.scene["robot"]
        assert not robot.is_fixed_base
        obs, extras = wrapped.get_observations()
        checkpoint = torch.load(args.checkpoint, map_location=args.device, weights_only=False)
        expected = (obs.shape[-1], extras["observations"]["critic"].shape[-1], 16)
        saved = tuple(checkpoint.get(key) for key in ("ame_num_actor_obs", "ame_num_critic_obs", "ame_num_actions"))
        if saved != expected:
            raise ValueError(f"Checkpoint {saved} incompatible with M1 evaluation {expected}")
        model = ActorCriticAME(*expected).to(args.device)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        episodes = EpisodeMetrics(args.num_envs, args.device, scenario)
        with torch.inference_mode():
            for _ in range(args.max_iterations):
                # Advance Kit/rendering so the WebRTC viewport receives frames.
                simulation_app.update()
                before = (robot.data.root_pos_w - env.scene.env_origins).clone()
                obs, _, done, _ = wrapped.step(model.act_inference(obs))
                geometry = collision_from_rewards(env.reward_manager._step_reward, env.reward_manager.active_terms)
                episodes.update(before, robot.data.root_pos_w - env.scene.env_origins, done,
                                geometry, env.termination_manager.get_term("nonfinite_robot_state"),
                                terminated=env.termination_manager.terminated)
                if not bool(episodes.alive.any()):
                    break
        metrics = {
            "scenario": scenario, "checkpoint": str(Path(args.checkpoint).resolve()),
            "seed": args.seed, "episodes": args.num_envs, "steps": args.max_iterations,
            **episodes.summary(),
        }
        print("M1_EVALUATION " + json.dumps(metrics), flush=True)
        crossing_rate = metrics.get("small_crossing_rate", float("nan"))
        if args.semantic_crossing and crossing_rate == crossing_rate and crossing_rate < args.min_crossing_rate:
            raise RuntimeError(
                f"semantic crossing rate {crossing_rate:.4f} is below "
                f"--min-crossing-rate {args.min_crossing_rate:.4f}"
            )
        print("M1_EVALUATION_COMPLETE", flush=True)
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
