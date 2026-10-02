import torch
from pathlib import Path


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


def test_m1_support_compensation_is_applied_after_cartesian_swing_override():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline" / "m1_mpc_teacher.py").read_text()
    cartesian = source.index("The Cartesian swing branch can replace")
    support = source.index('support_comp = float(os.environ.get("M1_TEACHER_SUPPORT_KNEE_COMP_RAD"', cartesian)
    final_hold = source.index("desired_legs = torch.where(\n                swing.unsqueeze(-1)", support)
    assert cartesian < support < final_hold


def test_m1_teacher_uses_measured_contact_for_stance_handoff():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline" / "ame_env_wrapper.py").read_text()
    assert "actual_contact_state" in source
    assert "contact_forces" in source


def test_m1_teacher_initial_hold_waits_for_measured_contacts():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline" / "ame_env_wrapper.py").read_text()
    assert "torch.full_like(self._m1_teacher_age, -1)" in source
    assert "M1_TEACHER_HOLD_CONTACT_BLEND" in source


def test_m1_default_serial_sequence_preserves_diagonal_support():
    for path in (
        Path(__file__).resolve().parents[1] / "ame_baseline" / "ame_env_wrapper.py",
        Path(__file__).resolve().parents[1] / "ame_baseline" / "m1_mpc_teacher.py",
    ):
        source = path.read_text()
        assert '"0,3,2,1"' in source
