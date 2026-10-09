"""Pure phase helpers for single-wheel obstacle crossing."""
import torch


def serial_crossing_wheel_actions(*, forward_speed, selected_leg, crossing_active,
                                  phase_progress, obstacle_lift_hold=None,
                                  touchdown_pending=None,
                                  support_scale=0.50,
                                  swing_scale=0.15):
    """Keep the three support wheels rolling while one wheel is airborne.

    ``support_scale`` deliberately remains nonzero during the crossing hold;
    scaling all four wheels to the swing-wheel value stalls the base before a
    rear wheel can pass the obstacle.  Outside a serial crossing, restore the
    commanded speed on all four wheels.
    """
    forward_speed = torch.as_tensor(forward_speed)
    if forward_speed.ndim == 0:
        forward_speed = forward_speed.reshape(1)
    device, dtype = forward_speed.device, forward_speed.dtype
    batch = int(forward_speed.shape[0])
    selected_leg = torch.as_tensor(selected_leg, device=device, dtype=torch.long).reshape(-1)
    crossing_active = torch.as_tensor(crossing_active, device=device, dtype=torch.bool).reshape(-1)
    phase_progress = torch.as_tensor(phase_progress, device=device, dtype=dtype).reshape(-1)
    if obstacle_lift_hold is None:
        obstacle_lift_hold = torch.zeros(batch, device=device, dtype=torch.bool)
    else:
        obstacle_lift_hold = torch.as_tensor(
            obstacle_lift_hold, device=device, dtype=torch.bool
        ).reshape(-1)
    if touchdown_pending is None:
        touchdown_pending = torch.zeros(batch, device=device, dtype=torch.bool)
    else:
        touchdown_pending = torch.as_tensor(
            touchdown_pending, device=device, dtype=torch.bool
        ).reshape(-1)
    for name, value in (("selected_leg", selected_leg), ("crossing_active", crossing_active),
                        ("phase_progress", phase_progress),
                        ("obstacle_lift_hold", obstacle_lift_hold),
                        ("touchdown_pending", touchdown_pending)):
        if int(value.numel()) == 1 and batch > 1:
            value = value.expand(batch)
        if int(value.numel()) != batch:
            raise ValueError(f"{name} must contain one value per environment")
        if name == "selected_leg":
            selected_leg = value
        elif name == "crossing_active":
            crossing_active = value
        elif name == "phase_progress":
            phase_progress = value
        elif name == "obstacle_lift_hold":
            obstacle_lift_hold = value
        else:
            touchdown_pending = value
    if torch.any((selected_leg < 0) | (selected_leg > 3)):
        raise ValueError("selected_leg must be in [0, 3]")
    support_scale = min(max(float(support_scale), 0.0), 1.0)
    swing_scale = min(max(float(swing_scale), 0.0), 1.0)
    # A fixed phase threshold must not restore full speed while the measured
    # obstacle event still requires the selected wheel to stay lifted.
    crossing_window = crossing_active & (
        (phase_progress < 0.75) | obstacle_lift_hold | touchdown_pending
    )
    scales = torch.ones((batch, 4), device=device, dtype=dtype)
    scales = torch.where(crossing_window[:, None],
                         torch.full_like(scales, support_scale), scales)
    swing_mask = torch.zeros((batch, 4), device=device, dtype=torch.bool)
    swing_mask.scatter_(1, selected_leg[:, None], True)
    scales = torch.where(crossing_window[:, None] & swing_mask,
                         torch.full_like(scales, swing_scale), scales)
    return forward_speed[:, None] * scales


def gate_probe_invalid_wheel_actions(action, *, valid, teacher_active, wheel_cols):
    """Mirror runtime gating: invalid active-teacher rows still carry wheel drive."""
    action = torch.as_tensor(action).clone()
    valid = torch.as_tensor(valid, device=action.device, dtype=torch.bool).reshape(-1)
    teacher_active = torch.as_tensor(teacher_active, device=action.device, dtype=torch.bool).reshape(-1)
    if valid.numel() != action.shape[0] or teacher_active.numel() != action.shape[0]:
        raise ValueError("valid and teacher_active must match action batch size")
    inactive_invalid = ~valid & ~teacher_active
    if inactive_invalid.any():
        wheel_mask = torch.zeros(action.shape[1], device=action.device, dtype=torch.bool)
        wheel_mask[list(wheel_cols)] = True
        action[inactive_invalid[:, None] & wheel_mask[None, :]] = 0.0
    return action


