import torch


def test_far_side_clearance_commands_vertical_touchdown_at_measured_safe_xy(monkeypatch):
    import ame_baseline.m1_mpc_teacher as teacher
    from extension.parallelism.m1_kinematics import (
        M1_ASSET_JOINT_NAMES,
        M1_DEFAULT_ASSET_JOINT_POS,
        M1_PLANNER_JOINT_NAMES,
        m1_fk,
    )
    from extension.parallelism.rl_adapter import resolve_named_indices

    monkeypatch.setenv("M1_TEACHER_SERIAL_FORCE", "1")
    monkeypatch.setenv("M1_TEACHER_FOOT_TRAJECTORY", "1")
    monkeypatch.setenv("M1_TEACHER_USE_PLANNER_FOOT_TARGET", "1")
    monkeypatch.setenv("M1_TEACHER_SLEW_RAD", "3.0")
    default = torch.tensor([M1_DEFAULT_ASSET_JOINT_POS], dtype=torch.float32)
    planner_cols = resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES)
    root = torch.tensor([[0.0, 0.0, 0.52]], dtype=torch.float32)
    rpy = torch.zeros((1, 3), dtype=torch.float32)
    current_fk = m1_fk(root, rpy, default[:, planner_cols])
    planner_local = current_fk.foot_pos_w - root[:, None, :]
    planner_local[:, 0, 0] += 0.10
    captured = []

    def capture_ik(root_pos, root_rpy, target):
        captured.append(target.detach().clone())
        return torch.zeros((1, 4, 3), dtype=target.dtype), torch.ones(
            (1, 4), dtype=torch.bool, device=target.device,
        )

    monkeypatch.setattr(teacher, "m1_ik", capture_ik)
    reference = {
        "joint_angles": torch.zeros((1, 12), dtype=torch.float32),
        "valid_mask": torch.ones(1, dtype=torch.bool),
        "contact_state": torch.tensor([[False, True, True, True]]),
        "serial_phase_index": torch.tensor([40]),
        "serial_leg_override": torch.tensor([0]),
        "serial_obstacle_lift_hold": torch.tensor([False]),
        "serial_obstacle_clearance_complete": torch.tensor([True]),
        "hold_joint_angles": default[:, planner_cols],
        "hold_foot_pos_w": current_fk.foot_pos_w,
        "foot_pos_w": current_fk.foot_pos_w,
        "foot_pos_root": planner_local,
        "m1_root_pos_w": root,
        "m1_root_rpy_w": rpy,
    }

    _, valid = teacher.reference_to_m1_action(
        reference, default, current_joint_pos=default,
    )

    assert bool(valid.item())
    torch.testing.assert_close(
        captured[0][0, 0, :2], current_fk.foot_pos_w[0, 0, :2],
    )
    torch.testing.assert_close(
        captured[0][0, 1:, :2],
        (root[:, None, :] + planner_local)[0, 1:, :2],
    )
    no_clearance_reference = dict(reference)
    no_clearance_reference["serial_obstacle_clearance_complete"] = torch.tensor([False])
    teacher.reference_to_m1_action(
        no_clearance_reference, default, current_joint_pos=default,
    )
    assert captured[0][0, 0, 2] < captured[1][0, 0, 2]


def test_m1_teacher_does_not_clip_high_knee_clearance_target(monkeypatch):
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_DEFAULT_ASSET_JOINT_POS

    monkeypatch.setenv("M1_TEACHER_SLEW_RAD", "2.0")
    default = torch.tensor([M1_DEFAULT_ASSET_JOINT_POS], dtype=torch.float32)
    current = default.clone()
    target = torch.tensor([[0.0, 0.0, 1.90, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    action, valid = reference_to_m1_action(
        {
            "joint_angles": target,
            "valid_mask": torch.ones(1, dtype=torch.bool),
            "contact_state": torch.tensor([[False, True, True, True]]),
            "phase_index": torch.tensor([0]),
        },
        default,
        current_joint_pos=current,
    )
    assert bool(valid.item())
    # A 10 cm course needs the knee target above the old 0.55 rad cap;
    # normalized action must retain enough authority to request it.
    knee_col = 2
    assert float(action[0, knee_col]) > 0.50


def test_m1_serial_swing_knee_uses_available_physical_range_not_global_delta_cap(monkeypatch):
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action
    from ame_baseline.m1_ame_contract import m1_action_targets
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_DEFAULT_ASSET_JOINT_POS

    monkeypatch.setenv("M1_TEACHER_MAX_DELTA_RAD", "1.10")
    monkeypatch.setenv("M1_TEACHER_SLEW_RAD", "3.0")
    monkeypatch.setenv("M1_TEACHER_SERIAL_FORCE", "1")
    default = torch.tensor([M1_DEFAULT_ASSET_JOINT_POS], dtype=torch.float32)
    current = default.clone()
    target = torch.zeros((1, 12))
    target[0, 2] = 2.5
    action, valid = reference_to_m1_action(
        {
            "joint_angles": target,
            "valid_mask": torch.ones(1, dtype=torch.bool),
            "serial_leg_override": torch.tensor([0]),
            "contact_state": torch.tensor([[False, True, True, True]]),
            "phase_index": torch.tensor([16]),
        },
        default,
        current_joint_pos=current,
    )
    decoded = m1_action_targets(action, default)
    assert bool(valid.item())
    assert 2.45 < float(decoded[0, 2]) <= 2.801
