"""Student per-control-step charges, including the real manager adapter."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
import torch

from ame_baseline.m1_collision_budget import (
    CollisionBudget, collision_budget_contract, collision_budget_cost,
    combine_collision_signals,
)


@pytest.mark.parametrize('dt', [.01, .02, .04])
def test_ten_charged_steps_exhaust_budget_independent_of_dt(dt):
    budget = CollisionBudget(2, 'cpu', dt, cost_per_step=2.)
    env = NS(step_dt=dt, _m1_collision_budget=budget)
    for step in range(10):
        env.common_step_counter = step
        snap = budget.update(torch.tensor([.001, 0.]), step)
        assert snap['cost'].tolist() == [2., 0.]
        assert snap['exhausted'].tolist() == [step == 9, False]
        assert budget.update(torch.ones(2), step) is snap
        # RewardManager applies dt exactly once to this rate.
        assert (collision_budget_cost(env) * dt).tolist() == pytest.approx([-2., 0.])
    assert snap['total'].tolist() == [20., 0.]


@pytest.mark.parametrize('value', [True, False, 0., -2., float('nan'), float('inf'), '2', [], 2j])
def test_invalid_per_step_cost_rejected(value):
    with pytest.raises(ValueError, match='cost_per_step'):
        CollisionBudget(1, 'cpu', .02, cost_per_step=value)


def test_max_union_intermittent_row_reset_and_terminal_snapshot():
    budget = CollisionBudget(2, 'cpu', .02, cost_per_step=2.)
    signal = combine_collision_signals(torch.tensor([1., .001]), torch.ones(2))
    for step in range(9):
        budget.update(signal if step % 2 == 0 else torch.tensor([1., 0.]), step)
    snap = budget.update(torch.tensor([1., 0.]), 9)
    assert snap['total'].tolist() == [20., 10.]
    assert snap['exhausted'].tolist() == [True, False]
    budget.reset(torch.tensor([0]))
    assert budget.total.tolist() == [0., 10.]
    assert snap['total'].tolist() == [20., 10.]
    assert budget.update(torch.zeros(2), 9) is snap
    assert budget.update(torch.zeros(2), 10)['total'].tolist() == [0., 10.]


def test_clips_last_cost_and_preserves_raw_signal_after_exhaustion():
    from ame_baseline.m1_strict_crossing import strict_collision_from_reward_terms
    budget = CollisionBudget(1, 'cpu', .02, cost_per_step=7.)
    assert [budget.update(torch.ones(1), step)['cost'].item() for step in range(4)] == [7., 7., 6., 0.]
    budget.reset([0])
    veto = strict_collision_from_reward_terms(torch.zeros(1, 1), ['collision_budget_cost'],
                                              collision_signal=budget.snapshot['signal'])
    assert veto.tolist() == [True]


def test_contract_describes_actual_cost_and_retains_legacy_exactly():
    from ame_baseline.m1_teacher_profile import student_training_contract
    legacy = dict(version=1, rate_per_s=5., episode_budget=20., combination='max',
                  immediate_reset=False, budget_terminal_extra_cost=0.,
                  other_failure_cost=20., intermittent='retain_until_reset')
    assert collision_budget_contract() == legacy
    assert CollisionBudget(1, 'cpu', .02).contract == legacy
    budget = CollisionBudget(1, 'cpu', .02, cost_per_step=2.)
    assert budget.contract == student_training_contract()['collision_budget']
    budget.contract['cost_per_step'] = 123.
    assert budget.contract['cost_per_step'] == 2.
    assert CollisionBudget(1, 'cpu', .02, cost_per_step=7.).contract['cost_per_step'] == 7.


def manager_module(monkeypatch):
    # Only Isaac's base class is replaced; the real adapter computes/charges.
    class ManagerTermBase:
        def __init__(self, cfg, env):
            self._env = env
    monkeypatch.setitem(sys.modules, 'isaaclab.managers', NS(ManagerTermBase=ManagerTermBase))
    name = 'ame_baseline._student_budget_terms_test'
    path = Path(__file__).parents[1] / 'ame_baseline/m1_collision_budget_terms.py'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_profile_to_manager_and_gate_consumes_actual_settings(monkeypatch):
    from ame_baseline import m1_mixed_course
    from ame_baseline.m1_teacher_profile import configure_teacher_student_profile, require_teacher_student_backend
    from ame_baseline.m1_learning_curriculum import _gate
    monkeypatch.delenv('M1_FIXED_ABAD', raising=False)
    monkeypatch.delenv('M1_FIXED_WHEEL_SPEED_M_S', raising=False)
    monkeypatch.setitem(sys.modules, 'ame_baseline.m1_ame_actions', NS(M1AmeActionsCfg=lambda: NS()))
    monkeypatch.setattr(m1_mixed_course, 'configure_flat_first_terrain', lambda cfg: None)
    cfg = configure_teacher_student_profile(NS(commands=NS(base_velocity=NS(ranges=NS(), limit_ranges=NS())), curriculum=NS()))
    env = NS(cfg=cfg, num_envs=3, device='cpu', step_dt=.02, common_step_counter=0)
    module = manager_module(monkeypatch)
    calls = []
    def geometry(env, **kwargs):
        calls.append(env.common_step_counter)
        return torch.tensor([.001, 0., 0.])
    monkeypatch.setattr(module, 'm1_obstacle_collision_penalty', geometry)
    monkeypatch.setattr(module, 'm1_non_support_obstacle_contact', lambda env: torch.tensor([1., 0., 0.]))
    manager = module.CollisionBudgetTermination(NS(), env)
    gate = _gate(env)
    require_teacher_student_backend(env)
    assert gate.stage_sequence == (0, 3)
    assert gate.state_dict()['stage_sequence'] == [0, 3]
    for step in range(10):
        env.common_step_counter = step
        assert manager(env).tolist() == [step == 9, False, False]
        assert manager(env).tolist() == [step == 9, False, False]
    assert calls == list(range(10))
    env.termination_manager = NS(terminated=torch.tensor([True, True, False]))
    from ame_baseline.m1_ame_rewards import m1_failure_termination_penalty
    terminal = m1_failure_termination_penalty(env) * -20. * env.step_dt
    assert terminal.tolist() == [0., -20., 0.]
    assert (collision_budget_cost(env) * env.step_dt + terminal).tolist() == [-2., -20., 0.]
    manager.reset([0])
    assert env._m1_collision_budget.snapshot['total'].tolist() == [20., 0., 0.]


@pytest.mark.parametrize('budget', [10., 30., True, float('nan'), '20'])
def test_manager_rejects_mismatched_declared_budget(monkeypatch, budget):
    env = NS(cfg=NS(m1_collision_cost_per_step=2., m1_collision_budget=budget),
             num_envs=1, device='cpu', step_dt=.02)
    with pytest.raises(ValueError, match='budget'):
        manager_module(monkeypatch).CollisionBudgetTermination(NS(), env)


def test_manager_without_profile_keeps_legacy(monkeypatch):
    env = NS(cfg=NS(), num_envs=1, device='cpu', step_dt=.02)
    budget = manager_module(monkeypatch).CollisionBudgetTermination(NS(), env).budget
    assert budget.contract == collision_budget_contract()
    assert budget.update(torch.ones(1), 0)['cost'].item() == pytest.approx(.1)
