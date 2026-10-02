"""M1 MPC reference to normalized 16-D AME teacher action adapter."""
from __future__ import annotations

import os
import torch

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES,
    M1_PLANNER_JOINT_NAMES,
    M1_WHEEL_JOINT_NAMES,
    M1_ABAD_LOWER, M1_ABAD_UPPER,
    M1_HIP_LOWER, M1_HIP_UPPER,
    M1_KNEE_LOWER, M1_KNEE_UPPER,
)
from extension.parallelism.rl_adapter import resolve_named_indices
from ame_baseline.m1_ame_contract import (
    M1_LEG_ACTION_SCALE_RAD, M1_WHEEL_ACTION_SCALE_RAD_S,
    M1_WHEEL_SPEED_LIMIT_RAD_S,
)


def reference_to_m1_action(
    reference: dict[str, torch.Tensor],
    default_joint_pos: torch.Tensor,
    *,
    current_joint_pos: torch.Tensor | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Convert MPC ``joint_angles`` into M1's normalized action and validity mask.

    The MPC reference is ordered by ``M1_PLANNER_JOINT_NAMES``.  The returned
    action preserves the 16-column asset order used by ``M1MixedJointAction``.
    Invalid/nonfinite references are replaced by zeros and marked invalid.
    """
    target = reference.get("joint_angles")
    valid = reference.get("valid_mask", reference.get("valid"))
    if target is None or target.ndim != 2 or target.shape[1] != len(M1_PLANNER_JOINT_NAMES):
        raise ValueError("M1 MPC joint_angles must have shape [B,12]")
    if default_joint_pos.ndim != 2 or default_joint_pos.shape[1] != len(M1_ASSET_JOINT_NAMES):
        raise ValueError("default_joint_pos must have shape [B,16]")
    if current_joint_pos is not None:
        if current_joint_pos.ndim != 2 or current_joint_pos.shape != default_joint_pos.shape:
            raise ValueError("current_joint_pos must match default_joint_pos shape [B,16]")
    finite = torch.isfinite(target).all(dim=-1)
    finite = finite & torch.isfinite(default_joint_pos).all(dim=-1)
    if current_joint_pos is not None:
        finite = finite & torch.isfinite(current_joint_pos).all(dim=-1)
    if valid is None:
        valid = finite
    else:
        valid = torch.as_tensor(valid, device=target.device, dtype=torch.bool).reshape(-1) & finite
    out = torch.zeros(default_joint_pos.shape[0], len(M1_ASSET_JOINT_NAMES), device=target.device, dtype=target.dtype)
    planner_cols = resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES)
    wheel_cols = resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES)
    lower = target.new_tensor(tuple(v for triple in zip(M1_ABAD_LOWER, M1_HIP_LOWER, M1_KNEE_LOWER) for v in triple))
    upper = target.new_tensor(tuple(v for triple in zip(M1_ABAD_UPPER, M1_HIP_UPPER, M1_KNEE_UPPER) for v in triple))
    leg_target = target[:, :len(M1_PLANNER_JOINT_NAMES)]
    default_legs = default_joint_pos[:, planner_cols]
    # The generic planner may mark a diagonal pair as swing at the same time.
    # M1 must cross one foot at a time, however: choose exactly one member of
    # that planned swing set and hold the other three at their measured pose.
    # We alternate the selected member using the horizon phase so both legs in
    # each pair (and therefore all four legs over a crossing) are exercised.
    contact_state = reference.get("contact_state")
    swing = None
    if current_joint_pos is not None and contact_state is not None:
        contact_state = torch.as_tensor(contact_state, device=target.device, dtype=torch.bool)
        if tuple(contact_state.shape) == (int(target.shape[0]), 4):
            planned_swing = torch.logical_not(contact_state)
            phase_index = torch.as_tensor(
                reference.get("serial_phase_index", reference.get("phase_index", torch.zeros(target.shape[0], device=target.device))),
                device=target.device,
                dtype=torch.long,
            ).reshape(-1)
            if int(phase_index.numel()) == 1 and int(target.shape[0]) > 1:
                phase_index = phase_index.expand(int(target.shape[0]))
            leg_index = torch.arange(4, device=target.device).view(1, 4)
            # Two deterministic priorities avoid starving the rear legs when
            # the planner emits the usual diagonal pairs.  If only one swing
            # leg is supplied, it remains selected unchanged.
            # Keep one member of the planned swing set selected for the
            # whole reference phase. Alternating on phase parity split the
            # lift into two half-steps, so neither M1 wheel cleared a 10 cm
            # box. The next phase selects the next leg deterministically.
            has_swing = planned_swing.any(dim=1)
            # Select one leg from the planner's swing set and advance to the
            # next candidate on the planner phase.  Always taking argmin
            # starves the other three legs and turns a serial crossing into a
            # repeated single-leg scrape.
            phase_block = max(1, int(os.environ.get("M1_TEACHER_PHASE_BLOCK", "8")))
            phase_slot = torch.div(phase_index, phase_block, rounding_mode="floor")
            # Some MPC frames report all four feet as support exactly when the
            # obstacle enters the short trigger window.  Keep the crossing
            # teacher alive by selecting one deterministic leg in that case;
            # the wrapper masks this path until the short trigger is observed.
            fallback_leg = phase_slot.remainder(4)
            fallback_swing = torch.nn.functional.one_hot(fallback_leg, num_classes=4).to(torch.bool)
            planned_swing = torch.where(
                has_swing.unsqueeze(1), planned_swing, fallback_swing,
            )
            has_swing = planned_swing.any(dim=1)
            # Recompute ranks after inserting a fallback leg; using the old
            # all-support ranks would select no leg unless the fallback index
            # happened to be zero.
            swing_rank = torch.cumsum(planned_swing.to(torch.long), dim=1) - 1
            swing_count = planned_swing.sum(dim=1).clamp_min(1)
            selected_rank = phase_slot.remainder(swing_count)
            swing = planned_swing & (swing_rank == selected_rank[:, None]) & has_swing[:, None]
            # The action decoder interprets zero as the nominal pose, not as
            # a physical hold.  Stance legs therefore must target their
            # measured pose; otherwise every swing phase pulls the support
            # polygon back to default and the body tips. Only the selected
            # leg receives the crossing target.
            nominal_legs = default_legs.to(device=target.device, dtype=target.dtype)
            stance_legs = current_joint_pos[:, planner_cols]
            hold_legs = reference.get("hold_joint_angles")
            if hold_legs is not None:
                hold_legs = torch.as_tensor(hold_legs, device=target.device, dtype=target.dtype)
                if tuple(hold_legs.shape) == tuple(stance_legs.shape):
                    stance_legs = hold_legs
            leg_target = torch.where(
                swing.unsqueeze(-1),
                leg_target.reshape(-1, 4, 3),
                stance_legs.reshape(-1, 4, 3),
            ).reshape(-1, len(M1_PLANNER_JOINT_NAMES))
    # Keep enough total knee/hip excursion for the strict 5 cm top clearance,
    # while slewing from the measured pose instead of injecting a large
    # position jump at 50 Hz.  The old default (0.30 rad from nominal) capped
    # the physical wheel bottom below the required height; the slew limiter
    # lets us use a taller target without destabilizing the base.
    desired_legs = leg_target.clamp(lower, upper)
    # The 0.55 rad cap clipped the M1 knee target for a 10 cm box before the
    # wheel centre reached the required top+radius+clearance.  Keep the
    # actuator/joint limits as the final guard, but allow the IK target to
    # request the full reachable lift; the slew limiter still makes the
    # command progressive and stable.
    if swing is not None and current_joint_pos is not None:
        # Generic MPC references can under-lift the M1 wheel. Enforce a
        # reachable single-leg clearance target before slew limiting: hip
        # retracts and knee flexes only on the selected leg.
        current_leg_pose = current_joint_pos[:, planner_cols].reshape(-1, 4, 3)
        desired_leg_pose = desired_legs.reshape(-1, 4, 3)
        # Most of the vertical clearance comes from knee flexion; a large
        # hip excursion rolls the M1 body while only one leg is unloaded.
        min_hip = current_leg_pose[..., 1] - float(os.environ.get("M1_TEACHER_MIN_HIP_LIFT_RAD", "0.12"))
        # Do not let repeated one-leg phases ratchet the hip farther backward
        # on every frame.  The previous current-pose-only floor accumulated
        # drift (e.g. -0.88 -> -1.03 rad), rolling the body while the knee was
        # lifting.  Bound the lift around the nominal support pose instead.
        hip_floor = nominal_legs.reshape(-1, 4, 3)[..., 1] - float(
            os.environ.get("M1_TEACHER_MAX_HIP_LIFT_RAD", "0.18")
        )
        min_hip = torch.maximum(min_hip, hip_floor)
        min_knee = current_leg_pose[..., 2] + float(os.environ.get("M1_TEACHER_MIN_KNEE_LIFT_RAD", "0.80"))
        desired_leg_pose[..., 1] = torch.where(
            swing, torch.maximum(desired_leg_pose[..., 1], min_hip), desired_leg_pose[..., 1],
        )
        desired_leg_pose[..., 2] = torch.where(
            swing, torch.maximum(desired_leg_pose[..., 2], min_knee), desired_leg_pose[..., 2],
        )
        # The generic planner's lateral/leg-frame angles are not safe as
        # direct M1 commands.  Bound only the selected swing leg around the
        # standing pose; the knee keeps enough extension for a 10 cm obstacle
        # while ABAD and hip cannot roll the floating base sideways.
        nominal_pose = nominal_legs.reshape(-1, 4, 3)
        abad_span = float(os.environ.get("M1_TEACHER_MAX_ABAD_RAD", "0.15"))
        hip_span = float(os.environ.get("M1_TEACHER_MAX_HIP_LIFT_RAD", "0.18"))
        knee_span = float(os.environ.get("M1_TEACHER_MAX_KNEE_LIFT_RAD", "1.10"))
        desired_leg_pose[..., 0] = torch.where(
            swing,
            desired_leg_pose[..., 0].clamp(
                nominal_pose[..., 0] - abad_span, nominal_pose[..., 0] + abad_span
            ),
            desired_leg_pose[..., 0],
        )
        desired_leg_pose[..., 1] = torch.where(
            swing,
            desired_leg_pose[..., 1].clamp(
                nominal_pose[..., 1] - hip_span, nominal_pose[..., 1] + hip_span
            ),
            desired_leg_pose[..., 1],
        )
        desired_leg_pose[..., 2] = torch.where(
            swing,
            desired_leg_pose[..., 2].clamp(
                nominal_pose[..., 2], nominal_pose[..., 2] + knee_span
            ),
            desired_leg_pose[..., 2],
        )
        desired_legs = desired_leg_pose.reshape(-1, len(M1_PLANNER_JOINT_NAMES))
    max_delta = float(os.environ.get("M1_TEACHER_MAX_DELTA_RAD", "1.10"))
    desired_legs = default_legs + (desired_legs - default_legs).clamp(-max_delta, max_delta)
    if current_joint_pos is not None:
        current_legs = current_joint_pos[:, planner_cols]
        slew = float(os.environ.get("M1_TEACHER_SLEW_RAD", "0.12"))
        slewed_legs = current_legs + (desired_legs - current_legs).clamp(-slew, slew)
        if swing is not None:
            # Preserve measured stance targets so the position-action decoder
            # does not reinterpret zero as a reset-to-default command.
            desired_legs = torch.where(
                swing.unsqueeze(-1),
                slewed_legs.reshape(-1, 4, 3),
                stance_legs.reshape(-1, 4, 3),
            ).reshape(-1, len(M1_PLANNER_JOINT_NAMES))
        else:
            desired_legs = slewed_legs
    delta = desired_legs - default_legs
    if swing is not None:
        # Enforce the serial-crossing contract at the action boundary.  The
        # The selected leg is the only leg whose target is intentionally
        # changed; stance deltas encode physical hold relative to nominal.
        delta = torch.where(
            swing.unsqueeze(-1),
            delta.reshape(-1, 4, 3),
            delta.reshape(-1, 4, 3),
        ).reshape(-1, len(M1_PLANNER_JOINT_NAMES))
    out[:, planner_cols] = (delta / M1_LEG_ACTION_SCALE_RAD).clamp(-1.0, 1.0)
    wheel_target = target.new_zeros((target.shape[0], len(wheel_cols)))
    # MPC joint_angles only contain the 12 leg joints; wheels are commanded by
    # the current base command and remain neutral until a wheel reference exists.
    wheel_target = wheel_target.clamp(-M1_WHEEL_SPEED_LIMIT_RAD_S, M1_WHEEL_SPEED_LIMIT_RAD_S)
    out[:, wheel_cols] = wheel_target / M1_WHEEL_ACTION_SCALE_RAD_S
    # Saturation is a diagnostic, not a validity gate.  Large but finite
    # swing targets are expected during obstacle crossing; clipping them to
    # the actuator action range still provides a useful lift command.  The
    # debug output records the fraction so training can monitor how often the
    # teacher asks for more than the normalized action range.
    out[~valid] = 0.0
    # Never let a malformed measured pose leak a NaN into the rollout.  The
    # corresponding row is already marked invalid above, so the caller will
    # fall back to the student action for it.
    out = torch.nan_to_num(out, nan=0.0, posinf=1.0, neginf=-1.0).clamp(-1.0, 1.0)
    if os.environ.get("M1_TEACHER_DEBUG") == "1" and not getattr(reference_to_m1_action, "_debugged", False):
        reference_to_m1_action._debugged = True
        print(
            "[M1 teacher debug] target_range=(%.4f,%.4f) default_range=(%.4f,%.4f) action_range=(%.4f,%.4f) saturated=%.3f valid=%.3f" % (
                float(leg_target.min().item()), float(leg_target.max().item()),
                float(default_legs.min().item()), float(default_legs.max().item()),
                float(out[:, planner_cols].min().item()), float(out[:, planner_cols].max().item()),
                float((out[:, planner_cols].abs().amax(dim=-1) >= 0.999).float().mean().item()),
                float(valid.float().mean().item()),
            ), flush=True,
        )
        print("[M1 teacher debug] delta_abs_max=%.4f delta_abs_mean=%.4f per_joint_delta=%s" % (
            float((leg_target - default_legs).abs().max().item()),
            float((leg_target - default_legs).abs().mean().item()),
            [round(float(x), 4) for x in (leg_target - default_legs)[0].detach().cpu().tolist()],
        ), flush=True)
        if swing is not None:
            print(
                "[M1 teacher debug] single_leg_swing_fraction=%.3f max_swing_per_env=%d"
                % (float(swing.float().mean().item()), int(swing.sum(dim=1).max().item())),
                flush=True,
            )
    return out, valid


def apply_m1_teacher_safety(
    action: torch.Tensor,
    valid: torch.Tensor,
    root_rpy: torch.Tensor,
    *,
    max_tilt_rad: float | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Stop the MPC teacher before it can amplify a falling/tilting body.

    The teacher is allowed to request a large wheel clearance, but it must
    hand control back to PPO as soon as the measured base tilt is outside the
    recoverable envelope.  This is deliberately a pure tensor helper so the
    safety contract is unit-testable without starting Isaac Sim.
    """
    if action.ndim != 2 or valid.ndim != 1 or root_rpy.ndim != 2:
        raise ValueError("action/valid/root_rpy must have shapes [B,A], [B], [B,3]")
    if action.shape[0] != valid.shape[0] or root_rpy.shape != (action.shape[0], 3):
        raise ValueError("action, valid, and root_rpy batch dimensions must match")
    if max_tilt_rad is None:
        max_tilt_rad = float(os.environ.get("M1_TEACHER_MAX_TILT_RAD", "0.30"))
    tilt = root_rpy[:, :2].abs().amax(dim=-1)
    safe = valid.to(dtype=torch.bool) & torch.isfinite(tilt) & (tilt <= float(max_tilt_rad))
    safe_action = torch.where(safe.unsqueeze(-1), action, torch.zeros_like(action))
    return safe_action, safe


__all__ = ["apply_m1_teacher_safety", "reference_to_m1_action"]
