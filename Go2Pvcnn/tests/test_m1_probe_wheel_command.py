"""Exercise the actual probe assignment without importing Isaac Sim."""
from pathlib import Path

import torch


def test_probe_preserves_wrapper_teacher_wheel_action():
    path = Path(__file__).resolve().parents[1] / 'scripts/probe_m1_teacher_physx.py'
    source = path.read_text()
    assert 'Preserve the teacher wheel action' in source
    assert 'full_like(action[:, 3::4], probe_speed)' not in source
    assert 'gate_probe_invalid_wheel_actions(' in source

    # A transient invalid MPC frame must not zero the reduced wheel drive
    # while the serial crossing teacher still owns the action. Invalid rows
    # outside that teacher phase remain fail-closed.
    from ame_baseline.m1_teacher_phase import gate_probe_invalid_wheel_actions
    action = torch.zeros((2, 16))
    wheel_cols = (3, 7, 11, 15)
    action[:, wheel_cols] = torch.tensor([0.06, 0.20, 0.20, 0.20])
    gated = gate_probe_invalid_wheel_actions(
        action,
        valid=torch.tensor([False, False]),
        teacher_active=torch.tensor([True, False]),
        wheel_cols=wheel_cols,
    )
    assert torch.equal(gated[0, list(wheel_cols)], action[0, list(wheel_cols)])
    assert torch.equal(gated[1, list(wheel_cols)], torch.zeros(4))
