from pathlib import Path

import pytest
import torch

from ame_baseline.m1_probe_metrics import (
    crossing_attempt_mask,
    measured_swing_leg_count,
    strict_target_leg_mismatch_mask,
)


def test_measured_swing_leg_count_detects_two_unloaded_elevated_legs():
    wheel_center_z = torch.tensor([[0.16, 0.18, 0.10, 0.20]])
    wheel_force_norm = torch.tensor([[0.0, 4.0, 35.0, 0.0]])

    count = measured_swing_leg_count(
        wheel_center_z,
        wheel_force_norm,
        ground_z=torch.tensor([0.0]),
        wheel_radius=0.10,
        minimum_lift_m=0.02,
    )

    assert count.tolist() == [3]


def test_measured_swing_leg_count_accepts_exactly_one_lifted_unloaded_leg():
    wheel_center_z = torch.tensor([[0.11, 0.16, 0.10, 0.10]])
    wheel_force_norm = torch.tensor([[0.0, 0.0, 35.0, 40.0]])

    count = measured_swing_leg_count(
        wheel_center_z,
        wheel_force_norm,
        ground_z=torch.tensor([0.0]),
        wheel_radius=0.10,
        minimum_lift_m=0.02,
    )

    assert count.tolist() == [1]


def test_measured_swing_leg_count_rejects_nonfinite_sensor_values():
    with pytest.raises(ValueError, match="finite"):
        measured_swing_leg_count(
            torch.tensor([[0.2, 0.1, 0.1, 0.1]]),
            torch.tensor([[float("nan"), 0.0, 0.0, 0.0]]),
            ground_z=torch.tensor([0.0]),
            wheel_radius=0.10,
        )


def test_physx_probe_uses_measured_swing_count_not_action_nonzero_count():
    source = (Path(__file__).resolve().parents[1] / 'scripts/probe_m1_teacher_physx.py').read_text()

    assert 'measured_swing_leg_count(' in source
    assert '"measured_swing_leg_count": measured_swing_count' in source
    assert 'max_swing_legs = max(max_swing_legs, measured_swing_count)' in source
    assert '"max_measured_swing_leg_count": max_swing_legs' in source
    assert '"max_commanded_leg_count"' not in source
    assert 'max_swing_legs = max(max_swing_legs, 1 if selected_leg_action_max else 0)' not in source


def test_crossing_attempt_mask_excludes_recovery_failed_and_unlatched_rows():
    mask = crossing_attempt_mask(
        teacher_active=torch.tensor([True, True, True, True, False]),
        selected_leg=torch.tensor([2, 1, 1, 1, 1]),
        target_wheel=torch.tensor([0, 0, 0, -1, 0]),
        awaiting_recovery=torch.tensor([False, True, False, False, False]),
        failed=torch.tensor([False, False, True, False, False]),
    )

    assert mask.tolist() == [True, False, False, False, False]


def test_physx_probe_scopes_measured_single_swing_gate_to_crossing_attempt():
    source = (Path(__file__).resolve().parents[1] / 'scripts/probe_m1_teacher_physx.py').read_text()

    assert 'crossing_attempt_mask(' in source
    assert '"crossing_attempt_active": bool(crossing_attempt[0].item())' in source
    assert 'sample["crossing_attempt_active"]' in source


def test_strict_target_leg_mismatch_is_counted_only_during_latched_crossing():
    mismatch = strict_target_leg_mismatch_mask(
        selected_leg=torch.tensor([0, 3, 1, 3]),
        target_wheel=torch.tensor([0, 0, 2, -1]),
        awaiting_recovery=torch.tensor([False, False, True, False]),
        failed=torch.tensor([False, False, False, False]),
    )

    assert mismatch.tolist() == [False, True, False, False]


def test_physx_probe_records_target_leg_mismatch_and_rejects_misaligned_swing():
    source = (Path(__file__).resolve().parents[1] / 'scripts/probe_m1_teacher_physx.py').read_text()

    assert 'strict_target_leg_mismatch_mask(' in source
    assert '"strict_leg_target_mismatch": bool(strict_leg_mismatch[0].item())' in source
    assert '"strict_target_and_teacher_leg_aligned": (' in source
    assert 'strict_target_checked_steps > 0 and strict_target_mismatch_steps == 0' in source