def preserve_invalid_obstacle_leg_action(
    action, *, valid, teacher_active, obstacle_hold, selected_leg,
    selected_phase, last_leg_action, last_leg, last_phase, leg_cols,
):
    """Hold the last valid leg target through a transient invalid MPC frame.

    During a measured obstacle hold, a missing planner frame must not decode
    as the nominal joint pose: that would drop the selected wheel while it is
    still over the obstacle. Reuse only a target from the same selected leg
    and serial phase, keep the current wheel commands untouched, and mark the
    fallback row valid so the caller actually applies it.
    """
    action = torch.as_tensor(action).clone()
    if action.ndim != 2 or action.shape[1] <= 0:
        raise ValueError("action must have shape [batch, action_dim]")
    batch = int(action.shape[0])
    valid = torch.as_tensor(valid, device=action.device, dtype=torch.bool).reshape(-1)
    teacher_active = torch.as_tensor(
        teacher_active, device=action.device, dtype=torch.bool
    ).reshape(-1)
    obstacle_hold = torch.as_tensor(
        obstacle_hold, device=action.device, dtype=torch.bool
    ).reshape(-1)
    selected_leg = torch.as_tensor(
        selected_leg, device=action.device, dtype=torch.long
    ).reshape(-1)
    selected_phase = torch.as_tensor(
        selected_phase, device=action.device, dtype=torch.long
    ).reshape(-1)
    last_leg = torch.as_tensor(last_leg, device=action.device, dtype=torch.long).reshape(-1)
    last_phase = torch.as_tensor(last_phase, device=action.device, dtype=torch.long).reshape(-1)
    last_leg_action = torch.as_tensor(
        last_leg_action, device=action.device, dtype=action.dtype
    )
    leg_cols = tuple(int(index) for index in leg_cols)
    rows = (valid, teacher_active, obstacle_hold, selected_leg, selected_phase,
            last_leg, last_phase)
    if any(row.numel() != batch for row in rows):
        raise ValueError("all per-environment state must match action batch size")
    if (not leg_cols or len(set(leg_cols)) != len(leg_cols)
            or any(index < 0 or index >= action.shape[1] for index in leg_cols)
            or last_leg_action.shape != (batch, len(leg_cols))
            or not torch.isfinite(last_leg_action).all()):
        raise ValueError("finite cached leg targets and unique in-range leg columns required")
    held = (~valid & teacher_active & obstacle_hold
            & (selected_leg == last_leg)
            & (selected_phase >= 0)
            & (selected_phase == last_phase))
    if held.any():
        col_mask = torch.zeros(action.shape[1], device=action.device, dtype=torch.bool)
        col_mask[list(leg_cols)] = True
        action[held[:, None] & col_mask[None, :]] = last_leg_action[held].reshape(-1)
    return action, valid | held, held


