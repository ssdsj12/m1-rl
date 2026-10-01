import torch


def test_m1_teacher_stance_action_decodes_to_measured_pose():
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS, m1_action_targets
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action
    from extension.parallelism.m1_kinematics import (
        M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES,
    )
    from extension.parallelism.rl_adapter import resolve_named_indices

    planner_cols = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    default = torch.tensor(M1_TRAINING_JOINT_POS, dtype=torch.float32).view(1, 16)
    current = default.clone()
    current[0, planner_cols[4]] += 0.20
    reference = {
        'joint_angles': current[:, planner_cols].clone(),
        'contact_state': torch.tensor([[False, True, True, True]]),
        'phase_index': torch.tensor([1]),
        'valid_mask': torch.tensor([True]),
    }
    reference['joint_angles'][0, 2] += 0.30

    action, valid = reference_to_m1_action(reference, default, current_joint_pos=current)
    decoded = m1_action_targets(action, default)

    assert bool(valid.item())
    assert torch.allclose(
        decoded[0, planner_cols[4]], current[0, planner_cols[4]], atol=1e-5
    )
