import ast
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]

def load_functions(path, names):
    tree = ast.parse((ROOT / path).read_text())
    tree.body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    scope = {'torch': torch}
    exec(compile('from __future__ import annotations\n' + ast.unparse(tree), str(path), 'exec'), scope)
    return scope

def manager(fail):
    failure = torch.tensor(fail, dtype=torch.bool)
    timeout = ~failure
    return NS(terminated=failure, time_outs=timeout, active_terms=['bad_orientation', 'time_out'],
              get_term=lambda name: {'bad_orientation': failure, 'time_out': timeout}[name])

@pytest.mark.parametrize('dt', [0.02, 0.01])
def test_failure_cost_is_once_and_dt_independent(dt):
    fn = load_functions('ame_baseline/m1_ame_rewards.py', ['m1_failure_termination_penalty'])['m1_failure_termination_penalty']
    env = NS(termination_manager=manager([True, False]), step_dt=dt)
    torch.testing.assert_close(fn(env) * -20 * dt, torch.tensor([-20., 0.]))

def test_real_termination_interface_is_used():
    fn = load_functions('go2_pvcnn/mdp/curriculums.py', ['_env_bool_buffer'])['_env_bool_buffer']
    env = NS(termination_manager=manager([True, False]), num_envs=2)
    assert fn(env, 'bad_orientation', device='cpu').tolist() == [True, False]
    assert fn(env, 'time_out', device='cpu').tolist() == [False, True]

def test_timeout_and_failure_on_same_step_still_penalized():
    fn = load_functions('ame_baseline/m1_ame_rewards.py', ['m1_failure_termination_penalty'])['m1_failure_termination_penalty']
    mgr = manager([True, False])
    mgr.time_outs[:] = True
    torch.testing.assert_close(fn(NS(termination_manager=mgr, step_dt=.02)) * -.4, torch.tensor([-20., 0.]))

def test_missing_optional_termination_is_false():
    fn = load_functions('go2_pvcnn/mdp/curriculums.py', ['_env_bool_buffer'])['_env_bool_buffer']
    assert not fn(NS(termination_manager=manager([True, False]), num_envs=2), 'base_contact', device='cpu').any()

@pytest.mark.parametrize('fail,expected', [([True]*9+[False], .1), ([False]*10, .3)])
def test_population_success_and_failure_drive_curriculum(fail, expected):
    scope = load_functions('go2_pvcnn/mdp/curriculums.py', ['lin_vel_cmd_levels', '_env_bool_buffer'])
    ranges = NS(lin_vel_x=(-.2,.2), lin_vel_y=(-.2,.2))
    command = NS(cfg=NS(ranges=ranges, limit_ranges=NS(lin_vel_x=(-1.,1.), lin_vel_y=(-.5,.5))))
    env = NS(device='cpu', num_envs=10, common_step_counter=1000, max_episode_length=1000,
             max_episode_length_s=20., episode_length_buf=torch.full((10,),1000),
             termination_manager=manager(fail),
             command_manager=NS(get_term=lambda _: command),
             reward_manager=NS(get_term_cfg=lambda _: NS(weight=1.5), _episode_sums={'track_lin_vel_xy':torch.full((10,),30.)}))
    scope['lin_vel_cmd_levels'](env, torch.arange(10), require_success=True)
    assert ranges.lin_vel_x[1] == pytest.approx(expected)
    # Calls during the same decision interval cannot advance again.
    scope['lin_vel_cmd_levels'](env, torch.arange(10), require_success=True)
    assert ranges.lin_vel_x[1] == pytest.approx(expected)
