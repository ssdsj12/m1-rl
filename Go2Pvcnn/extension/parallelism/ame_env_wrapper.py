"""RSL-RL VecEnv adapter for AME map/state observation groups."""

from __future__ import annotations

import gymnasium as gym
import os
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
        from .m1_crossing_metrics import CrossingEpisodeAccumulator
        self.crossing_metrics = CrossingEpisodeAccumulator(self.num_envs, self.device)
        self._small_candidate_prev = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self._small_candidate_seen = torch.zeros_like(self._small_candidate_prev)
        self._small_candidate_lift_seen = torch.zeros_like(self._small_candidate_prev)
        self._small_candidate_clearance_seen = torch.zeros_like(self._small_candidate_prev)
        self._large_candidate_seen = torch.zeros_like(self._small_candidate_prev)
        # Keep the M1 MPC swing alive after a semantic scan cell briefly
        # disappears under a moving wheel.  The old instantaneous gate
        # stopped the teacher after 2-4 frames, before the leg reached the
        # obstacle top, so the policy learned to scrape/slide instead of
        # lifting.  This is a bounded per-episode latch, not a replacement
        # for the policy: large obstacles always cancel it immediately.
        self._m1_teacher_active = torch.zeros_like(self._small_candidate_prev)
        self._m1_teacher_age = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)
        self._m1_teacher_no_candidate_steps = torch.zeros_like(self._m1_teacher_age)
        # A single 16-frame MPC horizon is not enough to execute the
        # one-leg lift, over-top swing, touchdown, and hand-off to the next
        # leg.  The old 32-step cap expired while the wheel was still beside
        # the first block, so PPO saw teacher action without seeing a complete
        # crossing transition and learned to scrape into the obstacle. Keep a
        # bounded latch, but span six horizons by default.  The environment
        # override is useful for smoke tests and remains bounded below so a
        # caller cannot silently restore the too-short phase.
        self._m1_teacher_max_steps = max(
            256, int(os.environ.get("M1_TEACHER_MAX_STEPS", "512"))
        )
        # De-duplicate repeated semantic detections of the same obstacle while
        # the forward corridor remains in the scanner field of view.
        self._m1_obstacle_event_seen = torch.zeros_like(self._small_candidate_prev)
        self._m1_obstacle_clear_steps = torch.zeros_like(self._m1_teacher_age)
        # A 10 cm obstacle remains in the forward scanner corridor for many
        # low-speed steps. Re-arm only after it has been absent long enough to
        # have physically passed the footprint, not after a short sensor gap.
        self._m1_obstacle_rearm_clear_steps = 48
        # Optional read-only diagnostics for short smoke runs.  This is kept
        # off during normal training so it cannot perturb PPO timing.
        self._m1_presence_debug = os.environ.get("M1_PRESENCE_DEBUG", "0") == "1"
        self._m1_presence_debug_steps = 0
        self._m1_presence_debug_small = 0
        self._m1_presence_debug_large = 0
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
        from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
        from extension.parallelism.rl_adapter import select_named_joint_state
        # Replan from the live scanner/command state before reading the first
        # reference frame. current_reference() is cache-backed and must not be
        # queried before refresh_from_env().
        refresh = getattr(manager, "refresh_from_env", None)
        if callable(refresh):
            refresh(self.unwrapped)
        # Frame 0 is the measured state copied into every newly replanned
        # trajectory. The M1 teacher must consume the first executable future
        # frame so a planned single-leg swing reaches the controller.
        reference = manager.current_reference(frame_offset=1)
        robot = self.unwrapped.scene["robot"]
        default_pos = select_named_joint_state(
            robot.data.default_joint_pos,
            source_names=tuple(robot.joint_names),
            selected_names=M1_ASSET_JOINT_NAMES,
        )
        current_pos = select_named_joint_state(
            robot.data.joint_pos,
            source_names=tuple(robot.joint_names),
            selected_names=M1_ASSET_JOINT_NAMES,
        )
        action, valid = reference_to_m1_action(
            reference, default_pos, current_joint_pos=current_pos,
        )
        # The MPC cache is also available on flat/no-obstacle terrain.  Do
        # not inject its standstill or nominal gait into every PPO rollout:
        # the teacher is only for a detected crossable small obstacle.  Large
        # obstacles remain the policy's avoidance task.  This prevents the
        # teacher from replacing normal locomotion and keeps PPO's action
        # distribution numerically well behaved.
        small_candidate, large_candidate = self.get_obstacle_presence()
        small_candidate = small_candidate.to(dtype=torch.bool)
        large_candidate = large_candidate.to(dtype=torch.bool)
        # Start a bounded crossing phase as soon as a small obstacle is
        # detected. Keep it active while the scanner cell moves under the
        # wheel; clear it on a large obstacle or after the bounded horizon.
        start = small_candidate & ~large_candidate & ~self._m1_obstacle_event_seen
        self._m1_obstacle_event_seen |= small_candidate
        self._m1_teacher_active |= start
        expired = self._m1_teacher_age >= self._m1_teacher_max_steps
        self._m1_teacher_active &= ~large_candidate & ~expired
        teacher_active = self._m1_teacher_active
        self._m1_teacher_age = torch.where(
            teacher_active,
            (self._m1_teacher_age + 1).clamp_max(self._m1_teacher_max_steps),
            torch.zeros_like(self._m1_teacher_age),
        )
        valid = valid & teacher_active
        action = torch.where(valid.unsqueeze(-1), action, torch.zeros_like(action))
        return action, valid

    def get_obstacle_presence(self):
        """Return semantic-small and semantic-large masks for crossing metrics."""
        from .m1_obstacle_rewards import m1_obstacle_presence
        return m1_obstacle_presence(self.unwrapped)

    def crossing_metrics_snapshot(self):
        return self.crossing_metrics.snapshot()

    def reset(self):
        obs_dict, _ = self.env.reset()
        self._m1_teacher_active.zero_()
        self._m1_teacher_age.zero_()
        self._m1_teacher_no_candidate_steps.zero_()
        self._m1_obstacle_event_seen.zero_()
        self._m1_obstacle_clear_steps.zero_()
        self._small_candidate_prev.zero_()
        self._small_candidate_seen.zero_()
        self._small_candidate_lift_seen.zero_()
        self._small_candidate_clearance_seen.zero_()
        self._large_candidate_seen.zero_()
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
        small_candidate, large_candidate = self.get_obstacle_presence()
        if self._m1_presence_debug:
            self._m1_presence_debug_steps += int(self.num_envs)
            self._m1_presence_debug_small += int(small_candidate.sum().item())
            self._m1_presence_debug_large += int(large_candidate.sum().item())
            if self._m1_presence_debug_steps >= 8192:
                denom = float(self._m1_presence_debug_steps)
                print(
                    "[M1 presence debug] samples=%d small=%.4f large=%.4f"
                    % (self._m1_presence_debug_steps,
                       self._m1_presence_debug_small / denom,
                       self._m1_presence_debug_large / denom),
                    flush=True,
                )
                self._m1_presence_debug_steps = 0
                self._m1_presence_debug_small = 0
                self._m1_presence_debug_large = 0
        done = (terminated | truncated).bool()
        from .m1_obstacle_rewards import m1_small_obstacle_climb, m1_small_obstacle_clearance
        lift_seen_now = m1_small_obstacle_climb(self.unwrapped) > 0.0
        clearance_seen_now = m1_small_obstacle_clearance(self.unwrapped)
        crossing_complete = (self._small_candidate_prev & ~small_candidate & self._small_candidate_seen
                             & (self._small_candidate_lift_seen | lift_seen_now)
                             & (self._small_candidate_clearance_seen | clearance_seen_now))
        # Do not release the teacher on the first transient clear scan.  A
        # complete M1 pass is a four-leg sequential motion; the 16-step
        # minimum lets the cached trajectory reach touchdown for the last leg.
        crossing_complete &= self._m1_teacher_age >= 24
        term = terminated.bool()
        collision = torch.zeros_like(done)
        names = list(self.unwrapped.reward_manager.active_terms)
        if "parallelism_geometry_collision" in names:
            collision |= self.unwrapped.reward_manager._step_reward[:, names.index("parallelism_geometry_collision")] != 0
        self.crossing_metrics.update(
            candidate=small_candidate,
            large_candidate=large_candidate,
            crossing_complete=crossing_complete,
            done=done,
            terminated=term,
            collision=collision,
            large_avoided=large_candidate & ~collision,
        )
        self._small_candidate_prev = small_candidate
        self._small_candidate_seen |= small_candidate
        self._small_candidate_lift_seen |= lift_seen_now & self._small_candidate_seen
        self._small_candidate_clearance_seen |= clearance_seen_now & self._small_candidate_seen
        self._large_candidate_seen |= large_candidate
        self._m1_obstacle_clear_steps = torch.where(
            small_candidate,
            torch.zeros_like(self._m1_obstacle_clear_steps),
            (self._m1_obstacle_clear_steps + 1).clamp_max(64),
        )
        self._m1_obstacle_event_seen &= self._m1_obstacle_clear_steps < self._m1_obstacle_rearm_clear_steps
        no_small = self._m1_teacher_active & ~small_candidate & self._small_candidate_seen
        self._m1_teacher_no_candidate_steps = torch.where(
            no_small,
            (self._m1_teacher_no_candidate_steps + 1).clamp_max(self._m1_teacher_max_steps),
            torch.zeros_like(self._m1_teacher_no_candidate_steps),
        )
        # Semantic returns can flicker for several frames while the wheel
        # passes over a small obstacle. Ending the teacher after three empty
        # scans cuts the single-leg sequence short and leaves the foot low.
        # Keep the bounded phase alive until the obstacle has been absent for
        # the same 12-frame clear window used to re-arm event de-duplication;
        # the independent max-age latch remains the hard safety stop.
        teacher_phase_done = no_small & (self._m1_obstacle_clear_steps >= 24) & (self._m1_teacher_age >= 48)
        # A successful crossing (or an episode reset) ends the latched
        # teacher phase. If clearance was not achieved, the age bound in
        # get_mpc_teacher_action is the safety stop and the policy remains in
        # control.
        self._m1_teacher_active &= ~crossing_complete & ~teacher_phase_done & ~done
        self._m1_teacher_age = torch.where(
            self._m1_teacher_active,
            self._m1_teacher_age,
            torch.zeros_like(self._m1_teacher_age),
        )
        self._m1_teacher_no_candidate_steps = torch.where(
            self._m1_teacher_active,
            self._m1_teacher_no_candidate_steps,
            torch.zeros_like(self._m1_teacher_no_candidate_steps),
        )
        self._small_candidate_seen = torch.where(done, torch.zeros_like(self._small_candidate_seen), self._small_candidate_seen)
        self._small_candidate_lift_seen = torch.where(done, torch.zeros_like(self._small_candidate_lift_seen), self._small_candidate_lift_seen)
        self._small_candidate_clearance_seen = torch.where(done, torch.zeros_like(self._small_candidate_clearance_seen), self._small_candidate_clearance_seen)
        self._large_candidate_seen = torch.where(done, torch.zeros_like(self._large_candidate_seen), self._large_candidate_seen)
        rewards = self._sanitize_rewards(rewards)
        policy, obs_extras = self._format_observations(obs_dict)
        extras["time_outs"] = truncated
        extras["observations"] = obs_extras["observations"]
        return policy, rewards, (terminated | truncated).to(dtype=torch.long), extras

    def close(self):
        return self.env.close()


__all__ = ["AmeRslRlEnvWrapper"]
