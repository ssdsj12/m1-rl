import torch


def test_m1_teacher_invalid_joint_state_is_marked_invalid_and_finite():
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action

    target = torch.zeros(1, 12)
    default = torch.zeros(1, 16)
    current = default.clone()
    current[0, 0] = float("nan")
    action, valid = reference_to_m1_action(
        {"joint_angles": target, "valid_mask": torch.ones(1, dtype=torch.bool)},
        default,
        current_joint_pos=current,
    )
    assert torch.isfinite(action).all()
    assert not bool(valid.item())


def test_m1_teacher_safety_hands_back_before_fall():
    from ame_baseline.m1_mpc_teacher import apply_m1_teacher_safety

    action = torch.ones((2, 16), dtype=torch.float32)
    valid = torch.tensor([True, True])
    rpy = torch.tensor([[0.10, 0.08, 0.0], [0.31, 0.0, 0.0]])
    safe_action, safe = apply_m1_teacher_safety(action, valid, rpy, max_tilt_rad=0.30)
    assert safe.tolist() == [True, False]
    assert torch.count_nonzero(safe_action[0]) == 16
    assert torch.count_nonzero(safe_action[1]) == 0


def test_m1_teacher_recovery_hold_preserves_measured_hold(monkeypatch):
    from ame_baseline.m1_mpc_teacher import apply_m1_teacher_safety

    monkeypatch.setenv("M1_TEACHER_RECOVERY_HOLD", "1")
    action = torch.ones((1, 16), dtype=torch.float32)
    valid = torch.tensor([False])
    rpy = torch.tensor([[0.40, 0.0, 0.0]])
    safe_action, safe = apply_m1_teacher_safety(action, valid, rpy, max_tilt_rad=0.30)
    assert safe.tolist() == [False]
    assert torch.count_nonzero(safe_action) == 16


def test_active_crossing_keeps_finite_swing_command_through_bounded_tilt():
    from ame_baseline.m1_mpc_teacher import apply_m1_teacher_safety

    action = torch.ones((2, 16), dtype=torch.float32)
    valid = torch.tensor([True, False])
    rpy = torch.tensor([[0.38, 0.0, 0.0], [0.42, 0.0, 0.0]])
    safe_action, safe = apply_m1_teacher_safety(
        action,
        valid,
        rpy,
        max_tilt_rad=0.30,
        crossing_active=torch.tensor([True, True]),
        crossing_max_tilt_rad=0.45,
    )
    assert safe.tolist() == [True, True]
    assert torch.count_nonzero(safe_action[0]) == 16
    assert torch.count_nonzero(safe_action[1]) == 16


def test_active_crossing_still_fails_closed_above_crossing_tilt_bound():
    from ame_baseline.m1_mpc_teacher import apply_m1_teacher_safety

    action = torch.ones((1, 16), dtype=torch.float32)
    safe_action, safe = apply_m1_teacher_safety(
        action,
        torch.tensor([True]),
        torch.tensor([[0.46, 0.0, 0.0]]),
        max_tilt_rad=0.30,
        crossing_active=torch.tensor([True]),
        crossing_max_tilt_rad=0.45,
    )
    assert safe.tolist() == [False]
    assert torch.count_nonzero(safe_action) == 0
