"""RSL-RL VecEnv adapter for AME map/state observation groups."""

from __future__ import annotations

import gymnasium as gym
import torch

from rsl_rl.env import VecEnv


class AmeRslRlEnvWrapper(VecEnv):
    _MAX_ABS_REWARD = 1.0e4

    def __init__(self, env, clip_actions: float | None = 100.0):
        self.env = env
        self.clip_actions = clip_actions
        self.num_envs = self.unwrapped.num_envs
        self.device = self.unwrapped.device
        self.max_episode_length = self.unwrapped.max_episode_length
        if hasattr(self.unwrapped, "action_manager"):
            self.num_actions = self.unwrapped.action_manager.total_action_dim
        else:
            self.num_actions = gym.spaces.flatdim(self.unwrapped.single_action_space)
        self.env.reset()

    @property
    def unwrapped(self):
        return self.env.unwrapped

    @property
    def cfg(self):
        return self.unwrapped.cfg

    @property
    def episode_length_buf(self):
        return self.unwrapped.episode_length_buf

    @episode_length_buf.setter
    def episode_length_buf(self, value):
        self.unwrapped.episode_length_buf = value

    @staticmethod
    def _flatten(obs_dict: dict[str, torch.Tensor], names: tuple[str, ...]) -> torch.Tensor:
        values = [obs_dict[name].reshape(obs_dict[name].shape[0], -1) for name in names]
        return torch.cat(values, dim=-1)

    def _format_observations(self, obs_dict: dict[str, torch.Tensor]) -> tuple[torch.Tensor, dict]:
        policy = self._flatten(
            obs_dict, ("policy_elevation_semantic_map", "policy_state")
        )
        critic = self._flatten(
            obs_dict, ("critic_elevation_semantic_map", "critic_state")
        )
        return policy, {"observations": {"critic": critic}}

    def get_observations(self):
        return self._format_observations(self.unwrapped.observation_manager.compute())

    def get_mpc_teacher_action(self):
        """Return the current M1 MPC action and validity mask when attached."""
        manager = getattr(self.unwrapped, "_trajectory_manager", None)
        if manager is None or not callable(getattr(manager, "current_reference", None)):
            return None, None
        from .m1_mpc_teacher import reference_to_m1_action
        reference = manager.current_reference()
        default_pos = self.unwrapped.scene["robot"].data.default_joint_pos
        return reference_to_m1_action(reference, default_pos)

    def get_obstacle_presence(self):
        """Return semantic-small and semantic-large masks for crossing metrics."""
        from .m1_obstacle_rewards import m1_obstacle_presence
        return m1_obstacle_presence(self.unwrapped)

    def reset(self):
        obs_dict, _ = self.env.reset()
        return self._format_observations(obs_dict)

    def _sanitize_rewards(self, rewards: torch.Tensor) -> torch.Tensor:
        termination_manager = self.unwrapped.termination_manager
        if "nonfinite_robot_state" not in termination_manager.active_terms:
            return rewards

        nonfinite_state = termination_manager.get_term("nonfinite_robot_state")
        # get_term() retains the last episode's cause, so intersect it with the
        # current step reset buffer before masking this step's reward.
        nonfinite_state = nonfinite_state & self.unwrapped.reset_buf
        invalid_reward = (~torch.isfinite(rewards)) | (
            torch.abs(rewards) > self._MAX_ABS_REWARD
        )
        invalid_count = int(invalid_reward.sum().item())
        if invalid_count:
            print(
                f"[AME][warning] sanitized invalid/extreme rewards env_count={invalid_count}",
                flush=True,
            )
        return torch.where(
            nonfinite_state | invalid_reward,
            torch.zeros_like(rewards),
            rewards,
        )

    def step(self, actions):
        if self.clip_actions is not None:
            actions = torch.clamp(actions, -self.clip_actions, self.clip_actions)
        obs_dict, rewards, terminated, truncated, extras = self.env.step(actions)
        rewards = self._sanitize_rewards(rewards)
        policy, obs_extras = self._format_observations(obs_dict)
        extras["time_outs"] = truncated
        extras["observations"] = obs_extras["observations"]
        return policy, rewards, (terminated | truncated).to(dtype=torch.long), extras

    def close(self):
        return self.env.close()


__all__ = ["AmeRslRlEnvWrapper"]
