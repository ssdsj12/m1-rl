import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from test_m1_fixed_wheel_runtime import runtime
from ame_baseline.m1_fixed_abad import fixed_abad_contract
from ame_baseline.m1_fixed_wheel_checkpoint import fixed_wheel_contract

SCRIPTS=Path(__file__).parents[1]/'scripts'

def evaluation(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec=importlib.util.spec_from_file_location('fixed_abad_eval_test',SCRIPTS/'evaluate_m1_ame.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    assert hasattr(mod,'configure_evaluation_action_mode')
    return mod

def config():
    return NS(action_dim=16,m1_fixed_abad=False,m1_fixed_wheel_speed_m_s=None,
        actions=NS(),commands=NS(base_velocity=NS(ranges=NS(),limit_ranges=NS())),curriculum=NS())

def test_evaluation_selects_mode_before_env_creation(runtime,monkeypatch):
    monkeypatch.delenv('M1_FIXED_ABAD',raising=False);monkeypatch.delenv('M1_FIXED_WHEEL_SPEED_M_S',raising=False)
    mod=evaluation(monkeypatch);cfg=config()
    mod.configure_evaluation_action_mode(cfg,dict(ame_num_actions=8,m1_action_contract=fixed_abad_contract(.3)))
    assert cfg.action_dim==8 and cfg.m1_fixed_abad
    cfg=config();mod.configure_evaluation_action_mode(cfg,dict(ame_num_actions=12,m1_action_contract=fixed_wheel_contract(.3)))
    assert cfg.action_dim==12 and not cfg.m1_fixed_abad
    src=(SCRIPTS/'evaluate_m1_ame.py').read_text()
    assert src.index('configure_evaluation_action_mode(cfg, checkpoint)')<src.index('env = ManagerBasedRLEnv(cfg=cfg)')

@pytest.mark.parametrize('bad',['flag','speed','unknown','missing','angle'])
def test_conflicting_mode_rejected(runtime,monkeypatch,bad):
    monkeypatch.delenv('M1_FIXED_ABAD',raising=False);monkeypatch.delenv('M1_FIXED_WHEEL_SPEED_M_S',raising=False)
    mod=evaluation(monkeypatch);cp=dict(ame_num_actions=8,m1_action_contract=fixed_abad_contract(.3))
    if bad=='flag':monkeypatch.setenv('M1_FIXED_ABAD','0')
    if bad=='speed':monkeypatch.setenv('M1_FIXED_WHEEL_SPEED_M_S','.4')
    if bad=='unknown':cp['m1_action_contract']['mode']='guess'
    if bad=='missing':cp.pop('m1_action_contract')
    if bad=='angle':cp['m1_action_contract']['fixed_joint_targets'][0]=.2
    with pytest.raises(ValueError):mod.configure_evaluation_action_mode(config(),cp)

def test_eval_control_loop_has_no_extra_physics_update():
    tree=ast.parse((SCRIPTS/'evaluate_m1_ame.py').read_text())
    calls=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)]
    assert 'wrapped.step' in calls and 'simulation_app.update' not in calls

def test_training_header_exposes_fixed_abad():
    assert 'fixed_abad=' in (SCRIPTS/'train_m1_cross_large_complex_ame.py').read_text()
