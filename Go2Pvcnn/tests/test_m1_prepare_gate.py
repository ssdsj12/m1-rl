"""Pre-lift gate contract: no timer-only advancement or cross-row resets."""
import importlib.util
from pathlib import Path

import pytest
import torch


def load_gate():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_prepare_gate.py'
    assert path.exists(), 'contact-driven prepare gate has not been implemented'
    spec = importlib.util.spec_from_file_location('m1_prepare_gate', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PrepareGate(2)


def observation(frame, **changes):
    args = dict(
        episode=torch.tensor([0, 0]), obstacle=torch.tensor([7, 7]),
        leg=torch.tensor([0, 3]), step=torch.tensor([frame, frame]),
        force=torch.full((2, 4), 20.), tilt=torch.zeros(2, 2),
        tilt_rate=torch.zeros(2, 2), margin=torch.full((2,), .03),
        ik_valid=torch.ones(2, dtype=torch.bool),
        collision=torch.zeros(2, dtype=torch.bool),
    )
    args.update(changes)
    return args


def test_five_consecutive_frames_required():
    gate = load_gate()
    for step in range(4):
        assert not gate.update(**observation(step)).any()
    assert gate.update(**observation(4)).all()


@pytest.mark.parametrize('field,value', [
    ('force', [[20., 0., 20., 20.], [20., 20., 20., 20.]]),
    ('force', [[0., 20., 20., 20.], [20., 20., 20., 20.]]),
    ('tilt', [[.16, 0.], [0., 0.]]),
    ('tilt_rate', [[0., .21], [0., 0.]]),
    ('margin', [.019, .03]),
    ('margin', [float('nan'), .03]),
    ('ik_valid', [False, True]),
])
def test_unsafe_row_resets_without_resetting_other_env(field, value):
    gate = load_gate()
    for step in range(4):
        gate.update(**observation(step))
    assert gate.update(**observation(4, **{field: torch.tensor(value)})).tolist() == [False, True]
    assert gate.update(**observation(5)).tolist() == [False, True]


@pytest.mark.parametrize('field,value', [
    ('episode', [1, 0]), ('obstacle', [8, 7]), ('leg', [1, 3]),
    ('step', [6, 4]),
])
def test_identity_or_sample_gap_restarts_only_affected_row(field, value):
    gate = load_gate()
    for step in range(4):
        gate.update(**observation(step))
    assert gate.update(**observation(4, **{field: torch.tensor(value)})).tolist() == [False, True]


def test_repeated_sample_does_not_accumulate_readiness():
    gate = load_gate()
    for _ in range(10):
        assert not gate.update(**observation(0)).any()


def test_collision_poison_survives_leg_change_until_new_event():
    gate = load_gate()
    gate.update(**observation(0, collision=torch.tensor([True, False])))
    for step in range(1, 8):
        result = gate.update(**observation(step, leg=torch.tensor([1, 3])))
        assert not result[0]
    for step in range(8, 13):
        result = gate.update(**observation(step, obstacle=torch.tensor([8, 7])))
    assert result.all()


def test_unknown_obstacle_is_not_accepted():
    gate = load_gate()
    for step in range(8):
        assert not gate.update(**observation(step, obstacle=torch.tensor([-1, -1]))).any()


def test_nonfinite_force_rejected_even_when_selected():
    gate = load_gate()
    for step in range(8):
        value = observation(step)
        value['force'][0, 0] = float('nan')
        assert not gate.update(**value)[0]


@pytest.mark.parametrize('field,value', [
    ('force', torch.ones(2, 1)), ('margin', torch.ones(2, 1)),
    ('leg', torch.tensor([0., 3.])), ('ik_valid', torch.tensor([1, 1])),
])
def test_malformed_observation_rejected_before_state_mutation(field, value):
    gate = load_gate()
    for frame in range(4):
        gate.update(**observation(frame))
    with pytest.raises(ValueError):
        gate.update(**observation(4, **{field: value}))
    assert gate.update(**observation(4)).all()
