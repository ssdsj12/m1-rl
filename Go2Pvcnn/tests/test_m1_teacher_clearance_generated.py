import torch


def test_m1_teacher_slew_reaches_strict_wheel_bottom_clearance():
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS, M1_TRAINING_ROOT_Z_M, m1_action_targets
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_RADIUS_M, m1_fk
    from extension.parallelism.rl_adapter import resolve_named_indices

    default = torch.tensor([M1_TRAINING_JOINT_POS], dtype=torch.float32)
    current = default.clone()
    planner_cols = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    target = default[:, planner_cols].clone()
    target[:, 1] -= 0.14
    target[:, 2] += 0.80
    reference = {
        "joint_angles": target,
        "valid_mask": torch.ones(1, dtype=torch.bool),
        "contact_state": torch.tensor([[False, True, True, True]]),
        "phase_index": torch.tensor([0]),
    }
    bottoms = []
    for phase in range(5):
        reference["phase_index"] = torch.tensor([phase])
        action, valid = reference_to_m1_action(reference, default, current_joint_pos=current)
        assert bool(valid.item())
        current = m1_action_targets(action, default)
        feet = m1_fk(
            torch.tensor([[0.0, 0.0, M1_TRAINING_ROOT_Z_M]]),
            torch.zeros((1, 3)),
            current[:, planner_cols],
        ).foot_pos_w
        bottoms.append(float((feet[0, 0, 2] - M1_WHEEL_RADIUS_M).item()))
    assert max(bottoms) >= 0.10, bottoms
    assert abs(float(bottoms[-1] - (feet[0, 1, 2] - M1_WHEEL_RADIUS_M))) >= 0.10