def build_m1_post_cross_recovery_action(
    current_joint_pos, default_joint_pos, *, planner_cols, wheel_cols,
    leg_action_scale, max_joint_step_rad=0.10,
):
    """Return a bounded nominal-stance recovery command after a crossing.

    Leg targets approach the M1 default support pose by at most
    ``max_joint_step_rad`` per control tick. Wheel commands are zero during
    this short balance-settling interval so the next obstacle is not entered
    before the support polygon is recovered.
    """
    current = torch.as_tensor(current_joint_pos)
    default = torch.as_tensor(default_joint_pos, device=current.device, dtype=current.dtype)
    if current.ndim != 2 or current.shape[1] != 16 or default.shape != current.shape:
        raise ValueError("current_joint_pos and default_joint_pos must have shape [B,16]")
    planner_cols = tuple(int(index) for index in planner_cols)
    wheel_cols = tuple(int(index) for index in wheel_cols)
    if len(planner_cols) != 12 or len(wheel_cols) != 4:
        raise ValueError("M1 action requires 12 leg columns and 4 wheel columns")
    scale = float(leg_action_scale)
    step = float(max_joint_step_rad)
    if not (scale > 0.0 and step > 0.0):
        raise ValueError("leg_action_scale and max_joint_step_rad must be positive")
    target = current[:, planner_cols] + (
        default[:, planner_cols] - current[:, planner_cols]
    ).clamp(-step, step)
    action = torch.zeros_like(current)
    action[:, planner_cols] = (
        (target - default[:, planner_cols]) / scale
    ).clamp(-1.0, 1.0)
    action[:, wheel_cols] = 0.0
    return torch.nan_to_num(action, nan=0.0, posinf=1.0, neginf=-1.0)


def m1_recovery_pose_ready(current_joint_pos, default_joint_pos, *, tolerance_rad=0.15):
    """Require measured leg joints to return near the nominal support pose."""
    current = torch.as_tensor(current_joint_pos)
    default = torch.as_tensor(default_joint_pos, device=current.device, dtype=current.dtype)
    tolerance = float(tolerance_rad)
    if current.ndim != 2 or current.shape[1] != 12 or default.shape != current.shape:
        raise ValueError("current and default M1 leg poses must have shape [B,12]")
    if tolerance <= 0.0:
        raise ValueError("tolerance_rad must be positive")
    finite = torch.isfinite(current).all(dim=-1) & torch.isfinite(default).all(dim=-1)
    error = (current - default).abs().amax(dim=-1)
    return finite & (error <= tolerance)


def m1_obstacle_crossing_phase_progress(age, obstacle_hold, *, phase_block,
                                        clearance_complete=None):
    """Keep horizontal progress monotonic while a swing foot is held high."""
    age = torch.as_tensor(age, dtype=torch.long)
    obstacle_hold = torch.as_tensor(obstacle_hold, device=age.device, dtype=torch.bool)
    if obstacle_hold.shape != age.shape:
        raise ValueError("obstacle_hold must match age")
    phase_block = max(1, int(phase_block))
    wrapped = (age.remainder(phase_block).to(torch.float32) + 1.0) / float(phase_block)
    held = ((age.to(torch.float32) + 1.0) / float(phase_block)).clamp(0.0, 1.0)
    progress = torch.where(obstacle_hold, torch.maximum(wrapped, held), wrapped)
    if clearance_complete is not None:
        clearance_complete = torch.as_tensor(
            clearance_complete, device=age.device, dtype=torch.bool
        )
        if clearance_complete.shape != age.shape:
            raise ValueError("clearance_complete must match age")
        progress = torch.where(clearance_complete, torch.ones_like(progress), progress)
    return progress


def m1_apply_obstacle_lift_floor(lift, obstacle_hold, *, lift_amplitude_m,
                                 hold_fraction=0.75):
    """Maintain enough foot height while its horizontal target crosses a block."""
    lift = torch.as_tensor(lift)
    obstacle_hold = torch.as_tensor(obstacle_hold, device=lift.device, dtype=torch.bool)
    if obstacle_hold.shape != lift.shape:
        raise ValueError("obstacle_hold must match lift")
    fraction = min(max(float(hold_fraction), 0.0), 1.0)
    floor = lift.new_full(lift.shape, max(0.0, float(lift_amplitude_m)) * fraction)
    return torch.where(obstacle_hold, torch.maximum(lift, floor), lift)


