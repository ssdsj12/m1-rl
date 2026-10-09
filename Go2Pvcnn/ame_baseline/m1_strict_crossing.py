"""Measured, per-obstacle strict crossing gate for the fixed M1 course.

This is deliberately stricter than the semantic-scan proxy.  It binds lift
clearance and far-side passage to one measured wheel and one ordered obstacle,
then requires loaded four-wheel touchdown beyond the far edge before recording success.
Consecutive nominal-support frames are a separate recovery gate before the
course advances to its next obstacle.
It does not infer success from scan disappearance or a commanded swing.
"""
from __future__ import annotations

import torch


def m1_wheel_lateral_half_width_from_quat(
    quat_wxyz: torch.Tensor,
    *,
    wheel_radius: float,
    wheel_thickness: float,
) -> torch.Tensor:
    """Project the M1 wheel cylinder onto world Y for lane-overlap checks.

    The M1 USD wheel axle is local Y. Its world-Y footprint therefore combines
    the axle half-thickness and the circular radius according to orientation.
    """
    quat = torch.as_tensor(quat_wxyz)
    if quat.ndim < 1 or quat.shape[-1] != 4 or not quat.is_floating_point():
        raise ValueError("quat_wxyz must be a floating tensor ending in 4")
    if not torch.isfinite(quat).all():
        raise ValueError("wheel quaternion must be finite")
    radius, thickness = float(wheel_radius), float(wheel_thickness)
    if not torch.isfinite(torch.tensor((radius, thickness))).all() or min(radius, thickness) <= 0:
        raise ValueError("wheel dimensions must be finite and positive")
    quat = quat / torch.linalg.vector_norm(quat, dim=-1, keepdim=True).clamp_min(1.0e-12)
    _, qx, _, qz = quat.unbind(dim=-1)
    axis_y = (1.0 - 2.0 * (qx.square() + qz.square())).abs().clamp(0.0, 1.0)
    radial_y = (1.0 - axis_y.square()).clamp_min(0.0).sqrt()
    return (0.5 * thickness) * axis_y + radius * radial_y


def strict_collision_from_reward_terms(
    step_rewards: torch.Tensor,
    active_terms: tuple[str, ...] | list[str],
) -> torch.Tensor:
    """Combine geometry and measured non-support obstacle contacts.

    Strict crossing success is collision-free, so both the semantic geometry
    penalty and the PhysX non-support contact penalty invalidate an attempt.
    Nonfinite reward values fail closed rather than silently certifying a pass.
    """
    rewards = torch.as_tensor(step_rewards)
    names = tuple(active_terms)
    if rewards.ndim != 2 or rewards.shape[1] != len(names):
        raise ValueError("step_rewards must be [num_envs, len(active_terms)]")
    collision = torch.zeros(rewards.shape[0], dtype=torch.bool, device=rewards.device)
    for name in ("parallelism_geometry_collision", "non_support_obstacle_contact"):
        if name in names:
            term = rewards[:, names.index(name)]
            collision |= ~torch.isfinite(term) | (term != 0)
    return collision


