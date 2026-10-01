import torch


def test_m1_teacher_does_not_clip_high_knee_clearance_target(monkeypatch):
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES

    monkeypatch.setenv("M1_TEACHER_SLEW_RAD", "2.0")
    default = torch.zeros((1, len(M1_ASSET_JOINT_NAMES)))
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
