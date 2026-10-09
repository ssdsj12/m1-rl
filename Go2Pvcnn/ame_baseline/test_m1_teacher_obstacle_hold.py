import torch

from ame_baseline.m1_teacher_phase import (
    advance_obstacle_lift_hold,
    build_m1_post_cross_recovery_action,
    m1_recovery_pose_ready,
    gate_probe_invalid_wheel_actions,
    serial_crossing_wheel_actions,
)
from ame_baseline.ame_env_wrapper import (
    _advance_m1_teacher_phase,
    _m1_teacher_obstacle_hold_max_steps,
)
from ame_baseline.ame_env_wrapper import _m1_fixed_obstacle_proximity_from_foot_xy


def test_obstacle_hold_freezes_lift_arc_until_collision_mask_clears_with_dwell():
    age = torch.tensor([27], dtype=torch.long)
    hold = torch.tensor([True])
    clear_steps = torch.tensor([0], dtype=torch.long)
    held_steps = torch.tensor([0], dtype=torch.long)

    for expected_clear in range(1, 8):
        hold, clear_steps, held_steps, phase_index = advance_obstacle_lift_hold(
            previous_hold=hold, clear_steps=clear_steps,
            held_steps=held_steps,
            selected_collision=torch.tensor([False]), age=age,
            phase_block=32, clear_required=8,
        )
        assert hold.tolist() == [True]
        assert clear_steps.tolist() == [expected_clear]
        assert phase_index.tolist() == [20]

    hold, clear_steps, held_steps, phase_index = advance_obstacle_lift_hold(
        previous_hold=hold, clear_steps=clear_steps,
        held_steps=held_steps,
        selected_collision=torch.tensor([False]), age=age,
        phase_block=32, clear_required=8,
    )
    assert hold.tolist() == [False]
    assert clear_steps.tolist() == [0]
    assert held_steps.tolist() == [32]
    assert phase_index.tolist() == [27]


def test_obstacle_hold_does_not_freeze_mid_swing_but_holds_near_descent():
    hold, clear_steps, held_steps, phase_index = advance_obstacle_lift_hold(
        previous_hold=torch.tensor([False, False]),
        clear_steps=torch.tensor([0, 0]),
        held_steps=torch.tensor([0, 0]),
        selected_collision=torch.tensor([True, True]),
        age=torch.tensor([16, 59]), phase_block=32, clear_required=8,
    )
    assert hold.tolist() == [False, True]
    assert clear_steps.tolist() == [0, 0]
    assert held_steps.tolist() == [0, 1]
    assert phase_index.tolist() == [16, 52]


def test_obstacle_hold_reasserts_lift_phase_if_collision_returns_during_dwell():
    hold, clear_steps, held_steps, phase_index = advance_obstacle_lift_hold(
        previous_hold=torch.tensor([True]), clear_steps=torch.tensor([6]),
        held_steps=torch.tensor([3]),
        selected_collision=torch.tensor([True]), age=torch.tensor([30]),
        phase_block=32, clear_required=8,
    )
    assert hold.tolist() == [True]
    assert clear_steps.tolist() == [0]
    assert held_steps.tolist() == [4]
    assert phase_index.tolist() == [20]


def test_persistent_obstacle_mask_cannot_freeze_the_teacher_phase_forever():
    hold = torch.tensor([True])
    clear_steps = torch.tensor([0], dtype=torch.long)
    held_steps = torch.tensor([0], dtype=torch.long)
    phase_index = None
    for _ in range(12):
        hold, clear_steps, held_steps, phase_index = advance_obstacle_lift_hold(
            previous_hold=hold,
            clear_steps=clear_steps,
            held_steps=held_steps,
            selected_collision=torch.tensor([True]),
            age=torch.tensor([24]),
            phase_block=32,
            clear_required=8,
            max_hold_steps=12,
        )
    assert hold.tolist() == [False]
    assert phase_index.tolist() == [24]
    # Once the bounded clearance dwell expires, do not retrigger in this
    # swing's final-quarter window; the trajectory can continue.
    hold, clear_steps, held_steps, phase_index = advance_obstacle_lift_hold(
        previous_hold=hold,
        clear_steps=clear_steps,
        held_steps=held_steps,
        selected_collision=torch.tensor([True]),
        age=torch.tensor([25]),
        phase_block=32,
        clear_required=8,
        max_hold_steps=12,
    )
    assert hold.tolist() == [False]
    assert phase_index.tolist() == [25]
    assert held_steps.tolist() == [12]
    hold, clear_steps, held_steps, phase_index = advance_obstacle_lift_hold(
        previous_hold=hold,
        clear_steps=clear_steps,
        held_steps=held_steps,
        selected_collision=torch.tensor([True]),
        age=torch.tensor([32]),
        phase_block=32,
        clear_required=8,
        max_hold_steps=12,
    )
    assert hold.tolist() == [False]
    assert held_steps.tolist() == [0]
    assert phase_index.tolist() == [32]


