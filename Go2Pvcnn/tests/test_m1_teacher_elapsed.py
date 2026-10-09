"""Exercise the production expiry block with a stalled touchdown phase."""
import torch
from ame_baseline.ame_env_wrapper import _advance_m1_teacher_phase


def test_stalled_phase_still_expires():
    active = torch.tensor([True, True])
    age = torch.tensor([31, 31])
    elapsed = torch.tensor([0, 0])
    for _ in range(257):
        active, age, elapsed = _advance_m1_teacher_phase(
            active, age, elapsed,
            handoff_ready=torch.tensor([False, False]),
            max_steps=256, phase_block=32,
        )
    assert not active.any(), 'frozen phase bypassed hard expiry'
    assert age.tolist() == [0, 0]


def test_stalled_phase_does_not_force_handoff_without_support():
    active = torch.tensor([True])
    age = torch.tensor([3])
    elapsed = torch.tensor([3])
    active, age, elapsed = _advance_m1_teacher_phase(
        active, age, elapsed,
        handoff_ready=torch.tensor([False]), max_steps=64, phase_block=4,
        handoff_grace=2,
    )
    assert active.item()
    assert age.item() == 3
    active, age, elapsed = _advance_m1_teacher_phase(
        active, age, elapsed,
        handoff_ready=torch.tensor([False]), max_steps=64, phase_block=4,
        handoff_grace=2,
    )
    assert age.item() == 3


def test_timeout_does_not_switch_without_full_support_polygon():
    active = torch.tensor([True])
    age = torch.tensor([3])
    elapsed = torch.tensor([3])
    active, age, elapsed = _advance_m1_teacher_phase(
        active, age, elapsed,
        handoff_ready=torch.tensor([False]),
        support_ready=torch.tensor([False]),
        max_steps=64, phase_block=4, handoff_grace=2,
    )
    assert active.item()
    assert age.item() == 3
