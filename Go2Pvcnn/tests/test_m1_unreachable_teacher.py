import torch


def test_finite_ik_fallback_does_not_certify_unreachable_swing(monkeypatch):
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS, M1_TRAINING_ROOT_Z_M
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, m1_fk
    for key, value in {
        'M1_TEACHER_SERIAL_FORCE': '1', 'M1_TEACHER_FOOT_TRAJECTORY': '1',
        'M1_TEACHER_USE_PLANNER_FOOT_TARGET': '1', 'M1_TEACHER_USE_PLANNER_CONTACT': '0',
        'M1_TEACHER_IK_FALLBACK': '1', 'M1_TEACHER_USE_GENERIC_MPC': '0',
    }.items():
        monkeypatch.setenv(key, value)
    cols = [M1_ASSET_JOINT_NAMES.index(name) for name in M1_PLANNER_JOINT_NAMES]
    default = torch.tensor([M1_TRAINING_JOINT_POS])
    root = torch.tensor([[0., 0., M1_TRAINING_ROOT_Z_M]])
    rpy = torch.zeros_like(root)
    feet = m1_fk(root, rpy, default[:, cols]).foot_pos_w
    feet[0, 0, 0] = 2.0  # beyond the physical linkage, though IK stays finite
    reference = dict(joint_angles=default[:, cols], valid_mask=torch.tensor([True]),
                     contact_state=torch.ones((1,4), dtype=torch.bool),
                     serial_leg_override=torch.tensor([0]), phase_index=torch.tensor([0]),
                     m1_root_pos_w=root, m1_root_rpy_w=rpy,
                     hold_joint_angles=default[:, cols], foot_pos_w=feet)
    action, valid = reference_to_m1_action(reference, default, current_joint_pos=default)
    assert torch.isfinite(action).all(), 'fallback must retain finite stabilization output'
    assert not valid.item(), 'finite fallback is not a reachable teacher target'