def m1_knee_lift_gate(phase_index, *, phase_block, obstacle_lift_hold,
                      end_fraction=0.72, clearance_complete=None):
    """Keep the knee lift floor through measured obstacle clearance.

    The nominal phase cutoff is useful for touchdown after a completed swing,
    but an active strict obstacle event must override it until far-side
    clearance ends the hold.
    """
    phase = torch.as_tensor(phase_index, dtype=torch.long)
    if phase.ndim == 0:
        phase = phase.reshape(1)
    if phase.ndim != 1 or torch.any(phase < 0):
        raise ValueError("phase_index must be a nonnegative scalar or vector")
    hold = torch.as_tensor(obstacle_lift_hold, device=phase.device, dtype=torch.bool)
    if hold.ndim == 0:
        hold = hold.reshape(1)
    if hold.ndim != 1:
        raise ValueError("obstacle_lift_hold must be a scalar or vector")
    batch = max(phase.numel(), hold.numel())
    if phase.numel() == 1 and batch > 1:
        phase = phase.expand(batch)
    if hold.numel() == 1 and batch > 1:
        hold = hold.expand(batch)
    if phase.numel() != hold.numel():
        raise ValueError("phase_index and obstacle_lift_hold batch sizes must match")
    block = max(1, int(phase_block))
    fraction = float(end_fraction)
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("end_fraction must be in [0, 1]")
    phase_progress = (phase.remainder(block).to(torch.float32) + 1.0) / float(block)
    gate = (phase_progress < fraction) | hold
    if clearance_complete is not None:
        clearance_complete = torch.as_tensor(
            clearance_complete, device=phase.device, dtype=torch.bool
        )
        if clearance_complete.ndim == 0:
            clearance_complete = clearance_complete.reshape(1)
        if clearance_complete.numel() == 1 and batch > 1:
            clearance_complete = clearance_complete.expand(batch)
        if clearance_complete.shape != phase.shape:
            raise ValueError("clearance_complete must match phase batch size")
        gate &= ~clearance_complete
    return gate


def m1_strict_crossing_event_active(*, target_wheel, awaiting_recovery, failed):
    """Keep the serial swing owned by one strict event until its far-edge pass.

    ``target_wheel`` is latched from measured wheel/obstacle geometry by the
    strict tracker. Recovery is a separate phase, and failed/inactive rows
    must not continue receiving crossing-only commands.
    """
    target_wheel = torch.as_tensor(target_wheel, dtype=torch.long)
    device = target_wheel.device
    awaiting_recovery = torch.as_tensor(
        awaiting_recovery, device=device, dtype=torch.bool
    ).reshape(-1)
    failed = torch.as_tensor(failed, device=device, dtype=torch.bool).reshape(-1)
    target_wheel = target_wheel.reshape(-1)
    if awaiting_recovery.shape != target_wheel.shape or failed.shape != target_wheel.shape:
        raise ValueError("strict crossing event state must use matching batch vectors")
    if torch.any((target_wheel < -1) | (target_wheel > 3)):
        raise ValueError("target_wheel must be -1 or a valid M1 leg index")
    return (target_wheel >= 0) & ~awaiting_recovery & ~failed


def m1_strict_crossing_lift_hold(*, target_wheel, awaiting_recovery, failed,
                                 clearance_seen, far_seen):
    """Hold the selected wheel high only until measured far-side clearance.

    The strict event continues owning the selected leg after this lift hold is
    released, so the same leg can descend and establish loaded touchdown before
    the crossing is counted or balance recovery begins.
    """
    event_active = m1_strict_crossing_event_active(
        target_wheel=target_wheel,
        awaiting_recovery=awaiting_recovery,
        failed=failed,
    )
    clearance_seen = torch.as_tensor(
        clearance_seen, device=event_active.device, dtype=torch.bool
    ).reshape(-1)
    far_seen = torch.as_tensor(
        far_seen, device=event_active.device, dtype=torch.bool
    ).reshape(-1)
    if clearance_seen.shape != event_active.shape or far_seen.shape != event_active.shape:
        raise ValueError("strict clearance latches must match event batch size")
    return event_active & ~(clearance_seen & far_seen)


