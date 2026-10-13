"""Direct flat-to-ten-centimeter course and checkpoint isolation."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace as NS

import pytest
import torch

from ame_baseline.m1_learning_curriculum import LearningCurriculumGate, curriculum_reset
from test_m1_learning_curriculum import episode


def test_three_complete_windows_promote_directly_and_final_stage_holds():
    gate = LearningCurriculumGate(2048, 'cpu', stage_sequence=(0, 3))
    assert gate.stage_sequence == (0, 3)
    for expected in (0, 0, 3):
        episode(gate)
        assert gate.stage == expected
    for _ in range(6):
        episode(gate, attempts=2, successes=2)
        assert gate.stage == 3


def test_old_episodes_excluded_and_last_pending_metrics_separate():
    gate = LearningCurriculumGate(4096, 'cpu', stage_sequence=(0, 3))
    for _ in range(3):
        episode(gate, ids=torch.arange(2048))
    assert gate.stage == 3
    episode(gate, ids=torch.arange(2048, 4096), attempts=100, successes=100)
    assert gate.window_count == gate.window_attempts == 0
    episode(gate, ids=torch.arange(10), terminated=True, attempts=2, successes=0)
    metrics = gate.metrics()
    assert metrics['last_sample_count'] == 2048.
    assert metrics['last_pass_rate'] == 1.
    assert metrics['pending_sample_count'] == 10.
    assert metrics['pending_pass_rate'] == 0.
    assert metrics['pending_strict_attempts'] == 20.
    restored = LearningCurriculumGate(4096, 'cpu', stage_sequence=(0, 3))
    restored.load_state_dict(gate.state_dict())
    assert restored.metrics() == metrics
    assert restored.steps.sum() == 0 and (restored.episode_stage == 3).all()


@pytest.mark.parametrize('sequence', [(), (1, 3), (0, 3, 3), (0, 3, 2), (0, 5),
                                     (0, -1), (False, 3), (0, 3.), '03', None])
def test_invalid_sequence_rejected(sequence):
    with pytest.raises(ValueError, match='stage_sequence'):
        LearningCurriculumGate(1, 'cpu', stage_sequence=sequence)


def test_single_stage_is_valid_and_holds():
    gate = LearningCurriculumGate(2048, 'cpu', stage_sequence=[0])
    for _ in range(4):
        episode(gate)
    assert gate.stage_sequence == (0,) and gate.stage == 0


def test_new_state_versions_sequence_and_legacy_restore_is_legacy_only():
    gate = LearningCurriculumGate(1, 'cpu', stage_sequence=(0, 3))
    state = gate.state_dict()
    assert state['version'] == 2 and state['stage_sequence'] == [0, 3]
    legacy = LearningCurriculumGate(1, 'cpu')
    old = legacy.state_dict()
    old['version'] = 1
    old.pop('stage_sequence')
    old['stage'] = 2
    legacy.load_state_dict(old)
    assert legacy.stage == 2 and legacy.stage_sequence == (0, 1, 2, 3, 4)
    with pytest.raises(ValueError):
        gate.load_state_dict(old)
    with pytest.raises(ValueError):
        legacy.load_state_dict(state)


@pytest.mark.parametrize('mutation', [
    lambda s: s.update(stage=1), lambda s: s.update(stage=True),
    lambda s: s.update(version=True), lambda s: s.update(window_error=float('nan')),
    lambda s: s.update(window_duration=float('inf')), lambda s: s.update(window_count=True),
    lambda s: s.update(window_count=2048), lambda s: s.update(window_pass=1),
    lambda s: s.update(window_successes=1), lambda s: s.update(stage_sequence=[0, 1, 3]),
    lambda s: s['last'].update(pass_rate=float('nan')), lambda s: s['last'].update(pass_rate=True),
    lambda s: s['last'].update(pass_rate=1.1), lambda s: s['last'].update(strict_success_rate=1.1),
    lambda s: s['last'].update(strict_successes=1),
])
def test_invalid_metadata_rejected_before_mutation(mutation):
    gate = LearningCurriculumGate(1, 'cpu', stage_sequence=(0, 3))
    before = gate.state_dict()
    invalid = deepcopy(before)
    mutation(invalid)
    with pytest.raises(ValueError):
        gate.load_state_dict(invalid)
    assert gate.state_dict() == before


def test_reset_selects_actual_row_three_with_eight_targets_and_seventy_fill(monkeypatch):
    from test_m1_lift_roll_authoring import setup_course
    build, kwargs = setup_course(monkeypatch)
    kwargs['layout_cfg'] = replace(kwargs['layout_cfg'], placement_strategy='m1_lift_roll')
    anchors = build(**kwargs)
    n = 2048
    origins = torch.tensor(kwargs['terrain_origins'])
    terrain = NS(terrain_origins=origins, terrain_levels=torch.zeros(n, dtype=torch.long),
                 terrain_types=torch.zeros(n, dtype=torch.long), env_origins=torch.zeros(n, 3))
    env = NS(cfg=NS(m1_learning_stage_sequence=(0, 3)), num_envs=n, device='cpu',
             max_episode_length=4, scene=NS(terrain=terrain),
             termination_manager=NS(terminated=torch.zeros(n, dtype=torch.bool),
                                    time_outs=torch.ones(n, dtype=torch.bool)))
    curriculum_reset(env, None)
    gate = env._m1_learning_gate
    for _ in range(3):
        for i in range(4):
            gate.accumulate(torch.full((n,), .3), torch.full((n,), .3),
                            torch.full((n, 3), i * .3), torch.ones(n, dtype=torch.bool), 1.)
        curriculum_reset(env, None)
    assert (terrain.terrain_levels == 3).all()
    assert (terrain.terrain_types == 0).all()
    assert (terrain.env_origins[:, 0] == 46.).all()
    row = [a for a in anchors if (a.row, a.col) == (3, 0)]
    assert sum(a.required_crossing is True for a in row) == 8
    assert sum(a.required_crossing is False for a in row) == 70
    assert all(a.target_height == .10 for a in row)