def test_serial_leg_age_does_not_advance_while_obstacle_hold_is_active():
    active, age, elapsed = _advance_m1_teacher_phase(
        torch.tensor([True]), torch.tensor([27]), torch.tensor([27]),
        handoff_ready=torch.tensor([True]), support_ready=torch.tensor([True]),
        phase_hold=torch.tensor([True]), max_steps=2048, phase_block=32,
    )
    assert active.tolist() == [True]
    assert age.tolist() == [27]
    assert elapsed.tolist() == [28]

    _, resumed_age, _ = _advance_m1_teacher_phase(
        torch.tensor([True]), torch.tensor([27]), torch.tensor([28]),
        handoff_ready=torch.tensor([True]), support_ready=torch.tensor([True]),
        phase_hold=torch.tensor([False]), max_steps=2048, phase_block=32,
    )
    assert resumed_age.tolist() == [28]


def test_wrapper_default_allows_a_full_clearance_hold():
    assert _m1_teacher_obstacle_hold_max_steps() == 32


def test_fixed_obstacle_hold_tracks_knee_envelope_after_wheel_center_passes():
    origins = torch.zeros((1, 2))
    yaw = torch.zeros(1)
    # The wheel has crossed the block center, but its knee remains behind it.
    leg_points = torch.tensor([[[[0.40, 0.215], [0.65, 0.215]],
                                [[0.30, -0.215], [0.35, -0.215]],
                                [[0.10, 0.215], [0.15, 0.215]],
                                [[0.10, -0.215], [0.15, -0.215]]]])
    intersects_path = _m1_fixed_obstacle_proximity_from_foot_xy(
        leg_points, yaw, origins, forward_m=0.30, lateral_m=0.04,
        obstacle_radius_m=0.02, obstacle_local_xy=((0.55, 0.215),),
    )
    assert intersects_path.tolist() == [[True, False, False, False]]

    fully_past = leg_points.clone()
    fully_past[0, 0, :, 0] = torch.tensor([0.75, 0.80])
    cleared = _m1_fixed_obstacle_proximity_from_foot_xy(
        fully_past, yaw, origins, forward_m=0.30, lateral_m=0.04,
        obstacle_radius_m=0.02, obstacle_local_xy=((0.55, 0.215),),
    )
    assert cleared.tolist() == [[False, False, False, False]]


def test_crossing_keeps_support_wheels_rolling_while_swing_wheel_is_slowed():
    wheel_actions = serial_crossing_wheel_actions(
        forward_speed=torch.tensor([0.4]),
        selected_leg=torch.tensor([2]),
        crossing_active=torch.tensor([True]),
        phase_progress=torch.tensor([0.55]),
        support_scale=0.5,
        swing_scale=0.15,
    )
    assert torch.allclose(wheel_actions, torch.tensor([[0.2, 0.2, 0.06, 0.2]]))


def test_probe_does_not_zero_wheel_drive_on_temporary_invalid_teacher_frames():
    actions = torch.zeros((2, 16))
    wheel_cols = (3, 7, 11, 15)
    actions[:, wheel_cols] = 0.25
    gated = gate_probe_invalid_wheel_actions(
        actions,
        valid=torch.tensor([False, False]),
        teacher_active=torch.tensor([True, False]),
        wheel_cols=wheel_cols,
    )
    assert torch.all(gated[0, list(wheel_cols)] == 0.25)
    assert torch.all(gated[1, list(wheel_cols)] == 0.0)


def test_post_cross_recovery_slews_leg_targets_toward_support_pose_and_stops_wheels():
    current = torch.zeros((1, 16))
    default = torch.zeros_like(current)
    planner_cols = tuple(index for leg in range(4) for index in range(leg * 4, leg * 4 + 3))
    wheel_cols = (3, 7, 11, 15)
    current[0, list(planner_cols)] = 0.5
    current[0, list(wheel_cols)] = 0.8

    action = build_m1_post_cross_recovery_action(
        current,
        default,
        planner_cols=planner_cols,
        wheel_cols=wheel_cols,
        leg_action_scale=1.0,
        max_joint_step_rad=0.1,
    )

    # Actions encode absolute offsets from nominal, so the smoothed target
    # moves a 0.5-rad error toward nominal to a 0.4-rad error; it is not a velocity delta.
    assert torch.allclose(action[0, list(planner_cols)], torch.full((12,), 0.4))
    assert torch.all(action[0, list(wheel_cols)] == 0.0)
    assert torch.isfinite(action).all()


def test_recovery_requires_leg_pose_to_return_near_nominal():
    default = torch.zeros((2, 12))
    current = torch.tensor([[0.10] * 12, [0.16] * 12])
    assert m1_recovery_pose_ready(current, default, tolerance_rad=0.15).tolist() == [True, False]
