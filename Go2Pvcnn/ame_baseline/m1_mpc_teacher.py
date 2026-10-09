"""M1 MPC reference to normalized 16-D AME teacher action adapter."""
from __future__ import annotations

import os
import torch

from ame_baseline.m1_cartesian_step import cartesian_joint_step

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES,
    M1_PLANNER_JOINT_NAMES,
    M1_WHEEL_JOINT_NAMES,
    M1_ABAD_LOWER, M1_ABAD_UPPER,
    M1_HIP_LOWER, M1_HIP_UPPER,
    M1_KNEE_LOWER, M1_KNEE_UPPER,
    m1_fk, m1_ik, rpy_to_rotation_matrix,
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
    # During a serial single-leg transfer the planner can briefly mark the
    # whole reference invalid while contact sensors transition. Zeroing the
    # complete teacher action in that window removes stance hold and can let
    # the body fall into the obstacle. Keep finite guards, but make the
    # planner validity gate optional for the M1 crossing teacher.
    ignore_planner_valid = os.environ.get("M1_TEACHER_IGNORE_PLANNER_VALID", "0").strip().lower() not in {"0", "false", "no"}
    if valid is None or ignore_planner_valid:
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
    cartesian_foot_target = None
    if os.environ.get("M1_TEACHER_NATIVE_MPC", "0") == "1":
        # Diagnostic/production mode for the planner's own trajectory. Do
        # not replace its contact schedule with the legacy serial adapter;
        # the planner already emits terrain-aware joint targets and support
        # transitions. Keep only finite/limit/slew guards at this boundary.
        desired_native = leg_target.clamp(lower, upper)
        if current_joint_pos is not None:
            current_native = current_joint_pos[:, planner_cols]
            native_slew = float(os.environ.get("M1_TEACHER_SLEW_RAD", "0.28"))
            desired_native = current_native + (desired_native - current_native).clamp(-native_slew, native_slew)
        out[:, planner_cols] = ((desired_native - default_legs) / M1_LEG_ACTION_SCALE_RAD).clamp(-1.0, 1.0)
        out[:, wheel_cols] = 0.0
        out[~valid] = 0.0
        return torch.nan_to_num(out, nan=0.0, posinf=1.0, neginf=-1.0).clamp(-1.0, 1.0), valid
    # The generic planner may mark a diagonal pair as swing at the same time.
    # M1 must cross one foot at a time, however: choose exactly one member of
    # that planned swing set and hold the other three at their measured pose.
    # We alternate the selected member using the horizon phase so both legs in
    # each pair (and therefore all four legs over a crossing) are exercised.
    contact_state = reference.get("actual_contact_state", reference.get("contact_state"))
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
            phase_block = max(1, int(os.environ.get("M1_TEACHER_PHASE_BLOCK", "32")))
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
            if (
                os.environ.get("M1_TEACHER_SERIAL_FORCE", "0") == "1"
                and os.environ.get("M1_TEACHER_USE_PLANNER_CONTACT", "0") != "1"
            ):
                # Contact reports can change to the next diagonal pair while
                # the current foot is still in the air.  For the M1 crossing
                # contract, keep exactly one deterministic leg for the full
                # phase block, then hand off to the next leg.
                # Match the alternating obstacle tracks: FBL(+y), RAR(-y),
                # RBL(+y), FAR(-y).  The previous 0,3,1,2 order sent FAR
                # toward a +y block and left FBL as a support wheel in the
                # obstacle corridor.
                sequence_text = os.environ.get("M1_TEACHER_LEG_SEQUENCE", "0,3,2,1")
                try:
                    leg_sequence = [int(item.strip()) for item in sequence_text.split(",") if item.strip()]
                    leg_sequence = [item for item in leg_sequence if 0 <= item < 4] or [0, 3, 2, 1]
                except ValueError:
                    leg_sequence = [0, 3, 2, 1]
                sequence = torch.as_tensor(leg_sequence, device=target.device, dtype=torch.long)
                forced_leg = sequence.index_select(0, phase_slot.remainder(int(sequence.numel())))
                leg_override = reference.get("serial_leg_override")
                if leg_override is not None:
                    leg_override = torch.as_tensor(leg_override, device=target.device, dtype=torch.long).reshape(-1)
                    if int(leg_override.numel()) == int(target.shape[0]):
                        forced_leg = leg_override.clamp(0, 3)
                collision_leg_mask = reference.get("collision_leg_mask")
                if collision_leg_mask is not None:
                    collision_leg_mask = torch.as_tensor(collision_leg_mask, device=target.device, dtype=torch.bool)
                    if tuple(collision_leg_mask.shape) == (int(target.shape[0]), 4):
                        hit_any = collision_leg_mask.any(dim=1)
                        first_hit = collision_leg_mask.to(torch.long).argmax(dim=1)
                        # A wrapper-provided phase-stable override may have
                        # selected a threatened rear leg at the handoff. If
                        # it is absent, retain the legacy one-step collision
                        # fallback for compatibility with unit tests.
                        if leg_override is None:
                            forced_leg = torch.where(hit_any, first_hit, forced_leg)
                swing = torch.nn.functional.one_hot(
                    forced_leg, num_classes=4
                ).to(torch.bool)
            # Give the three support wheels a short settling window after a
            # handoff.  Without it, the next swing starts on the same frame
            # that the previous wheel reports touchdown, so body heave/roll
            # has no time to recover and later legs lose clearance.
            settle_steps = max(0, int(os.environ.get("M1_TEACHER_SETTLE_STEPS", "0")))
            if settle_steps > 0:
                local_phase = phase_index.remainder(phase_block)
                swing = swing & (local_phase >= settle_steps).unsqueeze(1)
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
            measured_stance_blend = min(
                max(float(os.environ.get("M1_TEACHER_MEASURED_STANCE_BLEND", "0.0")), 0.0),
                1.0,
            )
            if measured_stance_blend > 0.0:
                # A small correction toward the live support pose lets the
                # stance polygon follow body heave/roll without capturing a
                # fully lifted leg as the next phase's permanent target.
                stance_legs = stance_legs + measured_stance_blend * (
                    current_joint_pos[:, planner_cols] - stance_legs
                )
            support_blend = float(os.environ.get("M1_TEACHER_SUPPORT_BLEND", "0.0"))
            if support_blend > 0.0:
                support_blend = min(support_blend, 1.0)
                stance_legs = stance_legs + support_blend * (leg_target - stance_legs)
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
            os.environ.get("M1_TEACHER_MAX_HIP_LIFT_RAD", "0.40")
        )
        min_hip = torch.maximum(min_hip, hip_floor)
        min_knee = current_leg_pose[..., 2] + float(os.environ.get("M1_TEACHER_MIN_KNEE_LIFT_RAD", "0.80"))
        # The knee-lift floor is only for the rising/traverse portion.  Keeping
        # it active through touchdown ratchets the knee upward every frame and
        # leaves the wheel suspended at the end of the serial arc.
        phase_block_for_lift = max(1, int(os.environ.get("M1_TEACHER_PHASE_BLOCK", "32")))
        phase_index_for_lift = torch.as_tensor(
            reference.get("serial_phase_index", reference.get("phase_index", torch.zeros(target.shape[0], device=target.device))),
            device=target.device, dtype=target.dtype,
        ).reshape(-1)
        if int(phase_index_for_lift.numel()) == 1 and int(target.shape[0]) > 1:
            phase_index_for_lift = phase_index_for_lift.expand(int(target.shape[0]))
        from .m1_teacher_phase import m1_knee_lift_gate
        obstacle_hold_for_lift = reference.get("serial_obstacle_lift_hold")
        if obstacle_hold_for_lift is None:
            obstacle_hold_for_lift = torch.zeros_like(phase_index_for_lift, dtype=torch.bool)
        lift_gate = m1_knee_lift_gate(
            phase_index_for_lift,
            phase_block=phase_block_for_lift,
            obstacle_lift_hold=obstacle_hold_for_lift,
            end_fraction=float(os.environ.get("M1_TEACHER_KNEE_LIFT_END_FRACTION", "0.72")),
            clearance_complete=reference.get("serial_obstacle_clearance_complete"),
        )
        knee_extra = torch.zeros(
            (int(target.shape[0]), 4), device=target.device, dtype=target.dtype
        )
        try:
            knee_extra_values = [float(item.strip()) for item in os.environ.get(
                "M1_TEACHER_KNEE_EXTRA_RAD", "0.0,0.0,0.0,0.0"
            ).split(",")]
            if len(knee_extra_values) == 4:
                knee_extra = torch.as_tensor(
                    knee_extra_values, device=target.device, dtype=target.dtype
                ).clamp(0.0, 0.80).view(1, 4).expand(int(target.shape[0]), -1)
        except (TypeError, ValueError):
            pass
        min_knee = min_knee + knee_extra
        desired_leg_pose[..., 1] = torch.where(
            swing, torch.maximum(desired_leg_pose[..., 1], min_hip), desired_leg_pose[..., 1],
        )
        desired_leg_pose[..., 2] = torch.where(
            swing & lift_gate.unsqueeze(-1),
            torch.maximum(desired_leg_pose[..., 2], min_knee),
            desired_leg_pose[..., 2],
        )
        # The generic planner's lateral/leg-frame angles are not safe as
        # direct M1 commands.  Bound only the selected swing leg around the
        # standing pose; the knee keeps enough extension for a 10 cm obstacle
        # while ABAD and hip cannot roll the floating base sideways.
        nominal_pose = nominal_legs.reshape(-1, 4, 3)
        abad_span = float(os.environ.get("M1_TEACHER_MAX_ABAD_RAD", "0.10"))
        hip_span = float(os.environ.get("M1_TEACHER_MAX_HIP_LIFT_RAD", "0.40"))
        knee_span = float(os.environ.get("M1_TEACHER_MAX_KNEE_LIFT_RAD", "2.20"))
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
        # A high single-leg lift unloads the body toward the swing side.  A
        # small extension of the diagonally opposite support leg keeps the
        # support polygon engaged without turning it into a second swing.
        support_comp = float(os.environ.get("M1_TEACHER_SUPPORT_KNEE_COMP_RAD", "0.0"))
        stance_raise = float(os.environ.get("M1_TEACHER_STANCE_KNEE_RAISE_RAD", "0.0"))
        if stance_raise:
            stance_knee = nominal_pose[..., 2] + stance_raise
            desired_leg_pose[..., 2] = torch.where(
                ~swing,
                stance_knee,
                desired_leg_pose[..., 2],
            )
        if support_comp:
            opposite = torch.flip(swing, dims=(1,))
            support_knee = nominal_pose[..., 2] + support_comp
            desired_leg_pose[..., 2] = torch.where(
                opposite & ~swing,
                support_knee,
                desired_leg_pose[..., 2],
            )
        desired_legs = desired_leg_pose.reshape(-1, len(M1_PLANNER_JOINT_NAMES))
        # The generic MPC joint target is not a reliable swing trajectory for
        # M1: it can flex the knee without moving the wheel over the obstacle.
        # When the wrapper provides the live root pose, generate a bounded
        # Cartesian foot arc and solve it with the native M1 IK.  The foot
        # starts at the held stance, lifts before advancing, and returns to
        # the ground at the end of the serial phase.  This keeps the other
        # three feet fixed and makes the teacher's action physically match
        # the crossing contract instead of rewarding a scrape.
        root_pos = reference.get("m1_root_pos_w")
        root_rpy = reference.get("m1_root_rpy_w")
        if (
            root_pos is not None
            and root_rpy is not None
            and os.environ.get("M1_TEACHER_FOOT_TRAJECTORY", "1") == "1"
            and os.environ.get("M1_TEACHER_USE_GENERIC_MPC", "0") != "1"
        ):
            root_pos = torch.as_tensor(root_pos, device=target.device, dtype=target.dtype)
            root_rpy = torch.as_tensor(root_rpy, device=target.device, dtype=target.dtype)
            if tuple(root_pos.shape) == (int(target.shape[0]), 3) and tuple(root_rpy.shape) == tuple(root_pos.shape):
                hold_fk = m1_fk(root_pos, root_rpy, stance_legs)
                planner_foot = reference.get("foot_pos_w")
                planner_foot_root = reference.get("foot_pos_root")
                planner_touchdown = reference.get("planned_touchdown_w")
                use_planner_foot = (
                    os.environ.get("M1_TEACHER_USE_PLANNER_FOOT_TARGET", "1") == "1"
                    and planner_foot is not None
                    and tuple(torch.as_tensor(planner_foot).shape) == (int(target.shape[0]), 4, 3)
                )
                if use_planner_foot:
                    # The trajectory manager already solves a terrain-aware
                    # lift/traverse/touchdown path. Preserve its world-frame
                    # target instead of replacing it with a timer-only arc.
                    if planner_foot_root is not None and tuple(torch.as_tensor(planner_foot_root).shape) == (int(target.shape[0]), 4, 3):
                        # Convert the planner's local future target using the
                        # measured current body pose.  Applying future world
                        # coordinates directly to current IK was the source
                        # of the large root tilt seen in the first experiment.
                        local_target = torch.as_tensor(planner_foot_root, device=target.device, dtype=target.dtype)
                        current_rot = rpy_to_rotation_matrix(root_rpy)
                        foot_target = root_pos[:, None, :] + torch.einsum("bij,bkj->bki", current_rot, local_target)
                    else:
                        foot_target = torch.as_tensor(planner_foot, device=target.device, dtype=target.dtype).clone()
                else:
                    held_foot = reference.get("hold_foot_pos_w")
                    if held_foot is not None and tuple(torch.as_tensor(held_foot).shape) == (int(target.shape[0]), 4, 3):
                        # Keep the stance/swing anchor fixed for this serial
                        # phase.  Using the current-root FK here lets body
                        # heave drag the target downward frame by frame.
                        foot_target = torch.as_tensor(
                            held_foot, device=target.device, dtype=target.dtype
                        ).clone()
                    else:
                        foot_target = hold_fk.foot_pos_w.clone()
                # Correct the small roll/pitch tilt that appears when one
                # wheel is unloaded.  Reproject the current support-wheel
                # locations through a horizontalized body rotation instead of
                # using nominal foot targets.  The latter can cross an M1 IK
                # branch and turn a tiny correction into a large roll.
                upright_support = os.environ.get("M1_TEACHER_UPRIGHT_SUPPORT", "0").strip().lower() not in {"0", "false", "no"}
                if upright_support and swing is not None:
                    upright_rpy = root_rpy.clone()
                    upright_rpy[:, :2] = 0.0
                    current_rot = rpy_to_rotation_matrix(root_rpy)
                    upright_rot = rpy_to_rotation_matrix(upright_rpy)
                    relative_foot = foot_target - root_pos[:, None, :]
                    relative_body = torch.einsum(
                        "bij,bkj->bki", current_rot.transpose(1, 2), relative_foot
                    )
                    upright_foot = root_pos[:, None, :] + torch.einsum(
                        "bij,bkj->bki", upright_rot, relative_body
                    )
                    upright_support_blend = min(max(float(os.environ.get("M1_TEACHER_UPRIGHT_SUPPORT_BLEND", "0.35")), 0.0), 1.0)
                    # Do not perturb the support polygon for the first few
                    # frames of a normal swing.  Engage the correction only
                    # after a measured roll/pitch threshold, with a smooth
                    # bounded gain; this avoids turning a harmless lean into
                    # a secondary knee contact.
                    tilt_threshold = max(0.0, float(os.environ.get("M1_TEACHER_UPRIGHT_SUPPORT_TILT_THRESHOLD_RAD", "0.0")))
                    tilt_ramp = max(1e-3, float(os.environ.get("M1_TEACHER_UPRIGHT_SUPPORT_TILT_RAMP_RAD", "0.12")))
                    tilt_mag = torch.linalg.vector_norm(root_rpy[:, :2], dim=-1)
                    tilt_gain = ((tilt_mag - tilt_threshold) / tilt_ramp).clamp(0.0, 1.0)
                    upright_support_blend_tensor = upright_support_blend * tilt_gain
                    max_shift = float(os.environ.get("M1_TEACHER_UPRIGHT_SUPPORT_MAX_SHIFT_M", "0.025"))
                    # Correct only the horizontal support polygon. Rotating
                    # the support targets in full 3-D also changes their
                    # world-z, briefly unloads a second wheel, and is the
                    # source of the visible roll/rocking seen during handoff.
                    # Preserve each held wheel's height so PhysX keeps the
                    # same three-wheel support while the selected wheel is up.
                    upright_xy_delta = (upright_foot[..., :2] - foot_target[..., :2]).clamp(
                        -max_shift, max_shift
                    )
                    upright_target = foot_target.clone()
                    z_only = os.environ.get("M1_TEACHER_UPRIGHT_SUPPORT_Z_ONLY", "0").strip().lower() not in {"0", "false", "no"}
                    if z_only:
                        # Keep the support polygon fixed in XY.  A lateral
                        # reprojection can push a knee/hip into the floor or
                        # obstacle while trying to correct a small roll.  In
                        # this mode only apply a bounded vertical correction
                        # predicted by the horizontalized body frame.
                        max_z_shift = float(os.environ.get("M1_TEACHER_UPRIGHT_SUPPORT_MAX_Z_SHIFT_M", "0.008"))
                        upright_z_delta = (upright_foot[..., 2] - foot_target[..., 2]).clamp(
                            -max_z_shift, max_z_shift
                        )
                        upright_target[..., 2] = foot_target[..., 2] + upright_support_blend_tensor.unsqueeze(-1) * upright_z_delta
                    else:
                        upright_target[..., :2] = foot_target[..., :2] + upright_support_blend_tensor.unsqueeze(-1) * upright_xy_delta
                        upright_target[..., 2] = foot_target[..., 2]
                    upright_mask = ~swing
                    if os.environ.get("M1_TEACHER_UPRIGHT_SUPPORT_ONLY_OPPOSITE", "0").strip().lower() not in {"0", "false", "no"}:
                        # The diagonal/opposite support wheel carries most of
                        # the roll moment when one M1 wheel is unloaded. Move
                        # only that stance target; perturbing all three
                        # stance legs can create secondary hip/knee contacts.
                        upright_mask = torch.flip(swing, dims=(1,))
                    foot_target = torch.where(
                        upright_mask.unsqueeze(-1), upright_target, foot_target
                    )
                from .m1_teacher_phase import (
                    m1_apply_obstacle_lift_floor,
                    m1_obstacle_crossing_phase_progress,
                )
                obstacle_lift_hold = reference.get("serial_obstacle_lift_hold")
                if obstacle_lift_hold is None:
                    obstacle_lift_hold = torch.zeros(
                        int(target.shape[0]), device=target.device, dtype=torch.bool
                    )
                else:
                    obstacle_lift_hold = torch.as_tensor(
                        obstacle_lift_hold, device=target.device, dtype=torch.bool
                    ).reshape(-1)
                clearance_complete = reference.get("serial_obstacle_clearance_complete")
                if clearance_complete is None:
                    clearance_complete = torch.zeros(
                        int(target.shape[0]), device=target.device, dtype=torch.bool
                    )
                else:
                    clearance_complete = torch.as_tensor(
                        clearance_complete, device=target.device, dtype=torch.bool
                    ).reshape(-1)
                if tuple(clearance_complete.shape) != (int(target.shape[0]),):
                    raise ValueError("serial obstacle clearance flag must match batch size")
                phase_progress = m1_obstacle_crossing_phase_progress(
                    phase_index, obstacle_lift_hold, phase_block=phase_block,
                    clearance_complete=clearance_complete,
                ).to(target.dtype)
                settle = float(max(0, int(os.environ.get("M1_TEACHER_SETTLE_STEPS", "0"))))
                active_span = float(max(1, phase_block - int(settle)))
                if settle > 0.0:
                    local_phase = phase_index.remainder(phase_block).to(target.dtype)
                    phase_progress = torch.where(
                        obstacle_lift_hold,
                        phase_progress,
                        ((local_phase - settle).clamp_min(0.0) + 1.0) / active_span,
                    ).clamp(0.0, 1.0)
                phase_progress = torch.where(
                    clearance_complete, torch.ones_like(phase_progress), phase_progress
                )
                # Smooth lift/advance/touchdown arc.  The forward offset is
                # intentionally modest so the robot does not overreach a
                # nearby block while still clearing its leading edge.
                if not use_planner_foot:
                    lift_amplitude = float(os.environ.get("M1_TEACHER_FOOT_LIFT_M", "0.25"))
                    # Four M1 linkages realize different world-z lift for the
                    # same Cartesian request. Keep the default symmetric, but
                    # allow bounded per-leg calibration without globally
                    # increasing lift and destabilizing the other legs.
                    lift_scale = torch.ones(
                        (int(target.shape[0]), 4), device=target.device, dtype=target.dtype
                    )
                    try:
                        scale_values = [float(item.strip()) for item in os.environ.get(
                            "M1_TEACHER_FOOT_LIFT_SCALE", "1,1,1,1"
                        ).split(",")]
                        if len(scale_values) == 4:
                            lift_scale = torch.as_tensor(
                                scale_values, device=target.device, dtype=target.dtype
                            ).clamp(0.5, 2.0).view(1, 4).expand(int(target.shape[0]), -1)
                    except (TypeError, ValueError):
                        pass
                    # Per-leg Cartesian clearance trim.  M1's four wheel
                    # linkages do not realize exactly the same bottom height
                    # under an identical lift request; a small bounded trim
                    # lets calibration correct the consistently low FAR
                    # wheel without raising the other three support wheels.
                    lift_bias = torch.zeros(
                        (int(target.shape[0]), 4), device=target.device, dtype=target.dtype
                    )
                    try:
                        bias_values = [float(item.strip()) for item in os.environ.get(
                            "M1_TEACHER_FOOT_LIFT_BIAS_M", "0,0,0,0"
                        ).split(",")]
                        if len(bias_values) == 4:
                            lift_bias = torch.as_tensor(
                                bias_values, device=target.device, dtype=target.dtype
                            ).clamp(-0.03, 0.03).view(1, 4).expand(int(target.shape[0]), -1)
                    except (TypeError, ValueError):
                        pass
                    advance_distance = float(os.environ.get("M1_TEACHER_FOOT_ADVANCE_M", "0.22"))
                    if os.environ.get("M1_TEACHER_PRELIFT", "0") == "1":
                        pre = (phase_progress / 0.30).clamp(0.0, 1.0)
                        pre = pre * pre * (3.0 - 2.0 * pre)
                        post = ((1.0 - phase_progress) / 0.30).clamp(0.0, 1.0)
                        post = post * post * (3.0 - 2.0 * post)
                        lift = torch.minimum(pre, post) * lift_amplitude
                        # Experimental target sequencing, not a physical
                        # crossing gate. Seed-2 smoke increased collisions
                        # (18 -> 21); keep disabled in production.
                        travel_end = 0.70 if os.environ.get("M1_TEACHER_EARLY_TRAVERSE", "0") == "1" else 1.0
                        travel = ((phase_progress - 0.30) / (travel_end - 0.30)).clamp(0.0, 1.0)
                        travel = travel * travel * (3.0 - 2.0 * travel)
                        advance = travel * advance_distance
                    else:
                        lift = torch.sin(torch.pi * phase_progress).clamp_min(0.0) * lift_amplitude
                        advance = phase_progress.clamp(0.0, 1.0) * advance_distance
                    lift = m1_apply_obstacle_lift_floor(
                        lift,
                        obstacle_lift_hold,
                        lift_amplitude_m=lift_amplitude,
                        hold_fraction=float(os.environ.get(
                            "M1_TEACHER_OBSTACLE_HOLD_LIFT_FRACTION", "0.78"
                        )),
                    )
                    # Keep the knee behind the leading edge while the leg is
                    # rising, then traverse forward only after the wheel has
                    # cleared the obstacle top.  This optional backstep is
                    # zero by default for compatibility, but is useful for
                    # the M1's long knee link where a straight foot arc can
                    # hit the front face even though the wheel is already
                    # above it.
                    backstep_distance = float(os.environ.get("M1_TEACHER_FOOT_BACKSTEP_M", "0.0"))
                    early_backstep = ((0.45 - phase_progress) / 0.45).clamp(0.0, 1.0) * backstep_distance
                    advance = advance - early_backstep
                    # Advance in the measured body-heading direction, not a
                    # hard-coded world +X axis.  The scanner/MPC reference
                    # is world-frame, so using +X after a yaw or reset
                    # rotation sends the foot sideways relative to the
                    # obstacle and invalidates the touchdown plan.
                    heading_xy = torch.stack((root_rpy[:, 2].cos(), root_rpy[:, 2].sin()), dim=-1)
                    foot_target[..., :2] = foot_target[..., :2] + (
                        advance.unsqueeze(-1).unsqueeze(-1)
                        * heading_xy[:, None, :]
                        * swing.unsqueeze(-1).to(target.dtype)
                    )
                    arc = torch.sin(torch.pi * phase_progress).clamp_min(0.0)
                    clearance = lift.unsqueeze(-1) * lift_scale + arc.unsqueeze(-1) * lift_bias
                    foot_target[..., 2] = foot_target[..., 2] + clearance * swing.to(target.dtype)
                    if (
                        os.environ.get("M1_TEACHER_USE_PLANNER_TOUCHDOWN", "0") == "1"
                        and planner_touchdown is not None
                        and tuple(torch.as_tensor(planner_touchdown).shape) == (int(target.shape[0]), 4, 3)
                    ):
                        touchdown_xy = torch.as_tensor(planner_touchdown, device=target.device, dtype=target.dtype)[..., :2]
                        current_xy = hold_fk.foot_pos_w[..., :2]
                        max_delta_xy = float(os.environ.get("M1_TEACHER_MAX_TOUCHDOWN_DELTA_M", "0.28"))
                        delta_xy = (touchdown_xy - current_xy).clamp(-max_delta_xy, max_delta_xy)
                        foot_target[..., :2] = current_xy + phase_progress.unsqueeze(-1) * delta_xy
                else:
                    # Keep MPC's horizontal traverse and touchdown, but
                    # enforce the M1 strict top-clearance contract on the
                    # selected wheel.  The planner target can be terrain-safe
                    # yet remain too close to the authored obstacle top for a
                    # 5 cm visual/physical margin.
                    planner_lift_amplitude = float(os.environ.get(
                        "M1_TEACHER_FOOT_LIFT_M", "0.18"
                    ))
                    lift = torch.sin(torch.pi * phase_progress).clamp_min(0.0) * planner_lift_amplitude
                    lift = m1_apply_obstacle_lift_floor(
                        lift,
                        obstacle_lift_hold,
                        lift_amplitude_m=planner_lift_amplitude,
                        hold_fraction=float(os.environ.get(
                            "M1_TEACHER_OBSTACLE_HOLD_LIFT_FRACTION", "0.78"
                        )),
                    )
                    # M1's four linkages do not produce the same wheel
                    # height for one Cartesian lift.  Calibrate the planner
                    # clearance per leg instead of globally increasing lift
                    # and rolling the support polygon.
                    planner_lift_scale = torch.ones(
                        (int(target.shape[0]), 4), device=target.device, dtype=target.dtype
                    )
                    try:
                        scale_values = [float(item.strip()) for item in os.environ.get(
                            "M1_TEACHER_PLANNER_LIFT_SCALE", "1.0,1.0,1.0,1.0"
                        ).split(",")]
                        if len(scale_values) == 4:
                            planner_lift_scale = torch.as_tensor(
                                scale_values, device=target.device, dtype=target.dtype
                            ).clamp(0.75, 2.25).view(1, 4).expand(int(target.shape[0]), -1)
                    except (TypeError, ValueError):
                        pass
                    lift_per_leg = lift.unsqueeze(-1) * planner_lift_scale
                    clearance_target_z = hold_fk.foot_pos_w[..., 2] + lift_per_leg
                    foot_target[..., 2] = torch.where(
                        swing,
                        torch.maximum(foot_target[..., 2], clearance_target_z),
                        foot_target[..., 2],
                    )
                # Once measured wheel clearance and far-edge passage are both
                # latched, stop holding the wheel at lift height and descend
                # vertically over its already-safe measured landing point.
                # The strict event still owns this single leg until loaded
                # touchdown; this only releases the clearance lift.
                if current_joint_pos is not None and swing is not None:
                    current_fk = m1_fk(
                        root_pos, root_rpy, current_joint_pos[:, planner_cols]
                    )
                    touchdown_mask = swing & clearance_complete.unsqueeze(-1)
                    foot_target[..., :2] = torch.where(
                        touchdown_mask.unsqueeze(-1),
                        current_fk.foot_pos_w[..., :2],
                        foot_target[..., :2],
                    )
                # Optional Cartesian support preload.  When the floating
                # base heaves below its reset height, press only the three
                # stance targets slightly downward before IK.  This is more
                # symmetric than a fixed knee-angle bias and keeps the M1
                # support polygon engaged while one wheel swings.
                support_press = float(os.environ.get("M1_TEACHER_SUPPORT_FOOT_PRESS_M", "0.0"))
                if support_press > 0.0:
                    target_root_z = float(os.environ.get("M1_TEACHER_SUPPORT_ROOT_Z_M", "0.52"))
                    deficit = (target_root_z - root_pos[:, 2]).clamp_min(0.0)
                    press = torch.minimum(deficit, torch.as_tensor(support_press, device=target.device, dtype=target.dtype))
                    foot_target[..., 2] = foot_target[..., 2] - press.unsqueeze(-1) * (~swing).to(target.dtype)
                held_foot = reference.get("hold_foot_pos_w")
                if held_foot is not None:
                    # Wheel-legged crossing: the chassis transports the
                    # raised wheel. Do not add a walking-foot forward arc or
                    # backstep. Keep heading-relative XY and absolute Z.
                    anchor = torch.as_tensor(held_foot, device=target.device, dtype=target.dtype)
                    anchor_root = torch.as_tensor(reference.get("hold_root_pos_w", root_pos), device=target.device, dtype=target.dtype)
                    anchor_rpy = torch.as_tensor(reference.get("hold_root_rpy_w", root_rpy), device=target.device, dtype=target.dtype)
                    yaw_delta = root_rpy[:, 2] - anchor_rpy[:, 2]
                    c, s = yaw_delta.cos()[:, None], yaw_delta.sin()[:, None]
                    relative = anchor[..., :2] - anchor_root[:, None, :2]
                    carried_xy = torch.stack((c * relative[..., 0] - s * relative[..., 1],
                                              s * relative[..., 0] + c * relative[..., 1]), dim=-1)
                    carried_xy = carried_xy + root_pos[:, None, :2]
                    foot_target[..., :2] = torch.where(swing.unsqueeze(-1), carried_xy, foot_target[..., :2])
                    event_height = reference.get("serial_wheel_target_z_w")
                    if event_height is not None:
                        event_height = torch.as_tensor(event_height, device=target.device, dtype=target.dtype).reshape(-1, 1)
                        foot_target[..., 2] = torch.where(
                            swing & obstacle_lift_hold[:, None], event_height, foot_target[..., 2])
                    foot_target[..., 2] = torch.where(
                        swing & clearance_complete[:, None], anchor[..., 2], foot_target[..., 2])
                ik_legs, ik_valid = m1_ik(root_pos, root_rpy, foot_target)
                # Keep the solved Cartesian objective through the actuator
                # boundary. A knee floor applied here changes the wheel's XY
                # and height without updating the IK validity certificate.
                cartesian_foot_target = foot_target
                ik_finite = torch.isfinite(ik_legs).all(dim=-1)
                ik_valid = ik_valid & ik_finite
                # A transient body heave/roll can put the Cartesian target just
                # outside the analytic workspace. Returning an all-zero action
                # in that frame drops the selected support and causes the tip
                # seen in PhysX. Use the nearest finite, joint-limit-clamped
                # pose for the selected swing leg; NaN/nonfinite states still
                # fail closed and remain invalid.
                ik_fallback = os.environ.get("M1_TEACHER_IK_FALLBACK", "0").strip().lower() not in {"0", "false", "no"}
                if ik_fallback:
                    lower_ik = lower.reshape(1, 4, 3)
                    upper_ik = upper.reshape(1, 4, 3)
                    ik_safe = torch.nan_to_num(ik_legs, nan=0.0, posinf=0.0, neginf=0.0).clamp(lower_ik, upper_ik)
                    ik_legs = torch.where(ik_finite.unsqueeze(-1), ik_legs, ik_safe)
                reproject_stance = os.environ.get("M1_TEACHER_REPROJECT_STANCE", "0").strip().lower() not in {"0", "false", "no"}
                if reproject_stance or upright_support:
                    # Re-solve all legs against the held world foot targets.
                    # The swing leg still follows the serial arc above, while
                    # measured-contact stance legs maintain their support point
                    # as the body rolls forward instead of stretching old joint
                    # angles until the base tips.
                    desired_leg_pose = torch.where(
                        ik_valid.unsqueeze(-1), ik_legs, desired_leg_pose
                    )
                else:
                    desired_leg_pose = torch.where(
                        (swing & ik_valid).unsqueeze(-1), ik_legs, desired_leg_pose
                    )
                # A finite fallback can preserve an output for stabilization,
                # but it must never certify an unreachable reference as a
                # valid imitation/control target.
                swing_ik_ok = ik_valid
                valid = valid & ((~swing) | swing_ik_ok).all(dim=-1)
                desired_legs = desired_leg_pose.reshape(-1, len(M1_PLANNER_JOINT_NAMES))
    # The Cartesian swing branch can replace ``desired_leg_pose`` after the
    # earlier support-compensation block. Re-apply the single opposite-leg
    # support target here, immediately before the final measured-stance hold,
    # so it cannot be discarded by the stance overwrite below.
    if swing is not None and current_joint_pos is not None:
        support_comp = float(os.environ.get("M1_TEACHER_SUPPORT_KNEE_COMP_RAD", "0.0"))
        stance_raise = float(os.environ.get("M1_TEACHER_STANCE_KNEE_RAISE_RAD", "0.0"))
        if support_comp:
            stance_pose = stance_legs.reshape(-1, 4, 3).clone()
            nominal_pose = default_legs.reshape(-1, 4, 3)
            opposite = torch.flip(swing, dims=(1,))
            stance_pose[..., 2] = torch.where(
                opposite & ~swing,
                nominal_pose[..., 2] + support_comp,
                stance_pose[..., 2],
            )
            stance_legs = stance_pose.reshape(-1, len(M1_PLANNER_JOINT_NAMES))
        if stance_raise:
            # The Cartesian swing branch above rebuilds desired_legs from
            # measured held poses. Re-apply the all-support knee raise here,
            # otherwise the earlier stance_raise is silently discarded at
            # the final single-leg hold boundary.
            stance_pose = stance_legs.reshape(-1, 4, 3).clone()
            nominal_pose = default_legs.reshape(-1, 4, 3)
            stance_pose[..., 2] = torch.where(
                ~swing,
                nominal_pose[..., 2] + stance_raise,
                stance_pose[..., 2],
            )
            stance_legs = stance_pose.reshape(-1, len(M1_PLANNER_JOINT_NAMES))

    max_delta = float(os.environ.get("M1_TEACHER_MAX_DELTA_RAD", "1.10"))
    requested_legs = desired_legs
    desired_legs = default_legs + (requested_legs - default_legs).clamp(-max_delta, max_delta)
    if swing is not None:
        # The global delta cap was silently clipping the selected knee at
        # nominal + 1.10 rad (2.20 rad for the M1 default pose), even though
        # the asset's physical knee limit permits 2.801 rad.  This caused the
        # FAR wheel to top out below the strict obstacle-clearance threshold.
        # Give only the active swing knee its requested, joint-limit-clamped
        # target; retain the existing delta and posture bounds for every
        # support joint and for swing hip/ABAD.
        requested_leg = requested_legs.reshape(-1, 4, 3)
        bounded_leg = desired_legs.reshape(-1, 4, 3)
        lower_knee = lower.reshape(1, 4, 3)[..., 2]
        upper_knee = upper.reshape(1, 4, 3)[..., 2]
        safe_knee = torch.maximum(
            torch.minimum(requested_leg[..., 2], upper_knee), lower_knee
        )
        bounded_leg[..., 2] = torch.where(swing, safe_knee, bounded_leg[..., 2])
        desired_legs = bounded_leg.reshape_as(desired_legs)
    if current_joint_pos is not None:
        current_legs = current_joint_pos[:, planner_cols]
        slew = float(os.environ.get("M1_TEACHER_SLEW_RAD", "0.28"))
        slewed_legs = current_legs + (desired_legs - current_legs).clamp(-slew, slew)
        if swing is not None:
            # Preserve measured stance targets so the position-action decoder
            # does not reinterpret zero as a reset-to-default command. When
            # Cartesian stance reprojection is enabled, keep its IK solution
            # for the three support legs; replacing it with stale stance_legs
            # here lets the body collapse during a swing.
            reproject_stance = os.environ.get("M1_TEACHER_REPROJECT_STANCE", "0").strip().lower() not in {"0", "false", "no"}
            upright_support = os.environ.get("M1_TEACHER_UPRIGHT_SUPPORT", "0").strip().lower() not in {"0", "false", "no"}
            support_targets = desired_legs if (reproject_stance or upright_support) else stance_legs
            desired_legs = torch.where(
                swing.unsqueeze(-1),
                slewed_legs.reshape(-1, 4, 3),
                support_targets.reshape(-1, 4, 3),
            ).reshape(-1, len(M1_PLANNER_JOINT_NAMES))
        else:
            desired_legs = slewed_legs
    if cartesian_foot_target is not None and swing is not None:
        current_legs = (current_joint_pos[:, planner_cols]
                        if current_joint_pos is not None else default_legs)
        # Include *all* later clamps in the solve. In particular, normalized
        # actions must not clip a correct IK solution after it is certified.
        allowed_delta = torch.full_like(default_legs, min(max_delta, M1_LEG_ACTION_SCALE_RAD))
        allowed_delta = allowed_delta.reshape(-1, 4, 3)
        allowed_delta[..., 2] = torch.where(
            swing, M1_LEG_ACTION_SCALE_RAD, allowed_delta[..., 2])
        nominal = default_legs.reshape(-1, 4, 3)
        step_lower = torch.maximum(lower.reshape(1, 4, 3), nominal - allowed_delta)
        step_upper = torch.minimum(upper.reshape(1, 4, 3), nominal + allowed_delta)
        step_q, endpoint_valid = cartesian_joint_step(
            root_pos, root_rpy, current_legs, cartesian_foot_target,
            step_lower, step_upper, float(os.environ.get("M1_TEACHER_SLEW_RAD", "0.28")),
        )
        desired_legs = torch.where(
            swing.unsqueeze(-1), step_q, desired_legs.reshape(-1, 4, 3)
        ).reshape_as(desired_legs)
        valid = valid & ((~swing) | endpoint_valid).all(-1)
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
    invalid_hold_current = (
        current_joint_pos is not None
        and os.environ.get("M1_TEACHER_INVALID_HOLD_CURRENT", "1").strip().lower()
        not in {"0", "false", "no"}
    )
    if invalid_hold_current and (~valid).any():
        # Zero is decoded as the nominal pose by M1's position-action
        # adapter.  On a transient planner/tilt invalid frame that snaps all
        # three support wheels away from their load-bearing pose and causes a
        # fall.  Hold the measured joint configuration instead; wheels stay
        # stopped and the next valid teacher frame can resume the arc.
        hold_action = torch.zeros_like(out)
        hold_action[:, planner_cols] = (
            (current_joint_pos[:, planner_cols] - default_legs)
            / M1_LEG_ACTION_SCALE_RAD
        ).clamp(-1.0, 1.0)
        out = torch.where(valid.unsqueeze(-1), out, hold_action)
    else:
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
    crossing_active: torch.Tensor | None = None,
    crossing_max_tilt_rad: float | None = None,
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
    tilt_safe = torch.isfinite(tilt) & (tilt <= float(max_tilt_rad))
    valid = valid.to(dtype=torch.bool)
    if crossing_active is None:
        crossing_active = torch.zeros_like(valid)
    else:
        crossing_active = torch.as_tensor(
            crossing_active, device=action.device, dtype=torch.bool
        ).reshape(-1)
        if crossing_active.shape != valid.shape:
            raise ValueError("crossing_active must match the action batch")
    if crossing_max_tilt_rad is None:
        crossing_max_tilt_rad = float(os.environ.get(
            "M1_TEACHER_CROSSING_MAX_TILT_RAD", "0.45"
        ))
    finite_action = torch.isfinite(action).all(dim=-1)
    # During a single-leg obstacle event, handing the leg back to PPO at the
    # ordinary 0.30-rad recovery threshold drops it before it reaches the far
    # edge. Continue the finite swing/hold and reduced support-wheel command
    # through a bounded crossing-only envelope; above that bound fail closed.
    crossing_safe = (
        crossing_active
        & torch.isfinite(tilt)
        & (tilt <= float(crossing_max_tilt_rad))
        & finite_action
    )
    safe = (valid & tilt_safe) | crossing_safe
    # reference_to_m1_action deliberately emits the measured joint hold pose
    # on a transient planner-invalid frame. Do not erase that hold here: a
    # zero action decodes as the nominal M1 pose and unloads all three
    # support wheels during a handoff. Planner validity remains false unless
    # the explicitly bounded crossing-active path below retains the command.
    hold_invalid = os.environ.get("M1_TEACHER_INVALID_HOLD_CURRENT", "1").strip().lower() not in {"0", "false", "no"}
    # A transient planner-invalid frame should keep the measured-pose hold
    # while the body recovers from a small swing-induced tilt.  The old gate
    # zeroed that hold at 0.30 rad, which unloaded the support polygon and
    # amplified the tilt.  Recovery remains opt-in and bounded; valid planner
    # frames still obey the strict safety limit.
    recovery_hold = os.environ.get("M1_TEACHER_RECOVERY_HOLD", "0").strip().lower() not in {"0", "false", "no"}
    recovery_tilt = float(os.environ.get("M1_TEACHER_RECOVERY_TILT_RAD", str(max(0.45, 2.0 * float(max_tilt_rad)))))
    recovery_safe = torch.isfinite(tilt) & (tilt <= recovery_tilt)
    apply_mask = (
        (valid & tilt_safe)
        | crossing_safe
        | ((~valid) & hold_invalid & finite_action & (tilt_safe | (recovery_hold & recovery_safe)))
    )
    safe_action = torch.where(apply_mask.unsqueeze(-1), action, torch.zeros_like(action))
    return safe_action, safe


__all__ = ["apply_m1_teacher_safety", "reference_to_m1_action"]
