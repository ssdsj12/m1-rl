"""End-to-end teacher/decoder/FK checks, without an idealized IK-only shortcut."""
import pytest
import torch

from ame_baseline.m1_ame_contract import (
    M1_TRAINING_JOINT_POS, M1_TRAINING_ROOT_Z_M, m1_action_targets,
)
from ame_baseline.m1_mpc_teacher import reference_to_m1_action
from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, m1_fk,
)

COLS = [M1_ASSET_JOINT_NAMES.index(n) for n in M1_PLANNER_JOINT_NAMES]


@pytest.mark.parametrize("leg", range(4))
@pytest.mark.parametrize("body_speed", [0.0, 0.10])
def test_vertical_lift_holds_xy_and_height_through_actual_action_decoder(
    monkeypatch, leg, body_speed,
):
    for key, value in {
        "M1_TEACHER_SERIAL_FORCE": "1",
        "M1_TEACHER_FOOT_TRAJECTORY": "1",
        "M1_TEACHER_USE_PLANNER_FOOT_TARGET": "1",
        "M1_TEACHER_FOOT_LIFT_M": "0.156",
        "M1_TEACHER_OBSTACLE_HOLD_LIFT_FRACTION": "1.0",
        "M1_TEACHER_SLEW_RAD": "0.10",
        "M1_TEACHER_REPROJECT_STANCE": "0",
    }.items():
        monkeypatch.setenv(key, value)
    default = torch.tensor([M1_TRAINING_JOINT_POS])
    current = default.clone()
    root = torch.tensor([[0.0, 0.0, M1_TRAINING_ROOT_Z_M]])
    rpy = torch.zeros((1, 3))
    contacts = torch.ones((1, 4), dtype=torch.bool)
    contacts[0, leg] = False
    baseline = m1_fk(root, rpy, default[:, COLS]).foot_pos_w
    local_xy = baseline[0, leg, :2].clone()
    requested_z = baseline[0, leg, 2] + 0.156
    support_cols = [c for i in range(4) if i != leg for c in COLS[3*i:3*i+3]]
    for step in range(70):
        root[0, 0] = step * 0.02 * body_speed
        requested = m1_fk(root, rpy, default[:, COLS]).foot_pos_w
        requested[0, leg, 2] = requested_z
        reference = dict(
            joint_angles=default[:, COLS].clone(), valid_mask=torch.tensor([True]),
            contact_state=contacts, phase_index=torch.tensor([step]),
            serial_leg_override=torch.tensor([leg]),
            serial_obstacle_lift_hold=torch.tensor([True]),
            m1_root_pos_w=root, m1_root_rpy_w=rpy, foot_pos_w=requested,
            hold_joint_angles=default[:, COLS],
        )
        action, valid = reference_to_m1_action(reference, default, current_joint_pos=current)
        assert bool(valid.item())
        decoded = m1_action_targets(action, default)
        assert float((decoded[:, COLS] - current[:, COLS]).abs().max()) <= 0.10001
        actual = m1_fk(root, rpy, decoded[:, COLS]).foot_pos_w
        torch.testing.assert_close(actual[0, leg, :2] - root[0, :2], local_xy, atol=2e-5, rtol=0)
        torch.testing.assert_close(decoded[:, support_cols], default[:, support_cols], atol=2e-6, rtol=0)
        assert float(actual[0, leg, 2]) <= float(requested_z) + 2e-5
        if step >= 15:
            torch.testing.assert_close(actual[0, leg, 2], requested_z, atol=2e-5, rtol=0)
        current = decoded


@pytest.mark.parametrize("leg", range(4))
@pytest.mark.parametrize("bottom_gap", [0.03, 0.04, 0.05])
def test_event_hold_follows_chassis_xy_not_planner_swing_or_body_heave(monkeypatch, leg, bottom_gap):
    for key, value in {
        "M1_TEACHER_SERIAL_FORCE": "1", "M1_TEACHER_FOOT_TRAJECTORY": "1",
        "M1_TEACHER_USE_PLANNER_FOOT_TARGET": "1", "M1_TEACHER_SLEW_RAD": "0.10",
        "M1_TEACHER_REPROJECT_STANCE": "0",
    }.items():
        monkeypatch.setenv(key, value)
    default = torch.tensor([M1_TRAINING_JOINT_POS])
    current = default.clone()
    anchor_root = torch.tensor([[0., 0., M1_TRAINING_ROOT_Z_M]])
    anchor_rpy = torch.zeros((1, 3))
    anchor = m1_fk(anchor_root, anchor_rpy, default[:, COLS]).foot_pos_w
    root, rpy = anchor_root.clone(), anchor_rpy.clone()
    from ame_baseline.m1_crossing_clearance import wheel_center_target_z
    from extension.parallelism.m1_kinematics import M1_WHEEL_RADIUS_M
    target_z = wheel_center_target_z(torch.tensor([0.10]),
        wheel_radius=M1_WHEEL_RADIUS_M, bottom_clearance=bottom_gap)
    for step in range(70):
        root[0, 0] = .001 * step
        root[0, 2] = anchor_root[0, 2] - min(step, 20) * .001
        # Feed a deliberately inappropriate planner swing: event-owned M1
        # lift/roll must not inherit its forward/backward foot excursion.
        planner = anchor.clone()
        planner[:, leg, 0] += .20
        reference = dict(
            joint_angles=default[:, COLS], valid_mask=torch.tensor([True]),
            contact_state=torch.ones((1, 4), dtype=torch.bool),
            phase_index=torch.tensor([step]), serial_leg_override=torch.tensor([leg]),
            serial_obstacle_lift_hold=torch.tensor([True]),
            m1_root_pos_w=root, m1_root_rpy_w=rpy, foot_pos_w=planner,
            hold_joint_angles=default[:, COLS], hold_foot_pos_w=anchor,
            hold_root_pos_w=anchor_root, hold_root_rpy_w=anchor_rpy,
            serial_wheel_target_z_w=target_z,
        )
        action, valid = reference_to_m1_action(reference, default, current_joint_pos=current)
        assert valid.item()
        current = m1_action_targets(action, default)
        actual = m1_fk(root, rpy, current[:, COLS]).foot_pos_w
        torch.testing.assert_close(actual[0, leg, :2] - root[0, :2], anchor[0, leg, :2], atol=2e-5, rtol=0)
        if step >= 20:
            torch.testing.assert_close(actual[:, leg, 2], target_z, atol=2e-5, rtol=0)
            torch.testing.assert_close(actual[:, leg, 2] - M1_WHEEL_RADIUS_M - 0.10,
                torch.tensor([bottom_gap]), atol=2e-5, rtol=0)
