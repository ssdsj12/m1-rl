"""Collision budget: hand-derived charges, not source-string assertions."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
import torch


def budget_module():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_collision_budget.py'
    assert path.exists(), 'missing collision budget implementation'
    spec = importlib.util.spec_from_file_location('budget_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_contact_four_seconds_and_no_duplicate_step():
    m = budget_module(); b = m.CollisionBudget(2, 'cpu', .02)
    for step in range(199):
        snap = b.update(torch.tensor([1.,0.]), step)
        again = b.update(torch.ones(2), step)
        assert torch.equal(snap['total'], again['total'])
        assert not snap['exhausted'].any()
    snap = b.update(torch.tensor([1.,0.]), 199)
    assert snap['exhausted'].tolist() == [True,False]
    assert snap['total'].tolist() == [20.,0.]
    assert snap['cost'][0] == pytest.approx(.1)


def test_intermittent_collision_keeps_budget_and_reset_is_row_local():
    b = budget_module().CollisionBudget(2,'cpu',.02)
    b.update(torch.tensor([1.,.5]),0)
    snap=b.update(torch.tensor([0.,1.]),1)
    assert snap['total'].tolist() == pytest.approx([.1,.15])
    b.reset(torch.tensor([0]))
    assert snap['total'].tolist() == pytest.approx([.1,.15])
    assert b.update(torch.zeros(2),2)['total'].tolist() == pytest.approx([0.,.15])


def test_last_charge_clipped_to_budget():
    b=budget_module().CollisionBudget(1,'cpu',.03)
    for step in range(134): snap=b.update(torch.ones(1),step)
    assert snap['total'].item() == 20.
    assert snap['cost'].item() == pytest.approx(.05)
    assert b.update(torch.ones(1),134)['cost'].item() == 0.


@pytest.mark.parametrize('dt',[0.,-1.,float('nan'),float('inf')])
def test_invalid_dt_rejected(dt):
    with pytest.raises(ValueError): budget_module().CollisionBudget(1,'cpu',dt)


def test_invalid_signal_is_conservative_and_finite():
    b=budget_module().CollisionBudget(4,'cpu',.02)
    snap=b.update(torch.tensor([float('nan'),float('inf'),-1.,2.]),0)
    assert snap['cost'].tolist() == pytest.approx([.1,.1,0.,.1])


def test_combined_signals_max_not_sum():
    m=budget_module()
    assert m.combine_collision_signals(torch.tensor([1.,.2,0.]),torch.tensor([1.,.7,.4])).tolist() == pytest.approx([1.,.7,.4])


def test_reward_reads_snapshot_without_mutation_after_reset():
    m=budget_module(); b=m.CollisionBudget(2,'cpu',.02)
    env=SimpleNamespace(step_dt=.02,common_step_counter=1,_m1_collision_budget=b)
    b.update(torch.tensor([1.,0.]),1)
    b.reset(torch.tensor([0]))
    assert m.collision_budget_cost(env).tolist() == pytest.approx([-5.,0.])
    assert m.collision_budget_cost(env).tolist() == pytest.approx([-5.,0.])


def test_failure_penalty_excludes_exhausted_and_timeout_only():
    m=budget_module(); b=m.CollisionBudget(3,'cpu',4.)
    b.update(torch.tensor([1.,0.,0.]),7)
    env=SimpleNamespace(step_dt=4.,common_step_counter=7,_m1_collision_budget=b,
        termination_manager=SimpleNamespace(terminated=torch.tensor([True,True,False])))
    from ame_baseline.m1_ame_rewards import m1_failure_termination_penalty
    actual=m1_failure_termination_penalty(env)*(-20)*4.
    assert actual.tolist() == [0.,-20.,0.]


def test_stale_reward_snapshot_rejected():
    m=budget_module(); b=m.CollisionBudget(1,'cpu',.02)
    b.update(torch.ones(1),1)
    env=SimpleNamespace(step_dt=.02,common_step_counter=2,_m1_collision_budget=b)
    with pytest.raises(RuntimeError,match='snapshot'): m.collision_budget_cost(env)


def test_new_contract_rejects_pre_budget_checkpoint():
    from ame_baseline.m1_ame_contract import m1_training_contract, validate_training_contract
    contract=m1_training_contract(fixed_abad=True)
    assert contract.get('collision_budget',{}).get('episode_budget') == 20.
    assert contract['obstacle_collision_reset'] is False
    old=dict(contract,version=3,obstacle_collision_reset=True)
    old.pop('collision_budget',None)
    with pytest.raises(ValueError,match='training contract'):
        validate_training_contract({'m1_training_contract':old},contract)


def test_raw_collision_survives_exhausted_cost_and_reset_for_success_veto():
    from ame_baseline.m1_strict_crossing import strict_collision_from_reward_terms
    m=budget_module();b=m.CollisionBudget(2,'cpu',4.)
    b.update(torch.tensor([1.,0.]),0)
    snap=b.update(torch.tensor([1.,0.]),1)
    b.reset(torch.tensor([0]))
    assert snap['cost'].tolist()==[0.,0.]
    assert 'signal' in snap,'missing raw collision signal for strict success'
    actual=strict_collision_from_reward_terms(torch.zeros(2,1),['collision_budget_cost'],collision_signal=snap['signal'])
    assert actual.tolist()==[True,False]


def test_native_gate_rejects_unstripped_positive_collision_reward():
    path=Path(__file__).parents[1]/'scripts/probe_m1_collision_budget.py'
    spec=importlib.util.spec_from_file_location('native_probe_gate',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert hasattr(module,'check_collision_final_reward'),'missing final reward gate'
    with pytest.raises(AssertionError):
        module.check_collision_final_reward(torch.tensor([.2]),torch.tensor([.2]),
            {'positive':torch.tensor([.3]),'cost':torch.tensor([-.1])},torch.tensor([1.]))
    module.check_collision_final_reward(torch.tensor([.2]),torch.tensor([-.1]),
        {'positive':torch.tensor([.3]),'cost':torch.tensor([-.1])},torch.tensor([1.]))
