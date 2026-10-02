"""RSL-RL VecEnv adapter for AME map/state observation groups."""

from __future__ import annotations

import gymnasium as gym
import os
import torch

from rsl_rl.env import VecEnv


M1_FIXED_SMALL_OBSTACLE_LOCAL_XY = (
    (0.55, 0.20), (1.10, -0.20), (1.65, 0.20),
    (2.20, -0.20), (2.75, 0.20), (3.30, -0.20),
)


def _m1_fixed_obstacle_proximity_from_foot_xy(
    foot_xy: torch.Tensor,
    root_yaw: torch.Tensor,
    env_origins_xy: torch.Tensor,
    *,
    forward_m: float = 0.30,
    lateral_m: float = 0.16,
    obstacle_radius_m: float = 0.08,
    obstacle_local_xy: tuple[tuple[float, float], ...] = M1_FIXED_SMALL_OBSTACLE_LOCAL_XY,
) -> torch.Tensor:
    """Return per-leg proximity to the authored runtime M1 blocks.

    The semantic scanner only labels terrain meshes.  The M1 course blocks
    are runtime kinematic shapes, so their collision geometry must also be
    exposed to the teacher.  Obstacles are expressed in the current tile's
    local frame and are projected into each leg's forward/lateral corridor.
    """
    if foot_xy.ndim != 3 or foot_xy.shape[-1] != 2:
        raise ValueError("foot_xy must have shape [B,4,2]")
    root_yaw = torch.as_tensor(root_yaw, device=foot_xy.device, dtype=foot_xy.dtype).reshape(-1)
    env_origins_xy = torch.as_tensor(env_origins_xy, device=foot_xy.device, dtype=foot_xy.dtype)
    if env_origins_xy.shape != (foot_xy.shape[0], 2):
        raise ValueError("env_origins_xy must have shape [B,2]")
    if root_yaw.numel() == 1 and foot_xy.shape[0] > 1:
        root_yaw = root_yaw.expand(foot_xy.shape[0])
    local = foot_xy.new_tensor(obstacle_local_xy).view(1, 1, -1, 2)
    obstacle_xy = env_origins_xy[:, None, None, :] + local
    rel = obstacle_xy - foot_xy[:, :, None, :]
    heading = torch.stack((root_yaw.cos(), root_yaw.sin()), dim=-1)[:, None, None, :]
    lateral = torch.stack((-root_yaw.sin(), root_yaw.cos()), dim=-1)[:, None, None, :]
    forward = (rel * heading).sum(dim=-1)
    side = (rel * lateral).sum(dim=-1).abs()
    return ((forward >= 0.0) & (forward <= float(forward_m)) &
            (side <= float(lateral_m) + float(obstacle_radius_m))).any(dim=-1)


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
        self._m1_teacher_selected_leg = torch.zeros_like(self._m1_teacher_age)
        self._m1_teacher_selected_phase = torch.full_like(self._m1_teacher_age, -1)
        # Position-action zero means nominal pose, so preserve a fixed stance
        # target across each serial swing phase instead of chasing measured
        # drift every frame.  The target is refreshed only at phase handoff.
        self._m1_teacher_hold_pose = None
        self._m1_teacher_hold_phase = None
        self._m1_teacher_no_candidate_steps = torch.zeros_like(self._m1_teacher_age)
        # A single 16-frame MPC horizon is not enough to execute the
        # one-leg lift, over-top swing, touchdown, and hand-off to the next
        # leg.  The old 32-step cap expired while the wheel was still beside
        # the first block, so PPO saw teacher action without seeing a complete
        # crossing transition and learned to scrape into the obstacle. Keep a
        # bounded latch, but span six horizons by default.  The environment
        # override is useful for smoke tests and remains bounded below so a
        # caller cannot silently restore the too-short phase.
        # Six serial blocks at the deliberately slow 0.12 m/s teacher
        # approach take substantially longer than one MPC horizon.  A 512
        # step latch expired after the first approach and left the remaining
        # course to PPO before it had learned a crossing gait.  Keep the
        # safety bound finite, but cover the complete authored course.
        self._m1_teacher_max_steps = max(
            256, int(os.environ.get("M1_TEACHER_MAX_STEPS", "2048"))
        )
        # De-duplicate repeated semantic detections of the same obstacle while
        # the forward corridor remains in the scanner field of view.
        self._m1_obstacle_event_seen = torch.zeros_like(self._small_candidate_prev)
        self._m1_initial_teacher_fallback_used = torch.zeros_like(self._small_candidate_prev)
        self._m1_short_trigger_seen = torch.zeros_like(self._small_candidate_prev)
        self._m1_short_trigger_clear_steps = torch.zeros_like(self._small_candidate_prev)
        self._m1_fixed_small_candidate = torch.zeros_like(self._small_candidate_prev)
        self._m1_obstacle_clear_steps = torch.zeros_like(self._m1_teacher_age)
        # A 10 cm obstacle remains in the forward scanner corridor for many
        # low-speed steps. Re-arm only after it has been absent long enough to
        # have physically passed the footprint, not after a short sensor gap.
        self._m1_obstacle_rearm_clear_steps = 48
        self._m1_teacher_clear_steps = max(
            24, int(os.environ.get("M1_TEACHER_CLEAR_STEPS", "128"))
        )
        # Optional read-only diagnostics for short smoke runs.  This is kept
        # off during normal training so it cannot perturb PPO timing.
        self._m1_presence_debug = os.environ.get("M1_PRESENCE_DEBUG", "0") == "1"
        self._m1_presence_debug_steps = 0
        self._m1_presence_debug_small = 0
        self._m1_presence_debug_large = 0
        self._m1_step_debug = os.environ.get("M1_STEP_DEBUG", "0") == "1"
        self._m1_step_debug_count = 0
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
        from .m1_mpc_teacher import apply_m1_teacher_safety, reference_to_m1_action
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
        # The planner phase can stall at its terminal support frame while the
        # robot enters the short obstacle trigger. Use teacher age as a
        # separate serial phase so the adapter can choose a fallback swing leg
        # without mutating the planner reference itself.
        reference = dict(reference)
        reference["serial_phase_index"] = self._m1_teacher_age.clone()
        robot = self.unwrapped.scene["robot"]
        # Planner contact_state is a future schedule, not measured contact.
        # Feed the live wheel contact forces to the teacher for stance holds
        # and serial-leg selection; a 10 N threshold filters sensor noise.
        try:
            from .m1_ame_rewards import M1_SUPPORT_BODY_NAMES
            contact_sensor = self.unwrapped.scene["contact_forces"]
            contact_ids = list(resolve_named_indices(
                tuple(contact_sensor.body_names), M1_SUPPORT_BODY_NAMES,
            ))
            actual_contact_state = (
                contact_sensor.data.net_forces_w[:, contact_ids].norm(dim=-1) > 10.0
            )
            reference["actual_contact_state"] = actual_contact_state.detach()
        except Exception:
            actual_contact_state = None
        from extension.convention import extract_roll_pitch_batch, extract_yaw_batch
        root_rpy = torch.zeros((self.num_envs, 3), device=robot.data.root_pos_w.device, dtype=robot.data.root_pos_w.dtype)
        root_rpy[:, 0], root_rpy[:, 1] = extract_roll_pitch_batch(robot.data.root_quat_w)
        root_rpy[:, 2] = extract_yaw_batch(robot.data.root_quat_w)
        # Feed the previous live collision event back into the teacher.  A
        # timer-only leg sequence can leave a support foot against the next
        # obstacle while a different leg is lifted; the collision-by-leg
        # hint makes the next phase select the actually threatened foot.
        try:
            from tracking.mdp.policy_geometry_rewards import (
                _terrain_from_scanner,
                live_m1_policy_geometry_collision_by_leg,
                live_m1_obstacle_proximity_by_leg,
            )
            from extension.parallelism.types import ParallelismTerrain
            scanner = self.unwrapped.scene["semantic_height_scanner"]
            pattern_cfg = getattr(getattr(scanner, "cfg", None), "pattern_cfg", None)
            resolution = float(getattr(pattern_cfg, "resolution", 0.01))
            live_terrain = _terrain_from_scanner(scanner, robot.data.root_pos_w, resolution=resolution)
            obstacle_mask = live_terrain.semantic_id > 0
            live_terrain = ParallelismTerrain(
                height_w=torch.where(obstacle_mask, live_terrain.height_w, torch.full_like(live_terrain.height_w, -torch.inf)),
                semantic_id=live_terrain.semantic_id,
                valid_mask=live_terrain.valid_mask & obstacle_mask,
                origin_w=live_terrain.origin_w,
                yaw_w=live_terrain.yaw_w,
                resolution=live_terrain.resolution,
            )
            collision_mask = live_m1_policy_geometry_collision_by_leg(
                robot.data.root_pos_w,
                robot.data.root_quat_w,
                robot.data.joint_pos,
                tuple(getattr(robot, "joint_names", ())),
                live_terrain,
                margin_m=float(os.environ.get("M1_TEACHER_COLLISION_LOOKAHEAD_M", "0.05")),
                lookahead_m=float(os.environ.get("M1_TEACHER_COLLISION_LOOKAHEAD_X_M", "0.14")),
            )
            proximity_mask = live_m1_obstacle_proximity_by_leg(
                robot.data.root_pos_w,
                robot.data.root_quat_w,
                robot.data.joint_pos,
                tuple(getattr(robot, "joint_names", ())),
                live_terrain,
                forward_m=float(os.environ.get("M1_TEACHER_PROXIMITY_FORWARD_M", "0.24")),
                lateral_m=float(os.environ.get("M1_TEACHER_PROXIMITY_LATERAL_M", "0.09")),
            )
            # The authored M1 obstacles are runtime kinematic shapes and do
            # not carry the terrain semantic material used by the scanner.
            # Add their exact per-leg corridor trigger so the teacher lifts
            # the alternating target foot before contact.
            from extension.convention import extract_yaw_batch
            from extension.parallelism.robot_backend import get_robot_backend
            from extension.parallelism.rl_adapter import select_named_joint_state
            backend = get_robot_backend("m1")
            planner_joint = select_named_joint_state(
                robot.data.joint_pos,
                source_names=tuple(robot.joint_names),
                selected_names=backend.planner_joint_names,
            )
            yaw = extract_yaw_batch(robot.data.root_quat_w)
            roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
            geometry = backend.fk(
                robot.data.root_pos_w,
                torch.stack((roll, pitch, yaw), dim=-1),
                planner_joint,
                capsule_samples=1,
            )
            env_origins = getattr(self.unwrapped.scene, "env_origins", None)
            if env_origins is None:
                env_origins = robot.data.root_pos_w
            fixed_mask = _m1_fixed_obstacle_proximity_from_foot_xy(
                geometry.foot_pos_w[..., :2], yaw, env_origins[..., :2],
                forward_m=float(os.environ.get("M1_FIXED_PROXIMITY_FORWARD_M", "0.30")),
                lateral_m=float(os.environ.get("M1_FIXED_PROXIMITY_LATERAL_M", "0.16")),
                obstacle_radius_m=float(os.environ.get("M1_FIXED_OBSTACLE_RADIUS_M", "0.08")),
            )
            self._m1_fixed_small_candidate = fixed_mask.any(dim=1)
            reference["collision_leg_mask"] = collision_mask | proximity_mask | fixed_mask
        except Exception:
            # The teacher remains usable if a diagnostic-only live collision
            # query is unavailable during unit tests or scene startup.
            reference["collision_leg_mask"] = torch.zeros((self.num_envs, 4), dtype=torch.bool, device=robot.data.root_pos_w.device)
        # Choose the swing leg once per serial phase, rather than changing it
        # on every collision frame.  A rear leg can be selected at the phase
        # handoff when the scanner already sees the same block, but the active
        # leg is then allowed to finish its lift/traverse/touchdown arc.
        phase_block = max(1, int(os.environ.get("M1_TEACHER_PHASE_BLOCK", "8")))
        serial_phase = torch.div(self._m1_teacher_age, phase_block, rounding_mode="floor")
        phase_changed = serial_phase != self._m1_teacher_selected_phase
        if phase_changed.any():
            sequence_text = os.environ.get("M1_TEACHER_LEG_SEQUENCE", "0,3,2,1")
            try:
                leg_sequence = [int(item.strip()) for item in sequence_text.split(",") if item.strip()]
                leg_sequence = [item for item in leg_sequence if 0 <= item < 4] or [0, 3, 2, 1]
            except ValueError:
                leg_sequence = [0, 3, 2, 1]
            sequence = torch.as_tensor(leg_sequence, device=self.device, dtype=torch.long)
            default_leg = sequence.index_select(0, serial_phase.remainder(int(sequence.numel())))
            mask = torch.as_tensor(reference.get("collision_leg_mask"), device=self.device, dtype=torch.bool)
            if tuple(mask.shape) == (self.num_envs, 4):
                hit = mask.any(dim=1)
                # Preserve the configured serial gait whenever the planned
                # leg is itself threatened.  Only fall back to another hit
                # leg when the scheduled leg has no warning; selecting the
                # first mask bit unconditionally can reorder the gait every
                # phase and destabilize the body before touchdown.
                default_hit = mask.gather(1, default_leg[:, None]).squeeze(1)
                first_hit = mask.to(torch.long).argmax(dim=1)
                prefer_scheduled = os.environ.get("M1_TEACHER_PREFER_SCHEDULED", "1") not in {"0", "false", "False"}
                strict_sequence = os.environ.get("M1_TEACHER_STRICT_SEQUENCE", "1") not in {"0", "false", "False"}
                if strict_sequence:
                    # The authored course alternates one target lane at a
                    # time. Never let a stale scanner hit reorder the gait
                    # and repeatedly lift the first leg.
                    selected = default_leg
                elif prefer_scheduled:
                    selected = torch.where(default_hit, default_leg, torch.where(hit, first_hit, default_leg))
                else:
                    selected = torch.where(hit, first_hit, default_leg)
            else:
                selected = default_leg
            self._m1_teacher_selected_leg = torch.where(
                phase_changed, selected, self._m1_teacher_selected_leg,
            )
            self._m1_teacher_selected_phase = torch.where(
                phase_changed, serial_phase, self._m1_teacher_selected_phase,
            )
        reference["serial_leg_override"] = self._m1_teacher_selected_leg.clone()
        reference["m1_root_pos_w"] = robot.data.root_pos_w.detach().clone()
        reference["m1_root_rpy_w"] = root_rpy.detach().clone()
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
        # Use the articulation's stable reset pose as the stance lock.  A
        # current-pose snapshot can already contain swing drift from the
        # previous phase and would simply preserve that error.
        if self._m1_teacher_hold_pose is None or self._m1_teacher_hold_pose.shape != current_pos.shape:
            self._m1_teacher_hold_pose = default_pos.detach().clone()
            # Force one initialization pass from measured contacts.  Starting
            # at phase 0 skipped that pass and snapped all stance legs back to
            # the authored default pose on the first crossing frame.
            self._m1_teacher_hold_phase = torch.full_like(self._m1_teacher_age, -1)
        phase_block = max(1, int(os.environ.get("M1_TEACHER_PHASE_BLOCK", "8")))
        phase_slot = torch.div(self._m1_teacher_age, phase_block, rounding_mode="floor")
        if actual_contact_state is not None:
            # Track only feet that are physically carrying load.  A small
            # blend keeps the three stance targets aligned with body heave
            # and roll, while a lifted foot (force <= 10 N) remains frozen and
            # cannot be accidentally re-captured as a second swing leg.
            hold_legs = self._m1_teacher_hold_pose.reshape(-1, 4, 4)
            current_legs = current_pos.reshape(-1, 4, 4)
            phase_changed = phase_slot != self._m1_teacher_hold_phase
            blend = float(os.environ.get("M1_TEACHER_HOLD_CONTACT_BLEND", "0.20"))
            blend = min(max(blend, 0.0), 1.0)
            if torch.any(phase_changed):
                blend = 1.0
                self._m1_teacher_hold_phase = phase_slot.detach().clone()
            blended_legs = hold_legs + blend * (current_legs - hold_legs)
            hold_legs = torch.where(
                actual_contact_state.unsqueeze(-1), blended_legs, hold_legs,
            )
            self._m1_teacher_hold_pose = hold_legs.reshape_as(current_pos).detach()
        from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES
        planner_cols = [M1_ASSET_JOINT_NAMES.index(name) for name in M1_PLANNER_JOINT_NAMES]
        reference["hold_joint_angles"] = self._m1_teacher_hold_pose[:, planner_cols].clone()
        action, valid = reference_to_m1_action(
            reference, default_pos, current_joint_pos=current_pos,
        )
        if os.environ.get("M1_TEACHER_TRACE") == "1":
            import json
            trace_step = getattr(self, "_m1_teacher_trace_step", 0)
            self._m1_teacher_trace_step = trace_step + 1
            if trace_step % 8 == 0:
                idx = min(20, self.num_envs - 1)
                contact = reference.get("contact_state")
                phase = reference.get("phase_index")
                def _one(value):
                    if value is None:
                        return None
                    return value[idx].detach().cpu().tolist() if hasattr(value, "shape") and value.ndim > 0 else value
                print("M1_TEACHER_TRACE " + json.dumps({
                    "step": trace_step,
                    "env": idx,
                    "valid": bool(valid[idx].item()),
                    "contact_state": _one(contact),
                    "phase_index": _one(phase),
                    "teacher_action": action[idx].detach().cpu().tolist(),
                    "leg_action": action[idx].reshape(4, 4)[:, :3].detach().cpu().tolist(),
                    "reference_keys": sorted(str(key) for key in reference.keys()),
                    "reference_shapes": {str(key): list(value.shape) for key, value in reference.items() if hasattr(value, "shape")},
                }), flush=True)
        # A serial swing is useful only while the body remains recoverable.
        # If the reference/contacts mapping is wrong and the base starts to
        # tip, stop injecting teacher leg commands immediately and hand the
        # frame back to PPO.  This prevents a bad MPC phase from being
        # reinforced as a training target or turning into a collision cascade.
        root_rpy = root_rpy.to(device=action.device, dtype=action.dtype)
        action, valid = apply_m1_teacher_safety(action, valid, root_rpy)
        # The MPC cache is also available on flat/no-obstacle terrain.  Do
        # not inject its standstill or nominal gait into every PPO rollout:
        # the teacher is only for a detected crossable small obstacle.  Large
        # obstacles remain the policy's avoidance task.  This prevents the
        # teacher from replacing normal locomotion and keeps PPO's action
        # distribution numerically well behaved.
        # Keep accounting broad, but do not start a one-leg swing while the
        # obstacle is still far down the scanner corridor.  The short gate is
        # what turns the planned arc into an actual pre-contact lift.
        small_candidate, large_candidate = self.get_obstacle_presence()
        from .m1_obstacle_rewards import m1_teacher_obstacle_presence
        small_trigger, _ = m1_teacher_obstacle_presence(self.unwrapped)
        small_candidate = small_candidate.to(dtype=torch.bool)
        large_candidate = large_candidate.to(dtype=torch.bool)
        small_trigger = small_trigger.to(dtype=torch.bool)
        self._m1_debug_large_candidate = large_candidate.clone()
        # Preserve the pre-trigger state before updating the latch.  The
        # episode-start fallback is intentionally allowed to drive the base
        # toward a broad-corridor obstacle, but it must not leak a leg swing
        # on later frames while the obstacle is still outside the short
        # pre-lift window.  Once the short trigger has been observed, a
        # transient scanner dropout must not re-enter this hold state.
        short_trigger_seen_before = self._m1_short_trigger_seen.clone()
        # Start a bounded crossing phase as soon as a small obstacle is
        # detected. Keep it active while the scanner cell moves under the
        # wheel; clear it on a large obstacle or after the bounded horizon.
        # If the policy is initially stationary, the first block is still
        # visible in the broad corridor but not yet inside the short pre-lift
        # window.  Allow one episode-start fallback so the teacher can create
        # forward motion; subsequent blocks are armed only by the short
        # world-course trigger and therefore re-arm independently.
        initial_fallback = (
            small_candidate & ~large_candidate
            & ~self._m1_initial_teacher_fallback_used
            & ~self._m1_obstacle_event_seen
        )
        activation_trigger = small_trigger | initial_fallback
        self._m1_initial_teacher_fallback_used |= initial_fallback
        self._m1_short_trigger_seen |= small_trigger
        self._m1_short_trigger_clear_steps = torch.where(
            small_trigger,
            torch.zeros_like(self._m1_short_trigger_clear_steps),
            (self._m1_short_trigger_clear_steps + 1).clamp_max(64),
        )
        rearm = self._m1_short_trigger_seen & (self._m1_short_trigger_clear_steps >= 12)
        self._m1_obstacle_event_seen &= ~rearm
        start = activation_trigger & ~large_candidate & ~self._m1_obstacle_event_seen
        # The episode-start fallback only drives the robot toward the first
        # obstacle; it must not consume the crossing event.  Otherwise the
        # later short-range trigger is treated as a duplicate and the teacher
        # action is masked exactly when the foot should lift.
        self._m1_obstacle_event_seen |= small_trigger
        self._m1_teacher_active |= start
        expired = self._m1_teacher_age >= self._m1_teacher_max_steps
        self._m1_debug_expired = expired.clone()
        self._m1_teacher_active &= ~large_candidate & ~expired
        teacher_active = self._m1_teacher_active
        self._m1_teacher_age = torch.where(
            teacher_active,
            (self._m1_teacher_age + 1).clamp_max(self._m1_teacher_max_steps),
            torch.zeros_like(self._m1_teacher_age),
        )
        valid = valid & teacher_active
        action = torch.where(valid.unsqueeze(-1), action, torch.zeros_like(action))
        # The episode-start fallback exists only to make a stationary policy
        # roll toward the first block.  Do not lift a leg while that block is
        # still outside the short pre-contact window: a stationary one-leg
        # swing destabilizes the base and produces the exact early failures
        # this latch is meant to prevent.  The runner still injects the
        # commanded forward wheel speed for valid teacher rows; once
        # ``small_trigger`` becomes true, the full single-leg trajectory is
        # passed through.
        initial_roll = (
            small_candidate
            & ~large_candidate
            & ~small_trigger
            & ~short_trigger_seen_before
        )
        # The deterministic Cartesian teacher owns the approach phase: a
        # broad-corridor small candidate is already enough to start lifting
        # before the wheel reaches the obstacle.  Keep the conservative
        # short-trigger mask for the legacy planner adapter only.
        trajectory_teacher = (
            os.environ.get("M1_TEACHER_FOOT_TRAJECTORY", "0") == "1"
            and os.environ.get("M1_TEACHER_SERIAL_FORCE", "0") == "1"
        )
        if bool(initial_roll.any().item()) and not trajectory_teacher:
            leg_mask = torch.ones(action.shape[-1], dtype=torch.bool, device=action.device)
            leg_mask[3::4] = False
            action = torch.where(
                initial_roll.unsqueeze(-1) & leg_mask.unsqueeze(0),
                torch.zeros_like(action),
                action,
            )
        return action, valid

    def get_obstacle_presence(self):
        """Return semantic-small and semantic-large masks for crossing metrics."""
        from .m1_obstacle_rewards import m1_obstacle_presence
        small, large = m1_obstacle_presence(self.unwrapped)
        return small | self._m1_fixed_small_candidate, large

    def crossing_metrics_snapshot(self):
        return self.crossing_metrics.snapshot()

    def reset(self):
        obs_dict, _ = self.env.reset()
        self._m1_teacher_active.zero_()
        self._m1_teacher_age.zero_()
        self._m1_teacher_selected_leg.zero_()
        self._m1_teacher_selected_phase.fill_(-1)
        self._m1_teacher_hold_pose = None
        self._m1_teacher_hold_phase = None
        self._m1_teacher_no_candidate_steps.zero_()
        self._m1_obstacle_event_seen.zero_()
        self._m1_initial_teacher_fallback_used.zero_()
        self._m1_short_trigger_seen.zero_()
        self._m1_short_trigger_clear_steps.zero_()
        self._m1_fixed_small_candidate.zero_()
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
        trace = os.environ.get("M1_CONTROL_TRACE", "0") == "1"
        if trace:
            import json
            from .m1_ame_contract import m1_action_targets, M1_TRAINING_JOINT_POS
            from .m1_ame_rewards import M1_SUPPORT_BODY_NAMES
            from .m1_obstacle_rewards import m1_teacher_obstacle_presence
            from extension.parallelism.rl_adapter import resolve_named_indices
            robot = self.unwrapped.scene["robot"]
            idx = min(20, self.num_envs - 1)
            term = self.unwrapped.action_manager.get_term("JointPositionAction")
            wheel_ids = list(resolve_named_indices(robot.body_names, M1_SUPPORT_BODY_NAMES))
            step_id = getattr(self, "_control_trace_step", 0)
            self._control_trace_step = step_id + 1
            if step_id % 8 == 0:
                origin = self.unwrapped.scene.env_origins[idx]
                row = {
                    "step": step_id, "env": idx, "origin": origin.tolist(),
                    "root_local": (robot.data.root_pos_w[idx] - origin).tolist(),
                    "wheel_local": (robot.data.body_pos_w[idx, wheel_ids] - origin).tolist(),
                    "joint_names": list(term._joint_names),
                    "joint_pos": robot.data.joint_pos[idx, term._joint_ids].tolist(),
                    "default": term._default_pos[idx].tolist(),
                    "training_default": list(M1_TRAINING_JOINT_POS),
                    "action": actions[idx].tolist(),
                    "target": m1_action_targets(actions, term._default_pos)[idx].tolist(),
                    "short_trigger": bool(m1_teacher_obstacle_presence(self.unwrapped)[0][idx]),
                }
                print("M1_CONTROL_TRACE " + json.dumps(row), flush=True)
        obs_dict, rewards, terminated, truncated, extras = self.env.step(actions)
        small_candidate, large_candidate = self.get_obstacle_presence()
        if self._m1_step_debug:
            self._m1_step_debug_count += 1
            if self._m1_step_debug_count % 32 == 0:
                robot = self.unwrapped.scene["robot"]
                command = self.unwrapped.command_manager.get_command("base_velocity")
                root = robot.data.root_pos_w
                origins = getattr(self.unwrapped.scene, "env_origins", None)
                local_root = root - origins if origins is not None else root
                idx = int(command[:, 0].argmax().item())
                from .m1_ame_rewards import M1_SUPPORT_BODY_NAMES
                from extension.parallelism.rl_adapter import resolve_named_indices
                from extension.parallelism.m1_kinematics import M1_WHEEL_RADIUS_M
                wheel_ids = list(resolve_named_indices(tuple(robot.body_names), M1_SUPPORT_BODY_NAMES))
                wheel_bottom = robot.data.body_pos_w[:, wheel_ids, 2] - M1_WHEEL_RADIUS_M
                sensor = self.unwrapped.scene.get("contact_forces") if hasattr(self.unwrapped.scene, "get") else None
                non_support_force = 0.0
                if sensor is not None:
                    support = set(M1_SUPPORT_BODY_NAMES)
                    other = [i for i, name in enumerate(tuple(sensor.body_names)) if name not in support]
                    if other:
                        non_support_force = float(sensor.data.net_forces_w[idx, other].norm(dim=-1).amax().item())
                print(
                    "[M1 step debug] step=%d idx=%d local_root=(%.3f,%.3f,%.3f) cmd=(%.3f,%.3f,%.3f) cmdx_mean=%.3f small=%s large=%s teacher=%s action_max=%.3f wheel_bottom=(%s) non_support_force=%.1f"
                    % (self._m1_step_debug_count,
                       idx,
                       float(local_root[idx, 0].item()), float(local_root[idx, 1].item()), float(local_root[idx, 2].item()),
                       float(command[idx, 0].item()), float(command[idx, 1].item()), float(command[idx, 2].item()),
                       float(command[:, 0].mean().item()),
                       bool(small_candidate[idx].item()), bool(large_candidate[idx].item()),
                       bool(self._m1_teacher_active[idx].item()), float(actions[idx].abs().max().item()),
                       ",".join("%.3f" % float(value) for value in wheel_bottom[idx].detach().cpu().tolist()), non_support_force),
                    flush=True,
                )
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
        # Existing proxy only; not proof of strict per-foot crossing.
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
            (self._m1_obstacle_clear_steps + 1).clamp_max(self._m1_teacher_clear_steps),
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
        teacher_phase_done = no_small & (
            self._m1_obstacle_clear_steps >= self._m1_teacher_clear_steps
        ) & (self._m1_teacher_age >= 48)
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
        # Isaac auto-resets completed rows inside env.step(); wrapper.reset()
        # is not called for those episodes. Re-arm only completed rows so the
        # next obstacle course cannot inherit the previous episode's latches.
        self._small_candidate_prev &= ~done
        self._m1_obstacle_event_seen &= ~done
        self._m1_initial_teacher_fallback_used &= ~done
        self._m1_short_trigger_seen &= ~done
        self._m1_short_trigger_clear_steps.masked_fill_(done, 0)
        self._m1_obstacle_clear_steps.masked_fill_(done, 0)
        rewards = self._sanitize_rewards(rewards)
        policy, obs_extras = self._format_observations(obs_dict)
        extras["time_outs"] = truncated
        extras["observations"] = obs_extras["observations"]
        return policy, rewards, (terminated | truncated).to(dtype=torch.long), extras

    def close(self):
        return self.env.close()


__all__ = ["AmeRslRlEnvWrapper"]
