#!/usr/bin/env python3
"""Train the isolated AME-XYZ-Semantic baseline on the M1 mixed task."""

from __future__ import annotations

import argparse
import copy
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


THIS_FILE = Path(__file__).resolve()
PACKAGE_ROOT = THIS_FILE.parent.parent
REPO_ROOT = PACKAGE_ROOT.parent
RSL_RL_ROOT = PACKAGE_ROOT / "rsl_rl"
for path in (PACKAGE_ROOT, RSL_RL_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _parse_args():
    from isaaclab.app import AppLauncher

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num_envs", type=int, default=1024)
    parser.add_argument("--max_iterations", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint", type=str, default=None)
    parser.add_argument("--keep_std", action="store_true")
    parser.add_argument("--semantic-crossing", action="store_true")
    parser.add_argument("--obstacle-threshold", type=float, default=None)
    parser.add_argument("--min-crossing-rate", type=float, default=0.50)
    parser.add_argument("--disable-crossing-reset", action="store_true")
    AppLauncher.add_app_launcher_args(parser)
    return parser.parse_args()


def _git_hash() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _register_runtime_env(gym, env_id, env_cfg_cls) -> None:
    if env_id in gym.registry:
        return
    gym.register(
        id=env_id,
        entry_point="isaaclab.envs:ManagerBasedRLEnv",
        kwargs={"env_cfg_entry_point": env_cfg_cls, "rsl_rl_cfg_entry_point": None},
        disable_env_checker=True,
    )


def _yaml_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(_yaml_safe(key)): _yaml_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_yaml_safe(item) for item in value]
    if hasattr(value, "__module__") and hasattr(value, "__qualname__"):
        return f"{value.__module__}:{value.__qualname__}"
    return str(value)


def main() -> int:
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    args = _parse_args()
    if args.num_envs <= 0 or args.max_iterations <= 0:
        raise ValueError("--num_envs and --max_iterations must be positive")
    if args.resume and not args.checkpoint:
        raise ValueError("--resume requires --checkpoint")
    if args.checkpoint and not args.resume:
        raise ValueError("--checkpoint requires --resume; refusing to silently train from scratch")

    if str(args.device).startswith("cuda"):
        import torch
        torch.cuda.set_device(int(str(args.device).split(":")[-1]))

    from isaaclab.app import AppLauncher

    app_launcher = AppLauncher(args)
    simulation_app = app_launcher.app
    env = None
    try:
        import gymnasium as gym
        import torch

        from ame_baseline.actor_critic_ame import ActorCriticAME  # noqa: F401 - runner injection contract
        from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
        from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
        from ame_baseline.ame_runner import AmeOnPolicyRunner
        from ame_baseline.m1_ame_train_cfg import get_m1_ame_train_cfg
        import go2_pvcnn.tasks.register_envs  # noqa: F401
        from isaaclab.utils.io import dump_yaml

        device = str(args.device)
        if device.startswith("cuda") and torch.cuda.is_available():
            torch.cuda.set_device(app_launcher.device_id)
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        _register_runtime_env(gym, "Isaac-M1-Cross-Large-Complex-AME-v0", M1AmeCrossLargeComplexEnvCfg)
        env_cfg = M1AmeCrossLargeComplexEnvCfg()
        env_cfg.scene.num_envs = args.num_envs
        env_cfg.sim.device = device
        env_cfg.seed = args.seed

        log_dir = (
            REPO_ROOT
            / "logs"
            / "rsl_rl"
            / "m1_cross_large_complex_ame"
            / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            / _git_hash()
        )
        log_dir.mkdir(parents=True, exist_ok=True)
        print(f"[AME] log_dir={log_dir}", flush=True)

        env = gym.make("Isaac-M1-Cross-Large-Complex-AME-v0", cfg=env_cfg)
        # Install the M1 MPC trajectory manager before wrapping the env so the
        # teacher adapter can consume current_reference() during rollouts.
        from extension.trajectory_manager_factory import attach_trajectory_manager_if_enabled
        attach_trajectory_manager_if_enabled(
            env.unwrapped,
            env_cfg,
            experiment_name="m1_cross_large_complex_ame_teacher",
            device=device,
        )
        if env.unwrapped.scene["robot"].is_fixed_base:
            raise RuntimeError("M1 locomotion requires a floating base; check USD root_joint")
        wrapped_env = AmeRslRlEnvWrapper(env, clip_actions=100.0)
        policy_obs, extras = wrapped_env.get_observations()
        critic_obs = extras["observations"]["critic"]
        print(
            f"[AME] observations policy={tuple(policy_obs.shape)} critic={tuple(critic_obs.shape)}",
            flush=True,
        )

        train_cfg = get_m1_ame_train_cfg()
        if os.environ.get("SAVE_INTERVAL"):
            train_cfg["save_interval"] = int(os.environ["SAVE_INTERVAL"])
        dump_yaml(str(log_dir / "env_cfg.yaml"), _yaml_safe(env_cfg.to_dict()))
        dump_yaml(str(log_dir / "train_cfg.yaml"), _yaml_safe(train_cfg))
        runner = AmeOnPolicyRunner(
            wrapped_env,
            copy.deepcopy(train_cfg),
            log_dir=str(log_dir),
            device=device,
        )
        if args.resume:
            checkpoint = Path(args.checkpoint).expanduser().resolve()
            if not checkpoint.is_file():
                raise FileNotFoundError(f"AME checkpoint not found: {checkpoint}")
            # Optimizer moments from the old Go2/flat task are not valid after
            # changing the M1 geometry and reward terms.  Reset them by
            # default for a resumed adaptation; set M1_LOAD_OPTIMIZER=1 only
            # when continuing an identical configuration.
            load_optimizer = os.environ.get("M1_LOAD_OPTIMIZER", "0") == "1"
            runner.load(str(checkpoint), load_optimizer=load_optimizer, keep_std=args.keep_std)
            print(f"[AME] resumed checkpoint={checkpoint}", flush=True)

        print("Starting Training - m1_cross_large_complex_ame", flush=True)
        # A resumed locomotion checkpoint already contains a settled gait.
        # Randomising the episode phase immediately after changing the M1
        # obstacle layout creates a large off-distribution impulse and can
        # destroy posture before PPO has adapted. Fresh runs retain the old
        # random-start exploration; resume runs begin from a full reset.
        runner.learn(
            num_learning_iterations=args.max_iterations,
            init_at_random_ep_len=(not args.resume)
            and os.environ.get("M1_DISABLE_RANDOM_EP_LEN", "0") != "1",
        )
        print("Training Complete - m1_cross_large_complex_ame", flush=True)
        return 0
    except BaseException:
        import traceback
        traceback.print_exc()
        print("EARLY_TERMINATION Python exception before training completion", file=sys.stderr, flush=True)
        raise
    finally:
        if env is not None:
            env.close()
        simulation_app.close()


if __name__ == "__main__":
    raise SystemExit(main())