def m1_merge_strict_event_hold(*, predictor_hold, strict_event_active,
                               strict_lift_hold=None):
    """Let measured event ownership outlive timeout, then permit touchdown.

    ``strict_event_active`` owns the leg through touchdown. If a distinct
    ``strict_lift_hold`` is supplied, it replaces the predictor lift hold for
    that event; this allows descent after far-side geometry clears without
    releasing the leg or switching to post-cross recovery early.
    """
    predictor_hold = torch.as_tensor(predictor_hold, dtype=torch.bool)
    strict_event_active = torch.as_tensor(
        strict_event_active, device=predictor_hold.device, dtype=torch.bool
    )
    if predictor_hold.ndim != 1 or strict_event_active.shape != predictor_hold.shape:
        raise ValueError("predictor and strict event holds must be matching vectors")
    if strict_lift_hold is not None:
        strict_lift_hold = torch.as_tensor(
            strict_lift_hold, device=predictor_hold.device, dtype=torch.bool
        )
        if strict_lift_hold.shape != predictor_hold.shape:
            raise ValueError("strict lift hold must match the event batch size")
        return torch.where(strict_event_active, strict_lift_hold, predictor_hold)
    return predictor_hold | strict_event_active


def advance_obstacle_lift_hold(*, previous_hold, clear_steps, held_steps,
                               selected_collision, age, phase_block,
                               clear_required=8, max_hold_steps=32):
    """Hold late in swing until wheel and knee clear, without pinning the apex.

    A collision at mid-swing must not pin the leg before it has traversed the
    obstacle. The hold begins in the final 3/8 of the swing: early enough to
    keep the wheel lifted through obstacle clearance, while still allowing
    the forward arc to complete. Clearance dwell and total hold remain bounded
    so a stale collision mask cannot deadlock the serial gait indefinitely.
    """
    previous_hold = torch.as_tensor(previous_hold, dtype=torch.bool)
    device = previous_hold.device
    age = torch.as_tensor(age, device=device, dtype=torch.long)
    clear_steps = torch.as_tensor(clear_steps, device=device, dtype=torch.long)
    held_steps = torch.as_tensor(held_steps, device=device, dtype=torch.long)
    selected_collision = torch.as_tensor(
        selected_collision, device=device, dtype=torch.bool
    )
    if (previous_hold.ndim != 1 or age.shape != previous_hold.shape
            or clear_steps.shape != previous_hold.shape
            or held_steps.shape != previous_hold.shape
            or selected_collision.shape != previous_hold.shape):
        raise ValueError('hold state, age, and hold counters must be matching vectors')
    if torch.any(age < 0) or torch.any(clear_steps < 0) or torch.any(held_steps < 0):
        raise ValueError('phase age and hold counters must be nonnegative')
    phase_block = max(1, int(phase_block))
    clear_required = max(1, int(clear_required))
    max_hold_steps = max(1, int(max_hold_steps))

    # Hold from the rising portion, before the wheel has descended back toward
    # the floor.  The caller keeps horizontal progress live and clamps only
    # vertical clearance while this mask remains true.
    hold_phase = max(1, phase_block // 4)
    eligible = age.remainder(phase_block) >= hold_phase
    # A phase gets one hold attempt. Otherwise an expired hold can retrigger
    # every tick in the final-quarter window and advance the swing only one
    # frame per hold timeout.
    phase_hold_used = held_steps >= max_hold_steps
    candidate = previous_hold | (selected_collision & eligible & ~phase_hold_used)
    next_clear_steps = torch.where(
        candidate & ~selected_collision,
        clear_steps + 1,
        torch.zeros_like(clear_steps),
    )
    next_held_steps = torch.where(candidate, held_steps + 1, held_steps)
    clear_complete = next_clear_steps >= clear_required
    hold_expired = next_held_steps >= max_hold_steps
    next_hold = candidate & ~clear_complete & ~hold_expired
    phase_complete = clear_complete | hold_expired
    next_held_steps = torch.where(
        phase_complete, torch.full_like(next_held_steps, max_hold_steps), next_held_steps,
    )
    next_held_steps = torch.where(
        (age.remainder(phase_block) == 0) & ~previous_hold,
        torch.zeros_like(next_held_steps), next_held_steps,
    )
    next_clear_steps = torch.where(
        next_hold, next_clear_steps, torch.zeros_like(next_clear_steps)
    )
    return next_hold, next_clear_steps, next_held_steps, age
