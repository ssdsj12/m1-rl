import torch


def test_m1_teacher_uses_finite_clamped_ik_fallback(monkeypatch):
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_ROOT_Z_M, m1_fk
    from extension.parallelism.rl_adapter import resolve_named_indices

    monkeypatch.setenv('M1_TEACHER_SERIAL_FORCE', '1')
    monkeypatch.setenv('M1_TEACHER_FOOT_TRAJECTORY', '1')
    monkeypatch.setenv('M1_TEACHER_USE_PLANNER_FOOT_TARGET', '0')
    monkeypatch.setenv('M1_TEACHER_IK_FALLBACK', '1')
    monkeypatch.setenv('M1_TEACHER_FOOT_ADVANCE_M', '1.0')
    cols = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    default = torch.tensor(M1_TRAINING_JOINT_POS, dtype=torch.float32).view(1, 16)
    root = torch.tensor([[0.0, 0.0, M1_ROOT_Z_M]])
    rpy = torch.zeros((1, 3))
    hold = m1_fk(root, rpy, default[:, cols]).foot_pos_w
    reference = {
        'joint_angles': default[:, cols].clone(),
        'valid_mask': torch.ones(1, dtype=torch.bool),
        'contact_state': torch.tensor([[False, True, True, True]]),
        'phase_index': torch.tensor([32]),
        'serial_leg_override': torch.tensor([0]),
        'm1_root_pos_w': root,
        'm1_root_rpy_w': rpy,
        'hold_joint_angles': default[:, cols].clone(),
        'hold_foot_pos_w': hold,
    }
    action, valid = reference_to_m1_action(reference, default, current_joint_pos=default)
    assert bool(valid.item())
    assert torch.isfinite(action).all()


def test_m1_training_wrapper_enables_ik_fallback():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / 'scripts/run_m1_train_with_placeholder.sh').read_text()
    assert 'M1_TEACHER_IK_FALLBACK="${M1_TEACHER_IK_FALLBACK:-1}"' in source
