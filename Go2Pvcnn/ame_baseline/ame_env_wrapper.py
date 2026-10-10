"""RSL-RL VecEnv adapter for AME map/state observation groups."""

from __future__ import annotations

import gymnasium as gym
import os
import torch

from rsl_rl.env import VecEnv
from .m1_obstacle_profile import (
    M1_FIXED_SMALL_OBSTACLE_LOCAL_XY,
    M1_SMALL_OBSTACLE_DIAMETER_M,
)


def _advance_m1_teacher_phase(
    active: torch.Tensor, age: torch.Tensor, elapsed: torch.Tensor, *,
    handoff_ready: torch.Tensor, max_steps: int, phase_block: int, handoff_grace: int = 16,
    support_ready: torch.Tensor | None = None, phase_hold: torch.Tensor | None = None,
):
    """Advance serial teacher; stalled handoff cannot bypass hard expiry."""
    active = torch.as_tensor(active, dtype=torch.bool)
    age = torch.as_tensor(age, device=active.device, dtype=torch.long)
    elapsed = torch.as_tensor(elapsed, device=active.device, dtype=torch.long)
    handoff_ready = torch.as_tensor(handoff_ready, device=active.device, dtype=torch.bool)
    # Backward-compatible default for unit callers; production passes the
    # measured full support-polygon gate explicitly.
    if support_ready is None:
        support_ready = torch.ones_like(handoff_ready)
    support_ready = torch.as_tensor(support_ready, device=active.device, dtype=torch.bool)
    if phase_hold is None:
        phase_hold = torch.zeros_like(active)
    else:
        phase_hold = torch.as_tensor(phase_hold, device=active.device, dtype=torch.bool)
        if phase_hold.shape != active.shape:
            raise ValueError('phase_hold must match the active-environment mask')
    max_steps = max(1, int(max_steps)); phase_block = max(1, int(phase_block)); handoff_grace = max(0, int(handoff_grace))
    next_elapsed = torch.where(active, elapsed + 1, torch.zeros_like(elapsed))
    next_active = active & (next_elapsed < max_steps)
    next_age = torch.where(next_active, (age + 1).clamp_max(max_steps), torch.zeros_like(age))
    # Never advance to another swing while the body does not have all four
    # support wheels loaded.  A timer-only handoff is what previously caused
    # the robot to tilt and scrape into the obstacle.
    handoff_due = next_active & (next_age.remainder(phase_block) == 0) & support_ready
    # A clearance hold intentionally keeps the same foot selected while its
    # horizontal arc advances. Do not stall that arc at a phase boundary just
    # because the support-force gate is momentarily low; selection remains
    # locked separately until the obstacle envelope clears.
    blocked_due = (
        next_active
        & (next_age.remainder(phase_block) == 0)
        & ~support_ready
        & ~phase_hold
    )
    # If the selected wheel never reports touchdown, keep the phase for a
    # bounded grace window and then advance anyway.  The old implementation
    # decremented age at every boundary and could remain on leg 0 forever.
    handoff_timeout = (
        next_active
        & (age.remainder(phase_block) == phase_block - 1)
        & (next_elapsed >= age + handoff_grace)
        & support_ready
        & handoff_ready
    )
    handoff = handoff_due | handoff_timeout
    next_age = torch.where(handoff & ~handoff_ready & ~handoff_timeout, (next_age - 1).clamp_min(0), next_age)
    next_age = torch.where(blocked_due, age, next_age)
    next_elapsed = torch.where(next_active, next_elapsed, torch.zeros_like(next_elapsed))
    return next_active, next_age, next_elapsed


def _m1_teacher_obstacle_hold_max_steps():
    """Read the bounded late-swing clearance hold used during obstacle crossing."""
    return max(1, int(os.environ.get("M1_TEACHER_OBSTACLE_HOLD_MAX_STEPS", "32")))


def _m1_fixed_obstacle_proximity_from_foot_xy(
    foot_xy: torch.Tensor,
    root_yaw: torch.Tensor,
    env_origins_xy: torch.Tensor,
    *,
    forward_m: float = 0.30,
    lateral_m: float = 0.16,
    obstacle_radius_m: float = 0.08,
    obstacle_local_xy: tuple[tuple[float, float], ...] = M1_FIXED_SMALL_OBSTACLE_LOCAL_XY,
    obstacle_world_xy: torch.Tensor | None = None,
    obstacle_valid: torch.Tensor | None = None,
) -> torch.Tensor:
    """Return per-leg proximity to the authored runtime M1 blocks.

    The semantic scanner only labels terrain meshes.  The M1 course blocks
    are runtime kinematic shapes, so their collision geometry must also be
    exposed to the teacher.  Obstacles are expressed in the current tile's
    local frame and are projected into each leg's forward/lateral corridor.
    """
    if foot_xy.ndim not in (3, 4) or foot_xy.shape[1] != 4 or foot_xy.shape[-1] != 2:
        raise ValueError("foot_xy must have shape [B,4,2] or [B,4,P,2]")
    root_yaw = torch.as_tensor(root_yaw, device=foot_xy.device, dtype=foot_xy.dtype).reshape(-1)
    env_origins_xy = torch.as_tensor(env_origins_xy, device=foot_xy.device, dtype=foot_xy.dtype)
    if env_origins_xy.shape != (foot_xy.shape[0], 2):
        raise ValueError("env_origins_xy must have shape [B,2]")
    if root_yaw.numel() == 1 and foot_xy.shape[0] > 1:
        root_yaw = root_yaw.expand(foot_xy.shape[0])
    if obstacle_world_xy is None:
        local = foot_xy.new_tensor(obstacle_local_xy).view(1, 1, -1, 2)
        obstacle_xy = env_origins_xy[:, None, None, :] + local
    else:
        if obstacle_world_xy.ndim != 3 or obstacle_world_xy.shape[0] != foot_xy.shape[0] or obstacle_world_xy.shape[-1] != 2:
            raise ValueError('actual obstacle XY must be [B,N,2]')
        obstacle_xy = obstacle_world_xy[:, None]
    if foot_xy.ndim == 3:
        rel = obstacle_xy - foot_xy[:, :, None, :]
        heading = torch.stack((root_yaw.cos(), root_yaw.sin()), dim=-1)[:, None, None, :]
        lateral = torch.stack((-root_yaw.sin(), root_yaw.cos()), dim=-1)[:, None, None, :]
    else:
        rel = obstacle_xy[:, :, :, None, :] - foot_xy[:, :, None, :, :]
        heading = torch.stack((root_yaw.cos(), root_yaw.sin()), dim=-1)[:, None, None, None, :]
        lateral = torch.stack((-root_yaw.sin(), root_yaw.cos()), dim=-1)[:, None, None, None, :]
    forward = (rel * heading).sum(dim=-1)
    side = (rel * lateral).sum(dim=-1).abs()
    in_corridor = ((forward >= 0.0) & (forward <= float(forward_m)) &
                   (side <= float(lateral_m) + float(obstacle_radius_m)))
    if obstacle_valid is not None:
        mask = obstacle_valid[:, None] if foot_xy.ndim == 3 else obstacle_valid[:, None, :, None]
        in_corridor &= mask
    return in_corridor.any(dim=2) if foot_xy.ndim == 3 else in_corridor.any(dim=(2, 3))