class StrictCrossingTracker:
    def __init__(self, num_envs: int, device: torch.device | str, *, obstacle_count: int):
        if int(num_envs) < 1 or int(obstacle_count) < 1:
            raise ValueError("num_envs and obstacle_count must be positive")
        self.device = torch.device(device)
        self.obstacle_count = int(obstacle_count)
        self.progress = torch.zeros(num_envs, dtype=torch.long, device=self.device)
        self.crossing_count = torch.zeros_like(self.progress)
        self.target_wheel = torch.full_like(self.progress, -1)
        self.clearance_seen = torch.zeros(num_envs, dtype=torch.bool, device=self.device)
        self.far_seen = torch.zeros_like(self.clearance_seen)
        self.stable_steps = torch.zeros_like(self.progress)
        self.recovery_elapsed_frames = torch.zeros_like(self.progress)
        self.awaiting_recovery = torch.zeros_like(self.clearance_seen)
        self.failed = torch.zeros_like(self.clearance_seen)

    def reset(self, rows: torch.Tensor) -> None:
        rows = torch.as_tensor(rows, dtype=torch.bool, device=self.device)
        if rows.shape != self.progress.shape:
            raise ValueError("rows must be bool [num_envs]")
        self.progress[rows] = 0
        self.crossing_count[rows] = 0
        self.target_wheel[rows] = -1
        self.clearance_seen[rows] = False
        self.far_seen[rows] = False
        self.stable_steps[rows] = 0
        self.recovery_elapsed_frames[rows] = 0
        self.awaiting_recovery[rows] = False
        self.failed[rows] = False

    @torch.no_grad()
    def update(
        self,
        *,
        wheel_pos_w: torch.Tensor,
        obstacle_centers_top_w: torch.Tensor,
        support_safe: torch.Tensor,
        collision: torch.Tensor,
        wheel_horizontal_radius: float,
        wheel_lateral_half_width: float | torch.Tensor,
        wheel_vertical_radius: float,
        obstacle_half_extents: tuple[float, float] | torch.Tensor,
        touchdown_safe: torch.Tensor,
        wheel_bottom_z_w: torch.Tensor | None = None,
        required_clearance: float = 0.05,
        required_far_margin: float = 0.04,
        stable_frames: int = 5,
        approach_distance: float = 0.25,
    ) -> dict[str, torch.Tensor]:
        """Record a collision-free passage and safe touchdown before recovery.

        ``obstacle_centers_top_w`` is ``[B,N,3]`` with X/Y center and the
        actual top Z. Obstacles must be ordered along the course direction.
        Production supplies ``wheel_bottom_z_w`` from measured wheel poses and
        authored collision meshes. The scalar-radius fallback is retained for
        legacy analytic callers only; it is not an oriented-wheel measurement.
        A target wheel is latched on the correct lateral track; its measured
        bottom must clear the top while over the obstacle, and that same
        wheel's horizontal envelope must then pass the far edge.  The event is
        not complete until ``touchdown_safe`` confirms a loaded touchdown beyond
        the obstacle. It does not require recovered nominal balance.
        Afterwards ``support_safe`` governs balance recovery and advancement
        to the next obstacle.
        """
        if wheel_pos_w.ndim != 3 or wheel_pos_w.shape[1:] != (4, 3):
            raise ValueError("wheel_pos_w must be [B,4,3]")
        batch = self.progress.shape[0]
        if wheel_pos_w.shape[0] != batch or wheel_pos_w.device != self.device:
            raise ValueError("wheel_pos_w batch/device mismatch")
        expected = (batch, self.obstacle_count, 3)
        if obstacle_centers_top_w.shape != expected or obstacle_centers_top_w.device != self.device:
            raise ValueError(f"obstacle_centers_top_w must be {expected} on {self.device}")
        for name, value in (("support_safe", support_safe), ("touchdown_safe", touchdown_safe),
                            ("collision", collision)):
            if value.shape != (batch,) or value.device != self.device or value.dtype != torch.bool:
                raise ValueError(f"{name} must be bool [B] on {self.device}")
        if not wheel_pos_w.is_floating_point() or not obstacle_centers_top_w.is_floating_point():
            raise ValueError("wheel and obstacle geometry must be floating point")
        if wheel_bottom_z_w is not None:
            if (wheel_bottom_z_w.shape != (batch, 4)
                    or wheel_bottom_z_w.device != self.device
                    or not wheel_bottom_z_w.is_floating_point()
                    or not torch.isfinite(wheel_bottom_z_w).all()):
                raise ValueError('measured wheel bottom must be finite aligned [B,4]')
        lateral_half_width = torch.as_tensor(
            wheel_lateral_half_width, dtype=wheel_pos_w.dtype, device=self.device
        )
        if lateral_half_width.ndim == 0:
            lateral_half_width = lateral_half_width.expand(batch, 4)
        if lateral_half_width.shape != (batch, 4):
            raise ValueError("wheel_lateral_half_width must be scalar or [B,4]")
        if not torch.isfinite(lateral_half_width).all():
            raise ValueError("wheel lateral widths must be finite")
        if not torch.isfinite(torch.tensor((wheel_horizontal_radius, wheel_vertical_radius,
                                            required_clearance,
                                            required_far_margin, approach_distance))).all():
            raise ValueError("crossing dimensions must be finite")
        extents = torch.as_tensor(obstacle_half_extents, device=self.device, dtype=wheel_pos_w.dtype)
        if extents.shape == (2,):
            extents = extents.expand(batch, 2)
        if extents.shape != (batch, 2) or not torch.isfinite(extents).all() or (extents <= 0).any():
            raise ValueError('obstacle half extents must be finite positive [2] or [B,2]')
        hx, hy = extents.unbind(-1)
        if min(wheel_horizontal_radius, wheel_vertical_radius) <= 0 or torch.any(lateral_half_width <= 0):
            raise ValueError("wheel radii and obstacle half-extents must be positive")
        stable_frames = max(1, int(stable_frames))

        event_complete = torch.zeros(batch, dtype=torch.bool, device=self.device)
        recovery_complete = torch.zeros_like(event_complete)
        attempt_started = torch.zeros_like(event_complete)
        course_active = (self.progress < self.obstacle_count) & ~self.failed
        safe_geometry = (torch.isfinite(wheel_pos_w).all(dim=(1, 2))
                         & torch.isfinite(obstacle_centers_top_w).all(dim=(1, 2)))
        rows = torch.arange(batch, device=self.device)
        event_index = self.progress.clamp_max(self.obstacle_count - 1)
        obstacle = obstacle_centers_top_w[rows, event_index]
        wheel_xy = wheel_pos_w[..., :2]
        lateral_match = (wheel_xy[..., 1] - obstacle[:, None, 1]).abs() <= hy[:, None] + lateral_half_width
        near_x = obstacle[:, 0] - hx
        far_x = obstacle[:, 0] + hx
        before_far = wheel_xy[..., 0] - float(wheel_horizontal_radius) <= far_x[:, None]
        approach = wheel_xy[..., 0] + float(wheel_horizontal_radius) >= near_x[:, None] - float(approach_distance)
        eligible = (lateral_match & before_far & approach & course_active[:, None]
                    & safe_geometry[:, None] & ~self.awaiting_recovery[:, None])
        has_target = self.target_wheel >= 0
        choose_target = (course_active & safe_geometry & ~self.awaiting_recovery
                         & ~has_target & eligible.any(dim=-1))
        frontmost = torch.where(eligible, wheel_xy[..., 0], torch.full_like(wheel_xy[..., 0], -torch.inf)).argmax(dim=-1)
        self.target_wheel = torch.where(choose_target, frontmost, self.target_wheel)
        attempt_started = choose_target
        # Record the obstacle attempt before latching same-frame contact as a
        # failure. Otherwise a collision at the approach boundary disappears
        # from the strict-success denominator.
        self.failed |= course_active & collision
        active = course_active & safe_geometry & ~collision & ~self.failed
        if not bool(active.any()):
            return {"attempt_started": attempt_started,
                    "target_wheel": self.target_wheel.clone(),
                    "event_complete": event_complete,
                    "recovery_complete": recovery_complete,
                    "episode_complete": (self.crossing_count >= self.obstacle_count) & ~self.failed,
                    "progress": self.progress.clone(),
                    "crossing_count": self.crossing_count.clone(),
                    "recovery_frames": self.recovery_elapsed_frames.clone(),
                    "failed": self.failed.clone(),
                    "clearance_latched": self.clearance_seen.clone(),
                    "far_latched": self.far_seen.clone()}
        has_target = self.target_wheel >= 0
        selected = self.target_wheel.clamp_min(0)
        selected_pos = wheel_pos_w[rows, selected]
        selected_lateral_half_width = lateral_half_width[rows, selected]
        selected_matches_lane = (selected_pos[:, 1] - obstacle[:, 1]).abs() <= hy + selected_lateral_half_width

        overlaps_top = ((selected_pos[:, 0] + float(wheel_horizontal_radius) >= near_x)
                        & (selected_pos[:, 0] - float(wheel_horizontal_radius) <= far_x))
        measured_bottom = (wheel_bottom_z_w[rows, selected] if wheel_bottom_z_w is not None
                           else selected_pos[:, 2] - float(wheel_vertical_radius))
        clearance_now = (active & ~self.awaiting_recovery & has_target & selected_matches_lane & overlaps_top
                         & (measured_bottom >= obstacle[:, 2] + float(required_clearance)))
        far_now = (active & ~self.awaiting_recovery & has_target & selected_matches_lane
                   & (selected_pos[:, 0] - float(wheel_horizontal_radius) - far_x
                      >= float(required_far_margin)))
        self.clearance_seen |= clearance_now
        self.far_seen |= far_now

        # Do not switch to the nominal recovery command at geometric clearance
        # alone. The target wheel must first land safely on the far side; only
        # then is the crossing counted and balance recovery allowed to begin.
        event_complete = (active & ~self.awaiting_recovery & has_target
                          & self.clearance_seen & self.far_seen & far_now
                          & touchdown_safe)
        self.awaiting_recovery |= event_complete
        self.crossing_count += event_complete.to(self.crossing_count.dtype)

        # Recovery starts on the next observation after the geometric event;
        # don't count the crossing frame as a recovery frame.
        recovery_active = active & self.awaiting_recovery & ~event_complete
        self.recovery_elapsed_frames += recovery_active.to(self.recovery_elapsed_frames.dtype)
        self.stable_steps = torch.where(
            recovery_active & support_safe, self.stable_steps + 1,
            torch.where(recovery_active, torch.zeros_like(self.stable_steps), self.stable_steps),
        )
        recovery_complete = recovery_active & (self.stable_steps >= stable_frames)
        self.progress += recovery_complete.to(self.progress.dtype)
        self.target_wheel = torch.where(recovery_complete, torch.full_like(self.target_wheel, -1), self.target_wheel)
        self.clearance_seen &= ~recovery_complete
        self.far_seen &= ~recovery_complete
        recovery_frames = self.recovery_elapsed_frames.clone()
        self.stable_steps = torch.where(recovery_complete, torch.zeros_like(self.stable_steps), self.stable_steps)
        self.recovery_elapsed_frames = torch.where(
            recovery_complete, torch.zeros_like(self.recovery_elapsed_frames),
            self.recovery_elapsed_frames)
        self.awaiting_recovery &= ~recovery_complete
        return {"attempt_started": attempt_started,
                "target_wheel": self.target_wheel.clone(),
                "event_complete": event_complete,
                "recovery_complete": recovery_complete,
                "episode_complete": (self.crossing_count >= self.obstacle_count) & ~self.failed,
                "progress": self.progress.clone(),
                "crossing_count": self.crossing_count.clone(),
                "recovery_frames": recovery_frames,
                "failed": self.failed.clone(),
                "clearance_latched": self.clearance_seen.clone(),
                "far_latched": self.far_seen.clone()}
