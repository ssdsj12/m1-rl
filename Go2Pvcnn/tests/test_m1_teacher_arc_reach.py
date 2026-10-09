import torch
import pytest
import re
from pathlib import Path


@pytest.mark.parametrize('leg', range(4))
def test_m1_teacher_serial_arc_keeps_ik_valid_through_touchdown(monkeypatch, leg):
    from ame_baseline.m1_ame_contract import (
        M1_TRAINING_JOINT_POS,
        M1_TRAINING_ROOT_Z_M,
        m1_action_targets,
    )
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action
    from extension.parallelism.m1_kinematics import (
        M1_ASSET_JOINT_NAMES,
        M1_PLANNER_JOINT_NAMES,
        M1_WHEEL_RADIUS_M,
        m1_fk,
    )
    from extension.parallelism.rl_adapter import resolve_named_indices

    wrapper = (Path(__file__).resolve().parents[1] / 'scripts/run_m1_train_with_placeholder.sh').read_text()
    for name, default_value in re.findall(r'export (M1_TEACHER_\w+)="\$\{[^:]+:-([^}]+)\}"', wrapper):
        monkeypatch.setenv(name, default_value)
    monkeypatch.setenv("M1_TEACHER_SERIAL_FORCE", "1")
    monkeypatch.setenv("M1_TEACHER_USE_PLANNER_FOOT_TARGET", "0")
    monkeypatch.setenv("M1_TEACHER_FOOT_TRAJECTORY", "1")
    monkeypatch.setenv("M1_TEACHER_PRELIFT", "1")
    monkeypatch.setenv("M1_TEACHER_REPROJECT_STANCE", "1")

    planner_cols = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    default = torch.tensor([M1_TRAINING_JOINT_POS], dtype=torch.float32)
    current = default.clone()
    root = torch.tensor([[0.0, 0.0, M1_TRAINING_ROOT_Z_M]])
    rpy = torch.zeros((1, 3))
    hold = m1_fk(root, rpy, current[:, planner_cols]).foot_pos_w
    reference = {
        "joint_angles": current[:, planner_cols].clone(),
        "valid_mask": torch.ones(1, dtype=torch.bool),
        "contact_state": torch.ones((1, 4), dtype=torch.bool),
        "serial_leg_override": torch.tensor([leg]),
        "phase_index": torch.tensor([0]),
        "m1_root_pos_w": root,
        "m1_root_rpy_w": rpy,
        "hold_joint_angles": current[:, planner_cols].clone(),
        "hold_foot_pos_w": hold.clone(),
    }
    bottoms = []
    for phase in range(128):
        reference["phase_index"] = torch.tensor([phase])
        action, valid = reference_to_m1_action(reference, default, current_joint_pos=current)
        assert bool(valid.item()), f"teacher invalid at phase {phase}"
        current = m1_action_targets(action, default)
        feet = m1_fk(root, rpy, current[:, planner_cols]).foot_pos_w
        bottoms.append(float(feet[0, leg, 2] - M1_WHEEL_RADIUS_M))
    assert max(bottoms) >= 0.15
    assert abs(bottoms[-1]) < 0.002, 'decoded foot must return to ground'