class AmeRslRlEnvWrapper(VecEnv):
    _MAX_ABS_REWARD = 1.0e4

    def _m1_current_course(self):
        terrain = self.unwrapped.scene.terrain
        return self._m1_course_registry.for_envs(terrain.terrain_levels, terrain.terrain_types)

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
        self.crossing_metrics = CrossingEpisodeAccumulator(self.num_envs, self.device,
            strict_mode='encounter' if getattr(self.unwrapped.cfg,'m1_course_profile','fixed')=='mixed' else 'episode')
        from .m1_strict_crossing import StrictCrossingTracker
        self._m1_strict_crossing = StrictCrossingTracker(
            self.num_envs, self.device, obstacle_count=len(M1_FIXED_SMALL_OBSTACLE_LOCAL_XY),
        )
        self._m1_course_registry = None
        self._m1_required_gate = None
        if getattr(getattr(self.unwrapped, 'cfg', None), 'm1_course_profile', 'fixed') == 'mixed':
            from .m1_course_registry import CourseRegistry
            from .m1_dynamic_crossing import EncounterCrossingTracker
            terrain = self.unwrapped.scene.terrain
            self._m1_course_registry = CourseRegistry(
                terrain.grounded_course_obstacles,
                rows=terrain.terrain_origins.shape[0], cols=terrain.terrain_origins.shape[1], device=self.device,
            )
            self._m1_strict_crossing = EncounterCrossingTracker(
                self.num_envs, self.device, obstacle_count=self._m1_course_registry.capacity,
            )
            if getattr(self.unwrapped.cfg, 'm1_flat_first', False):
                from .m1_required_crossing import RequiredCrossingRewardGate
                self._m1_required_gate = RequiredCrossingRewardGate(
                    self.num_envs, self._m1_course_registry.capacity, self.device)
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
        self._m1_teacher_elapsed = torch.zeros_like(self._m1_teacher_age)
        self._m1_teacher_selected_leg = torch.zeros_like(self._m1_teacher_age)
        self._m1_teacher_selected_phase = torch.full_like(self._m1_teacher_age, -1)
        self._m1_last_valid_swing_action = torch.zeros(
            (self.num_envs, 12), device=self.device, dtype=torch.float32,
        )
        self._m1_last_valid_swing_leg = torch.full_like(self._m1_teacher_age, -1)
        self._m1_last_valid_swing_phase = torch.full_like(self._m1_teacher_age, -1)
        self._m1_invalid_swing_fallback = torch.zeros_like(self._small_candidate_prev)
        # A serial handoff must not occur while the selected wheel is still
        # inside the authored obstacle corridor.  The previous timer-only
        # handoff changed legs before the body had passed the block, leaving
        # the old support wheel to scrape the obstacle.
        self._m1_teacher_selected_collision = torch.zeros_like(self._m1_teacher_age, dtype=torch.bool)
        # A lifted wheel must stay above its target obstacle until the
        # per-leg collision/proximity corridor has cleared continuously.
        self._m1_teacher_obstacle_hold = torch.zeros_like(self._m1_teacher_age, dtype=torch.bool)
        self._m1_teacher_obstacle_clear_steps = torch.zeros_like(self._m1_teacher_age)
        self._m1_teacher_obstacle_hold_steps = torch.zeros_like(self._m1_teacher_age)
        # Position-action zero means nominal pose, so preserve a fixed stance
        # target across each serial swing phase instead of chasing measured
        # drift every frame.  The target is refreshed only at phase handoff.
        self._m1_teacher_hold_pose = None
        self._m1_teacher_hold_phase = None
        # Freeze each phase's stance feet in world coordinates.  Recomputing
        # the swing anchor from the current root every frame makes a heaving
        # body pull the target down, which is especially harmful to the
        # left-side legs.  The anchor is refreshed only at serial handoff.
        self._m1_teacher_hold_foot_w = None
        self._m1_teacher_hold_foot_phase = None
        self._m1_teacher_hold_foot_leg = None
        self._m1_teacher_hold_root_w = None
        self._m1_teacher_hold_rpy_w = None
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
        from extension.parallelism.rl_adapter import select_named_joint_state, resolve_named_indices
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
            if os.environ.get("M1_TEACHER_USE_ACTUAL_CONTACT", "0") == "1":
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
                capsule_samples=5,
            )
            env_origins = getattr(self.unwrapped.scene, "env_origins", None)
            if env_origins is None:
                env_origins = robot.data.root_pos_w
            leg_envelope_xy = torch.cat((
                geometry.thigh_samples_w,
                geometry.calf_samples_w,
                geometry.foot_pos_w.unsqueeze(-2),
            ), dim=-2)[..., :2]
            course_kwargs = {}
            if getattr(self, '_m1_course_registry', None) is not None:
                course = self._m1_current_course()
                course_kwargs = dict(obstacle_world_xy=course["centers_top"][..., :2],
                                     obstacle_valid=course['valid'])
            fixed_mask = _m1_fixed_obstacle_proximity_from_foot_xy(
                leg_envelope_xy, yaw, env_origins[..., :2],
                forward_m=float(os.environ.get("M1_FIXED_PROXIMITY_FORWARD_M", "0.30")),
                lateral_m=float(os.environ.get("M1_FIXED_PROXIMITY_LATERAL_M", "0.16")),
                obstacle_radius_m=float(os.environ.get("M1_FIXED_OBSTACLE_RADIUS_M", "0.08")),
                **course_kwargs,
            )
            self._m1_fixed_small_candidate = fixed_mask.any(dim=1)
            reference["collision_leg_mask"] = collision_mask | proximity_mask | fixed_mask
            # Keep the raw geometry hit separate from the predictive corridor
            # masks.  Predictive proximity is used to trigger a swing, but it
            # must not freeze the phase or the robot can remain stalled beside
            # a block and lose its support polygon.
            reference["geometry_collision_leg_mask"] = collision_mask
        except Exception:
            if getattr(self, '_m1_course_registry', None) is not None:
                raise RuntimeError('mixed-course teacher geometry failed')
            # The teacher remains usable if a diagnostic-only live collision
            # query is unavailable during unit tests or scene startup.
            reference["collision_leg_mask"] = torch.zeros((self.num_envs, 4), dtype=torch.bool, device=robot.data.root_pos_w.device)
            reference["geometry_collision_leg_mask"] = torch.zeros((self.num_envs, 4), dtype=torch.bool, device=robot.data.root_pos_w.device)
        # Choose the swing leg once per serial phase, rather than changing it
        # on every collision frame.  A rear leg can be selected at the phase
        # handoff when the scanner already sees the same block, but the active
        # leg is then allowed to finish its lift/traverse/touchdown arc.
        phase_block = max(1, int(os.environ.get("M1_TEACHER_PHASE_BLOCK", "32")))
        serial_phase = torch.div(self._m1_teacher_age, phase_block, rounding_mode="floor")
        hold_active_before = self._m1_teacher_obstacle_hold.clone()
        phase_changed = serial_phase != self._m1_teacher_selected_phase
        phase_update = phase_changed & ~hold_active_before
        if phase_update.any():
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
                phase_update, selected, self._m1_teacher_selected_leg,
            )
            self._m1_teacher_selected_phase = torch.where(
                phase_update, serial_phase, self._m1_teacher_selected_phase,
            )
        from .m1_teacher_phase import (
            m1_merge_strict_event_hold,
            m1_strict_crossing_event_active,
            m1_strict_crossing_lift_hold,
        )
        strict_event_active = m1_strict_crossing_event_active(
            target_wheel=self._m1_strict_crossing.target_wheel,
            awaiting_recovery=self._m1_strict_crossing.awaiting_recovery,
            failed=self._m1_strict_crossing.failed,
        )
        strict_lift_hold = m1_strict_crossing_lift_hold(
            target_wheel=self._m1_strict_crossing.target_wheel,
            awaiting_recovery=self._m1_strict_crossing.awaiting_recovery,
            failed=self._m1_strict_crossing.failed,
            clearance_seen=self._m1_strict_crossing.clearance_seen,
            far_seen=self._m1_strict_crossing.far_seen,
        )
        strict_target_wheel = self._m1_strict_crossing.target_wheel.clamp(0, 3)
        self._m1_teacher_selected_leg = torch.where(
            strict_event_active, strict_target_wheel, self._m1_teacher_selected_leg,
        )
        reference["serial_leg_override"] = self._m1_teacher_selected_leg.clone()
        collision_mask = torch.as_tensor(
            reference.get("collision_leg_mask"), device=self.device, dtype=torch.bool
        )
        if tuple(collision_mask.shape) == (self.num_envs, 4):
            self._m1_teacher_selected_collision = collision_mask.gather(
                1, self._m1_teacher_selected_leg.clamp(0, 3)[:, None]
            ).squeeze(1).detach()
        else:
            self._m1_teacher_selected_collision.zero_()
        event_hold_enabled = os.environ.get(
            "M1_TEACHER_EVENT_HOLD_ON_OBSTACLE", "1"
        ).strip().lower() not in {"0", "false", "no"}
        phase_hold = torch.zeros_like(self._m1_teacher_obstacle_hold)
        if event_hold_enabled:
            from .m1_teacher_phase import advance_obstacle_lift_hold
            (self._m1_teacher_obstacle_hold,
             self._m1_teacher_obstacle_clear_steps,
             self._m1_teacher_obstacle_hold_steps,
             dynamic_phase) = advance_obstacle_lift_hold(
                previous_hold=self._m1_teacher_obstacle_hold,
                clear_steps=self._m1_teacher_obstacle_clear_steps,
                held_steps=self._m1_teacher_obstacle_hold_steps,
                selected_collision=self._m1_teacher_selected_collision,
                age=self._m1_teacher_age,
                phase_block=phase_block,
                clear_required=int(os.environ.get(
                    "M1_TEACHER_OBSTACLE_CLEAR_DWELL", "8"
                )),
                max_hold_steps=_m1_teacher_obstacle_hold_max_steps(),
            )
            reference["serial_phase_index"] = dynamic_phase
        else:
            self._m1_teacher_obstacle_hold.zero_()
            self._m1_teacher_obstacle_clear_steps.zero_()
            self._m1_teacher_obstacle_hold_steps.zero_()
        # Keep event ownership through loaded touchdown, but release the
        # vertical lift as soon as measured wheel clearance and far-edge
        # passage are both proven. Otherwise the lift floor prevents the same
        # selected wheel from descending onto the far side.
        self._m1_teacher_obstacle_hold = m1_merge_strict_event_hold(
            predictor_hold=self._m1_teacher_obstacle_hold,
            strict_event_active=strict_event_active,
            strict_lift_hold=strict_lift_hold,
        )
        self._m1_teacher_obstacle_clear_steps = torch.where(
            strict_event_active,
            torch.zeros_like(self._m1_teacher_obstacle_clear_steps),
            self._m1_teacher_obstacle_clear_steps,
        )
        phase_hold = self._m1_teacher_obstacle_hold
        reference["serial_obstacle_lift_hold"] = self._m1_teacher_obstacle_hold.clone()
        geometry_clearance_complete = (
            strict_event_active
            & self._m1_strict_crossing.clearance_seen
            & self._m1_strict_crossing.far_seen
        )
        reference["serial_obstacle_clearance_complete"] = geometry_clearance_complete.clone()
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
        phase_block = max(1, int(os.environ.get("M1_TEACHER_PHASE_BLOCK", "32")))
        phase_slot = torch.div(self._m1_teacher_age, phase_block, rounding_mode="floor")
        phase_slot = torch.where(
            self._m1_teacher_obstacle_hold | strict_event_active,
            self._m1_teacher_selected_phase,
            phase_slot,
        )
        if (
            actual_contact_state is not None
            and os.environ.get("M1_TEACHER_USE_MEASURED_HOLD", "0") == "1"
        ):
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
        from extension.parallelism.m1_kinematics import m1_fk
        held_planner = self._m1_teacher_hold_pose[:, planner_cols]
        refresh_foot_anchor = (
            self._m1_teacher_hold_foot_w is None
            or self._m1_teacher_hold_foot_w.shape != (self.num_envs, 4, 3)
            or self._m1_teacher_hold_foot_phase is None
            or self._m1_teacher_hold_foot_phase.shape != phase_slot.shape
        )
        if refresh_foot_anchor:
            self._m1_teacher_hold_foot_w = torch.zeros(
                (self.num_envs, 4, 3), device=current_pos.device, dtype=current_pos.dtype
            )
            self._m1_teacher_hold_foot_phase = torch.full_like(phase_slot, -1)
            self._m1_teacher_hold_foot_leg = torch.full_like(phase_slot, -1)
            self._m1_teacher_hold_root_w = reference["m1_root_pos_w"].clone()
            self._m1_teacher_hold_rpy_w = root_rpy.clone()
        foot_phase_changed = ((phase_slot != self._m1_teacher_hold_foot_phase)
                              | (self._m1_teacher_selected_leg != self._m1_teacher_hold_foot_leg))
        if refresh_foot_anchor or bool(foot_phase_changed.any().item()):
            # Capture the actual articulated foot pose only at handoff.  This
            # preserves the physical touchdown height after body heave while
            # avoiding the unstable per-frame measured-contact feedback path.
            anchor_joint = held_planner
            if os.environ.get("M1_TEACHER_HOLD_FOOT_USE_CURRENT", "1") == "1":
                anchor_joint = current_pos[:, planner_cols]
            held_fk = m1_fk(reference["m1_root_pos_w"], root_rpy, anchor_joint)
            self._m1_teacher_hold_foot_w = torch.where(
                foot_phase_changed[:, None, None],
                held_fk.foot_pos_w.detach(),
                self._m1_teacher_hold_foot_w,
            )
            self._m1_teacher_hold_foot_phase = torch.where(
                foot_phase_changed, phase_slot, self._m1_teacher_hold_foot_phase,
            )
            self._m1_teacher_hold_foot_leg = torch.where(
                foot_phase_changed, self._m1_teacher_selected_leg, self._m1_teacher_hold_foot_leg)
            self._m1_teacher_hold_root_w = torch.where(
                foot_phase_changed[:, None], reference["m1_root_pos_w"], self._m1_teacher_hold_root_w)
            self._m1_teacher_hold_rpy_w = torch.where(
                foot_phase_changed[:, None], root_rpy, self._m1_teacher_hold_rpy_w)
        # While rolling forward, a world-fixed stance anchor stretches the
        # three support legs until the base pitches/falls.  Re-anchor only
        # measured-contact support wheels every frame; the selected swing
        # wheel remains frozen to its planned touchdown arc.
        measured_contact_state = locals().get("actual_contact_state")
        if (
            measured_contact_state is not None
            and os.environ.get("M1_TEACHER_USE_MEASURED_HOLD", "0") == "1"
        ):
            try:
                from extension.parallelism.m1_kinematics import m1_fk
                live_fk = m1_fk(
                    reference["m1_root_pos_w"], root_rpy, current_pos[:, planner_cols],
                )
                leg_ids = torch.arange(4, device=current_pos.device).view(1, 4)
                selected = self._m1_teacher_selected_leg.reshape(-1, 1)
                support_contact = measured_contact_state & (leg_ids != selected)
                self._m1_teacher_hold_foot_w = torch.where(
                    support_contact.unsqueeze(-1),
                    live_fk.foot_pos_w.detach(),
                    self._m1_teacher_hold_foot_w,
                )
            except Exception:
                pass
        reference["hold_foot_pos_w"] = self._m1_teacher_hold_foot_w.clone()
        reference["hold_root_pos_w"] = self._m1_teacher_hold_root_w.clone()
        reference["hold_root_rpy_w"] = self._m1_teacher_hold_rpy_w.clone()
        from extension.parallelism.m1_kinematics import M1_WHEEL_RADIUS_M
        # Conservative configured top of this fixed flat course; do not use
        # current base height, which sinks during load transfer. Strict
        # physical acceptance still needs the independently measured top.
        from .m1_crossing_clearance import wheel_center_target_z
        reference["serial_wheel_target_z_w"] = wheel_center_target_z(
            self.unwrapped.scene.env_origins[:, 2]
            + float(os.environ.get("M1_SMALL_OBSTACLE_HEIGHT_M", "0.10")),
            wheel_radius=M1_WHEEL_RADIUS_M,
            bottom_clearance=float(os.environ.get("M1_WHEEL_BOTTOM_CLEARANCE_M", "0.04")),
        )
        action, valid = reference_to_m1_action(
            reference, default_pos, current_joint_pos=current_pos,
        )
        # Keep the IK/reference certificate separate from permission to
        # execute a finite safety hold. Later crossing/recovery gates may
        # retain control, but cannot turn a failed IK into an imitation label.
        reference_valid = valid.detach().clone()
        # A leg-only MPC target is not enough for a forward crossing: with
        # neutral wheels the teacher repeatedly lifts a foot while the body
        # stays over the same obstacle and eventually tips.  Preserve the
        # commanded forward velocity in every teacher-controlled row.  The
        # M1 wheel action is normalized directly in m/s because
        # M1_WHEEL_ACTION_SCALE_RAD_S == 1 / wheel_radius.
        if os.environ.get("M1_TEACHER_DRIVE_WHEELS", "1").strip().lower() not in {"0", "false", "no"}:
            try:
                from .m1_ame_contract import M1_WHEEL_ACTION_SCALE_RAD_S, M1_WHEEL_SPEED_LIMIT_RAD_S
                from extension.parallelism.m1_kinematics import M1_WHEEL_JOINT_NAMES
                wheel_cols = resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES)
                command = torch.as_tensor(
                    self.unwrapped.command_manager.get_command("base_velocity"),
                    device=action.device, dtype=action.dtype,
                )
                forward_speed = command[:, 0].clamp(
                    -M1_WHEEL_SPEED_LIMIT_RAD_S / M1_WHEEL_ACTION_SCALE_RAD_S,
                    M1_WHEEL_SPEED_LIMIT_RAD_S / M1_WHEEL_ACTION_SCALE_RAD_S,
                )
                # Keep the three stance wheels moving during a serial swing.
                # Scaling every wheel to the swing-wheel value (15%) stalls
                # the base while the event latch holds one wheel in the air;
                # the wheel cannot pass the block and the robot remains stuck
                # beside it.  The support wheels roll at a reduced but useful
                # speed; only the airborne wheel receives the lower scale.
                phase_block = max(1, int(os.environ.get("M1_TEACHER_PHASE_BLOCK", "32")))
                phase_progress = (self._m1_teacher_age.remainder(phase_block).to(action.dtype) + 1.0) / float(phase_block)
                phase_progress = torch.where(
                    geometry_clearance_complete,
                    torch.ones_like(phase_progress),
                    phase_progress,
                )
                swing_scale = float(os.environ.get("M1_TEACHER_WHEEL_SWING_SCALE", "0.15"))
                support_scale = float(os.environ.get("M1_TEACHER_SUPPORT_WHEEL_SWING_SCALE", "0.50"))
                crossing_active = torch.as_tensor(
                    getattr(self, "_m1_teacher_active", torch.zeros(self.num_envs, device=action.device)),
                    device=action.device, dtype=torch.bool,
                )
                selected_leg = torch.as_tensor(
                    getattr(self, "_m1_teacher_selected_leg", torch.zeros(self.num_envs, device=action.device)),
                    device=action.device, dtype=torch.long,
                )
                from .m1_teacher_phase import serial_crossing_wheel_actions
                wheel_action = serial_crossing_wheel_actions(
                    forward_speed=forward_speed,
                    selected_leg=selected_leg,
                    crossing_active=crossing_active,
                    phase_progress=phase_progress,
                    obstacle_lift_hold=phase_hold,
                    touchdown_pending=strict_event_active,
                    support_scale=support_scale,
                    swing_scale=swing_scale,
                )
                action[:, wheel_cols] = wheel_action
            except Exception:
                # Unit-test doubles may not expose a command manager; the
                # leg trajectory remains usable in that case.
                pass
        # Strict crossing is latched before recovery is evaluated.  During
        # that separate recovery interval, stop wheel drive and smoothly
        # return all four legs toward their nominal support pose; do not start
        # the next obstacle's swing until the measured support gate clears.
        recovery_mask = self._m1_strict_crossing.awaiting_recovery.clone()
        if bool(recovery_mask.any().item()):
            from .m1_teacher_phase import build_m1_post_cross_recovery_action
            from .m1_ame_contract import M1_LEG_ACTION_SCALE_RAD
            recovery_action = build_m1_post_cross_recovery_action(
                current_pos,
                default_pos,
                planner_cols=planner_cols,
                wheel_cols=resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES),
                leg_action_scale=M1_LEG_ACTION_SCALE_RAD,
                max_joint_step_rad=float(os.environ.get(
                    "M1_TEACHER_RECOVERY_SLEW_RAD", "0.10"
                )),
            )
            action = torch.where(recovery_mask[:, None], recovery_action, action)
            valid = torch.where(recovery_mask, torch.ones_like(valid), valid)
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
        action, valid = apply_m1_teacher_safety(
            action,
            valid,
            root_rpy,
            crossing_active=getattr(
                self, "_m1_teacher_active",
                torch.zeros(self.num_envs, device=action.device, dtype=torch.bool),
            ) | recovery_mask,
        )
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
        allow_initial_fallback = os.environ.get("M1_TEACHER_INITIAL_FALLBACK", "0").strip().lower() in {"1", "true", "yes"}
        initial_fallback = (
            small_candidate & ~large_candidate
            & ~self._m1_initial_teacher_fallback_used
            & ~self._m1_obstacle_event_seen
            & allow_initial_fallback
        )
        fixed_trigger = self._m1_fixed_small_candidate.clone()
        activation_trigger = small_trigger | fixed_trigger | initial_fallback
        self._m1_initial_teacher_fallback_used |= initial_fallback
        self._m1_short_trigger_seen |= small_trigger | fixed_trigger
        self._m1_short_trigger_clear_steps = torch.where(
            small_trigger | fixed_trigger,
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
        expired = self._m1_teacher_elapsed >= self._m1_teacher_max_steps
        self._m1_debug_expired = expired.clone()
        self._m1_teacher_active &= ~large_candidate & ~expired
        teacher_active = self._m1_teacher_active
        phase_block = max(1, int(os.environ.get("M1_TEACHER_PHASE_BLOCK", "32")))
        handoff_ready = torch.ones_like(teacher_active)
        support_ready = torch.ones_like(teacher_active)
        try:
            from .m1_ame_rewards import M1_SUPPORT_BODY_NAMES
            from extension.parallelism.rl_adapter import resolve_named_indices
            contact_sensor = self.unwrapped.scene["contact_forces"]
            contact_ids = list(resolve_named_indices(tuple(contact_sensor.body_names), M1_SUPPORT_BODY_NAMES))
            contact_norm = contact_sensor.data.net_forces_w[:, contact_ids].norm(dim=-1)
            # One wheel is intentionally unloaded during a serial swing. A
            # valid support polygon is therefore three loaded wheels, not
            # four; requiring all four deadlocks touchdown and causes tilt.
            support_threshold = float(os.environ.get("M1_TEACHER_HANDOFF_CONTACT_N", "10.0"))
            min_support_wheels = max(2, int(os.environ.get("M1_TEACHER_MIN_SUPPORT_WHEELS", "3")))
            support_ready = contact_norm.gt(support_threshold).sum(dim=-1) >= min_support_wheels
            selected_leg = self._m1_teacher_selected_leg.clamp_min(0).clamp_max(3)
            handoff_ready = contact_norm.gather(1, selected_leg[:, None]).squeeze(1) > float(
                os.environ.get("M1_TEACHER_HANDOFF_CONTACT_N", "10.0")
            )
        except Exception:
            pass
        # Keep the current serial leg through the obstacle corridor.  This is
        # an event gate, not another fixed distance: once the collision mask
        # clears and the selected wheel is loaded, the normal handoff resumes.
        if os.environ.get("M1_TEACHER_HOLD_ON_COLLISION", "0").strip().lower() not in {"0", "false", "no"}:
            # Predictive proximity is allowed to trigger the lift, but only
            # blocks a handoff during the final descent window.  Blocking at
            # phase start would freeze the body beside every obstacle.
            local_phase = self._m1_teacher_age.remainder(phase_block)
            near_touchdown = local_phase >= max(0, phase_block - 2)
            handoff_ready = handoff_ready & ~(
                self._m1_teacher_selected_collision & near_touchdown
            )
        (self._m1_teacher_active, self._m1_teacher_age, self._m1_teacher_elapsed) = _advance_m1_teacher_phase(
            teacher_active, self._m1_teacher_age, self._m1_teacher_elapsed,
            handoff_ready=handoff_ready, support_ready=support_ready,
            phase_hold=phase_hold,
            max_steps=self._m1_teacher_max_steps, phase_block=phase_block,
            handoff_grace=int(os.environ.get("M1_TEACHER_HANDOFF_GRACE_STEPS", "16")),
        )
        teacher_active = self._m1_teacher_active
        valid = valid & teacher_active
        # A planner-invalid frame may still carry the measured-pose hold
        # action produced by the teacher adapter. Keep that finite hold while
        # the bounded teacher phase is active; otherwise this final wrapper
        # gate undoes the invalid-frame safety fix and snaps every joint back
        # to the nominal pose.
        hold_invalid = os.environ.get("M1_TEACHER_INVALID_HOLD_CURRENT", "1").strip().lower() not in {"0", "false", "no"}
        keep_hold = teacher_active & hold_invalid
        keep_hold = keep_hold & torch.isfinite(action).all(dim=-1)
        action = torch.where(
            (valid | keep_hold).unsqueeze(-1), action, torch.zeros_like(action)
        )
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
        valid_before_fallback = torch.as_tensor(
            valid, device=action.device, dtype=torch.bool,
        ).reshape(-1)
        teacher_active = self._m1_teacher_active.to(device=action.device, dtype=torch.bool)
        selected_leg = self._m1_teacher_selected_leg.to(device=action.device, dtype=torch.long)
        selected_phase = self._m1_teacher_selected_phase.to(device=action.device, dtype=torch.long)
        from .m1_teacher_phase import preserve_invalid_obstacle_leg_action
        action, valid, self._m1_invalid_swing_fallback = preserve_invalid_obstacle_leg_action(
            action,
            valid=valid_before_fallback,
            teacher_active=teacher_active,
            obstacle_hold=phase_hold,
            selected_leg=selected_leg,
            selected_phase=selected_phase,
            last_leg_action=self._m1_last_valid_swing_action,
            last_leg=self._m1_last_valid_swing_leg,
            last_phase=self._m1_last_valid_swing_phase,
            leg_cols=planner_cols,
        )
        remember = valid_before_fallback & teacher_active & ~recovery_mask
        self._m1_last_valid_swing_action = torch.where(
            remember[:, None], action[:, planner_cols].detach(),
            self._m1_last_valid_swing_action,
        )
        self._m1_last_valid_swing_leg = torch.where(
            remember, selected_leg, self._m1_last_valid_swing_leg,
        )
        self._m1_last_valid_swing_phase = torch.where(
            remember, selected_phase, self._m1_last_valid_swing_phase,
        )
        self._m1_teacher_reference_valid = (
            reference_valid & valid & teacher_active & ~recovery_mask
            & ~self._m1_invalid_swing_fallback & ~self._m1_strict_crossing.failed
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
        self._m1_teacher_elapsed.zero_()
        self._m1_teacher_selected_leg.zero_()
        self._m1_teacher_selected_phase.fill_(-1)
        self._m1_last_valid_swing_action.zero_()
        self._m1_last_valid_swing_leg.fill_(-1)
        self._m1_last_valid_swing_phase.fill_(-1)
        self._m1_invalid_swing_fallback.zero_()
        self._m1_teacher_selected_collision.zero_()
        self._m1_teacher_obstacle_hold.zero_()
        self._m1_teacher_obstacle_clear_steps.zero_()
        self._m1_teacher_obstacle_hold_steps.zero_()
        self._m1_teacher_hold_pose = None
        self._m1_teacher_hold_phase = None
        self._m1_teacher_hold_foot_w = None
        self._m1_teacher_hold_foot_phase = None
        self._m1_teacher_hold_foot_leg = None
        self._m1_teacher_hold_root_w = None
        self._m1_teacher_hold_rpy_w = None
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
        self._m1_strict_crossing.reset(torch.ones(self.num_envs, dtype=torch.bool, device=self.device))
        if self._m1_required_gate is not None:
            self._m1_required_gate.reset(torch.ones(self.num_envs, dtype=torch.bool, device=self.device))
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
        # Snapshot BEFORE Isaac auto-reset so terminal rewards cannot use a
        # newly spawned pose/course. Only the straight progressive rows apply.
        from .m1_required_crossing import progressive_required_wheels, required_crossing_reward
        required_zone = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        if getattr(self.unwrapped.cfg, 'm1_flat_first', False):
            levels = self.unwrapped.scene.terrain.terrain_levels
            course = self._m1_current_course()
            course['valid'] &= ((levels >= 1) & (levels <= 3))[:, None]
            required_zone = self._m1_required_gate.update(
                self.unwrapped.scene['robot'].data.root_pos_w, course,
                progressive_required_wheels(course, self.unwrapped.scene.env_origins[:, 1]),
                self._m1_strict_crossing.recovered_for_course(course))
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
        # Existing proxy only; not proof of strict per-foot crossing. Its
        # lifecycle is the measured candidate/lift/clearance state above,
        # never the clock of an optional (now disabled in PPO) teacher.
        term = terminated.bool()
        names = list(self.unwrapped.reward_manager.active_terms)
        from .m1_strict_crossing import strict_collision_from_reward_terms
        collision = strict_collision_from_reward_terms(
            self.unwrapped.reward_manager._step_reward,
            names,
        )
        # Keep the scan-disappearance metric as a proxy. Strict completion is
        # evaluated separately against the actual ordered fixed-course boxes.
        touchdown_safe = torch.zeros_like(done)
        recovery_balance_safe = torch.zeros_like(done)
        strict_crossing_touchdown = torch.zeros_like(done)
        recovery_pose_ready = torch.zeros_like(done)
        support_contact = torch.zeros((self.num_envs,4),device=done.device,dtype=torch.bool)
        try:
            contact_sensor = self.unwrapped.scene["contact_forces"]
            from .m1_ame_rewards import M1_SUPPORT_BODY_NAMES
            from extension.parallelism.rl_adapter import resolve_named_indices
            contact_ids = list(resolve_named_indices(tuple(contact_sensor.body_names), M1_SUPPORT_BODY_NAMES))
            support_force = contact_sensor.data.net_forces_w[:, contact_ids].norm(dim=-1)
            support_contact = support_force > 10.0
            from .m1_crossing_landing import crossing_touchdown_safe
            touchdown_safe = crossing_touchdown_safe(
                support_contact=support_contact,
                support_force=support_force,
                target_wheel=self._m1_strict_crossing.target_wheel.clamp(0, 3),
            )
        except Exception:
            touchdown_safe = torch.zeros_like(done)

        # A valid loaded touchdown is the crossing result.  Keep this gate
        # outside the recovery diagnostics so a missing/invalid recovery
        # measurement can never erase an already-safe crossing.
        strict_crossing_touchdown = touchdown_safe.clone()
        try:
            # Required in the normal (trace/debug disabled) training path too.
            robot = self.unwrapped.scene["robot"]
            quat = robot.data.root_quat_w
            qw, qx, qy, qz = quat.unbind(-1)
            roll = torch.atan2(2.0 * (qw * qx + qy * qz), 1.0 - 2.0 * (qx.square() + qy.square()))
            pitch = torch.asin((2.0 * (qw * qy - qz * qx)).clamp(-1.0, 1.0))
            tilt = torch.stack((roll.abs(), pitch.abs()), dim=-1).amax(dim=-1)
            angular_velocity = robot.data.root_ang_vel_w
            tilt_rate = angular_velocity[:, :2].abs().amax(dim=-1)
            # Tilt/rate, nominal joint pose, and reset-height restoration are
            # exclusively post-cross recovery gates.
            recovery_balance_safe = touchdown_safe & torch.isfinite(tilt) & (
                tilt <= min(0.15, float(os.environ.get("M1_STRICT_MAX_TILT_RAD", "0.15")))
            ) & torch.isfinite(tilt_rate) & (
                tilt_rate <= min(0.20, float(os.environ.get("M1_STRICT_MAX_TILT_RATE_RAD_S", "0.20")))
            )
            # Recovering balance also means restoring the leg configuration,
            # not merely touching down briefly in a deep crouch.  The strict
            # tracker keeps the next obstacle gated while the post-cross
            # action smoothly returns these joints toward nominal support.
            from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES
            from extension.parallelism.rl_adapter import select_named_joint_state
            from .m1_teacher_phase import m1_recovery_pose_ready
            measured_leg_pose = select_named_joint_state(
                robot.data.joint_pos,
                source_names=tuple(robot.joint_names),
                selected_names=M1_PLANNER_JOINT_NAMES,
            )
            nominal_leg_pose = select_named_joint_state(
                robot.data.default_joint_pos,
                source_names=tuple(robot.joint_names),
                selected_names=M1_PLANNER_JOINT_NAMES,
            )
            recovery_pose_ready = m1_recovery_pose_ready(
                measured_leg_pose,
                nominal_leg_pose,
                tolerance_rad=float(os.environ.get(
                    "M1_STRICT_RECOVERY_JOINT_TOL_RAD", "0.15"
                )),
            )
            from .m1_crossing_landing import m1_recovery_root_height_ready
            root_height_ready = m1_recovery_root_height_ready(
                root_z_w=robot.data.root_pos_w[:, 2],
                nominal_root_z_w=(
                    robot.data.default_root_state[:, 2]
                    + self.unwrapped.scene.env_origins[:, 2]
                ),
                tolerance_m=min(0.08, float(os.environ.get(
                    "M1_STRICT_RECOVERY_ROOT_HEIGHT_TOL_M", "0.08"
                ))),
            )
            from .m1_crossing_landing import split_crossing_and_recovery_gates
            _, recovery_balance_safe = split_crossing_and_recovery_gates(
                touchdown_safe=touchdown_safe,
                balance_recovered=recovery_balance_safe,
                nominal_pose_ready=recovery_pose_ready,
                root_height_ready=root_height_ready,
            )
        except Exception as exc:
            # An unavailable measurement is a wiring failure, not a measured
            # failure to recover. Continuing would silently train on bad labels.
            raise RuntimeError("M1 recovery measurement failed") from exc
        strict_result = {
            "episode_complete": torch.zeros_like(done),
            "attempt_started": torch.zeros_like(done),
            "event_complete": torch.zeros_like(done),
            "recovery_complete": torch.zeros_like(done),
            "recovery_frames": torch.zeros_like(done, dtype=torch.long),
        }
        try:
            from .m1_ame_rewards import M1_SUPPORT_BODY_NAMES
            from extension.parallelism.rl_adapter import resolve_named_indices
            from extension.parallelism.m1_kinematics import (
                M1_WHEEL_HORIZONTAL_ENVELOPE_M,
                M1_WHEEL_RADIUS_M,
                M1_WHEEL_THICKNESS_M,
            )
            from .m1_strict_crossing import m1_wheel_lateral_half_width_from_quat
            robot = self.unwrapped.scene["robot"]
            wheel_ids = list(resolve_named_indices(tuple(robot.body_names), M1_SUPPORT_BODY_NAMES))
            from .m1_crossing_clearance import (
                load_wheel_collision_vertices, wheel_bottom_from_vertices,
            )
            if getattr(self, '_m1_wheel_vertices_b', None) is None:
                import omni.usd
                self._m1_wheel_vertices_b = torch.tensor(
                    load_wheel_collision_vertices(
                        omni.usd.get_context().get_stage(),
                        self.unwrapped.scene.env_prim_paths[0] + '/Robot',
                        M1_SUPPORT_BODY_NAMES,
                    ), dtype=robot.data.body_pos_w.dtype, device=robot.data.body_pos_w.device,
                )
            wheel_bottom_z_w = wheel_bottom_from_vertices(
                robot.data.body_pos_w[:, wheel_ids],
                robot.data.body_quat_w[:, wheel_ids], self._m1_wheel_vertices_b,
            )
            wheel_lateral_half_width = m1_wheel_lateral_half_width_from_quat(
                robot.data.body_quat_w[:, wheel_ids],
                wheel_radius=float(M1_WHEEL_RADIUS_M),
                wheel_thickness=float(M1_WHEEL_THICKNESS_M),
            )
            if getattr(self, '_m1_course_registry', None) is not None:
                course = self._m1_current_course()
                # Isaac resets inside env.step. Never judge old-episode motion
                # using the new robot pose/terrain on a terminal observation.
                self._m1_strict_crossing.reset(done)
                course["valid"] &= ~done[:, None]
                from extension.convention import extract_yaw_batch
                yaw = extract_yaw_batch(robot.data.root_quat_w)
                command = self.unwrapped.command_manager.get_command('base_velocity')[:, :2]
                direction = torch.stack((command[:,0]*yaw.cos()-command[:,1]*yaw.sin(),
                                         command[:,0]*yaw.sin()+command[:,1]*yaw.cos()), dim=-1)
                strict_result = self._m1_strict_crossing.update(
                    wheel_pos_w=robot.data.body_pos_w[:, wheel_ids],
                    wheel_quat_w=robot.data.body_quat_w[:, wheel_ids],
                    course=course, direction_w=direction, wheel_bottom_z_w=wheel_bottom_z_w,
                    wheel_grounded=support_contact,
                    support_safe=recovery_balance_safe, touchdown_safe=strict_crossing_touchdown,
                    collision=collision, wheel_horizontal_radius=float(M1_WHEEL_HORIZONTAL_ENVELOPE_M),
                    wheel_vertical_radius=float(M1_WHEEL_RADIUS_M),wheel_thickness=float(M1_WHEEL_THICKNESS_M),
                    required_clearance=max(.03,float(os.environ.get('M1_STRICT_TOP_CLEARANCE_M','.03'))),
                    required_far_margin=max(.04,float(os.environ.get('M1_STRICT_FAR_MARGIN_M','.04'))),
                    stable_frames=max(5,int(os.environ.get('M1_STRICT_STABLE_FRAMES','5'))),
                )
            elif os.environ.get("M1_OBSTACLE_STAGE", "full").strip().lower() != "none":
                env_origins = self.unwrapped.scene.env_origins
                fixed_xy = robot.data.root_pos_w.new_tensor(M1_FIXED_SMALL_OBSTACLE_LOCAL_XY)
                centers_top = torch.cat((
                    env_origins[:, None, :2] + fixed_xy[None, :, :],
                    (env_origins[:, 2:3] + float(os.environ.get(
                        "M1_SMALL_OBSTACLE_HEIGHT_M", "0.10",
                    )))[:, None, :].expand(-1, fixed_xy.shape[0], -1),
                ), dim=-1)
                strict_result = self._m1_strict_crossing.update(
                    wheel_pos_w=robot.data.body_pos_w[:, wheel_ids],
                    obstacle_centers_top_w=centers_top,
                    support_safe=recovery_balance_safe,
                    touchdown_safe=strict_crossing_touchdown,
                    collision=collision,
                    wheel_horizontal_radius=float(M1_WHEEL_HORIZONTAL_ENVELOPE_M),
                    wheel_lateral_half_width=wheel_lateral_half_width,
                    wheel_vertical_radius=float(M1_WHEEL_RADIUS_M),
                    wheel_bottom_z_w=wheel_bottom_z_w,
                    obstacle_half_extents=(M1_SMALL_OBSTACLE_DIAMETER_M / 2.0,
                                           M1_SMALL_OBSTACLE_DIAMETER_M / 2.0),
                    required_clearance=max(0.03, float(os.environ.get("M1_STRICT_TOP_CLEARANCE_M", "0.03"))),
                    required_far_margin=max(0.04, float(os.environ.get("M1_STRICT_FAR_MARGIN_M", "0.04"))),
                    stable_frames=max(5, int(os.environ.get("M1_STRICT_STABLE_FRAMES", "5"))),
                )
        except Exception as exc:
            if getattr(self, '_m1_course_registry', None) is not None:
                raise RuntimeError('mixed-course strict geometry failed') from exc
            strict_result = {
                "episode_complete": torch.zeros_like(done),
                "attempt_started": torch.zeros_like(done),
                "event_complete": torch.zeros_like(done),
                "recovery_complete": torch.zeros_like(done),
                "recovery_frames": torch.zeros_like(done, dtype=torch.long),
            }
        strict_crossing_complete = strict_result["episode_complete"]
        if getattr(self.unwrapped.cfg, 'm1_flat_first', False):
            rewards, removed, event_bonus = required_crossing_reward(
                rewards, self.unwrapped.reward_manager._step_reward,
                float(self.unwrapped.step_dt), blocked=required_zone, collision=collision,
                done=done, prelift=strict_result.get('single_prelift_event', torch.zeros_like(done)),
                recovery=strict_result['recovery_complete'],
                prelift_progress_delta=strict_result.get('prelift_progress_delta', torch.zeros_like(rewards)))
            # Isaac may reuse extras. Snapshot tensors so runner steps do not
            # alias the next frame's dict or in-place updated measurements.
            extras['log'] = {k: v.detach().clone() if isinstance(v, torch.Tensor) else v
                             for k, v in extras.get('log', {}).items()}
            log = extras['log']
            log['RequiredCrossing/removed_positive_reward'] = removed.mean()
            log['RequiredCrossing/event_bonus'] = event_bonus.mean()
            log['RequiredCrossing/zone_fraction'] = required_zone.float().mean()
            log['RequiredCrossing/prelift_events'] = strict_result.get('single_prelift_event', torch.zeros_like(done)).sum()
            log['RequiredCrossing/prelift_progress_delta'] = strict_result.get('prelift_progress_delta', torch.zeros_like(rewards)).mean()
            log['RequiredCrossing/loaded_touchdown_fraction'] = touchdown_safe.float().mean()
            log['RequiredCrossing/recovery_ready_fraction'] = recovery_balance_safe.float().mean()
            log['RequiredCrossing/stable_landings'] = strict_result['recovery_complete'].sum()
            log['RequiredCrossing/collision_frames'] = (required_zone & collision).sum()
            samples = strict_result.get('overlap_sample', torch.zeros_like(done)) & ~done
            clearance = strict_result.get('bottom_clearance', torch.full_like(rewards, float('nan')))
            log['RequiredCrossing/clearance_samples'] = samples.sum()
            log['RequiredCrossing/min_bottom_clearance_m'] = (
                clearance[samples].min() if samples.any() else rewards.new_tensor(float('nan')))
        from .m1_mixed_course import record_curriculum_strict_events
        record_curriculum_strict_events(self.unwrapped, strict_result, done)
        self.crossing_metrics.update(
            candidate=small_candidate,
            large_candidate=large_candidate,
            crossing_complete=crossing_complete,
            strict_crossing_complete=strict_crossing_complete,
            strict_crossing_attempt=strict_result["attempt_started"],
            strict_crossing_event=strict_result["event_complete"],
            strict_recovery_complete=strict_result["recovery_complete"],
            strict_recovery_frames=strict_result["recovery_frames"],
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
        self._m1_teacher_active &= ~strict_crossing_complete & ~teacher_phase_done & ~done
        self._m1_teacher_elapsed = torch.where(
            self._m1_teacher_active, self._m1_teacher_elapsed,
            torch.zeros_like(self._m1_teacher_elapsed),
        )
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
        self._m1_strict_crossing.reset(done)
        if self._m1_required_gate is not None:
            self._m1_required_gate.reset(done)
        # Isaac auto-reset bypasses wrapper.reset(). Never retain the previous
        # course's world-frame wheel/root anchor in a newly reset row.
        if self._m1_teacher_hold_foot_phase is not None:
            self._m1_teacher_hold_foot_phase.masked_fill_(done, -1)
        if self._m1_teacher_hold_foot_leg is not None:
            self._m1_teacher_hold_foot_leg.masked_fill_(done, -1)
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
