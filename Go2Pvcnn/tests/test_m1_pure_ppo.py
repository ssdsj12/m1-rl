import ast
from pathlib import Path
from types import SimpleNamespace


def test_m1_train_cfg_cannot_reenable_imitation(monkeypatch):
    monkeypatch.setenv('M1_IMITATION_COEF', '100')
    from ame_baseline.m1_ame_train_cfg import get_m1_ame_train_cfg
    cfg = get_m1_ame_train_cfg()
    assert cfg['algorithm']['class_name'] == 'PPO'
    assert cfg['algorithm']['imitation_coef'] == 0.0
    assert cfg['enable_mpc_teacher'] is False


def test_runner_disabled_teacher_is_not_even_looked_up():
    class Env:
        @property
        def get_mpc_teacher_action(self):
            raise AssertionError('teacher must not be touched in pure PPO')
    path = Path(__file__).parents[1] / 'rsl_rl/rsl_rl/runners/on_policy_runner.py'
    tree = ast.parse(path.read_text())
    statement = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'get_teacher' for t in n.targets))
    scope = {'self': SimpleNamespace(env=Env(), cfg={'enable_mpc_teacher': False})}
    exec(compile(ast.Module(body=[statement], type_ignores=[]), str(path), 'exec'), scope)
    assert scope['get_teacher'] is None


def test_entry_no_longer_attaches_planner_or_teacher_defaults():
    source = (Path(__file__).parents[1] / 'scripts/train_m1_cross_large_complex_ame.py').read_text()
    assert 'attach_trajectory_manager_if_enabled' not in source
    assert 'apply_m1_runtime_defaults' not in source


def test_env_disables_planner_at_final_configuration():
    source = (Path(__file__).parents[1] / 'ame_baseline/m1_ame_env_cfg.py').read_text()
    tree = ast.parse(source)
    assignments = {n.targets[0].attr: n.value.value for n in ast.walk(tree)
                   if isinstance(n, ast.Assign) and len(n.targets) == 1
                   and isinstance(n.targets[0], ast.Attribute) and isinstance(n.value, ast.Constant)}
    assert assignments['planner_owned_reference_cache'] is False
    assert assignments['use_batched_reference_trajectory'] is False


def test_crossing_proxy_does_not_depend_on_disabled_teacher_clock():
    source = (Path(__file__).parents[1] / 'ame_baseline/ame_env_wrapper.py').read_text()
    tree = ast.parse(source)
    gates = [n for n in ast.walk(tree) if isinstance(n, ast.AugAssign)
             and isinstance(n.target, ast.Name) and n.target.id == 'crossing_complete']
    assert not any(isinstance(n, ast.Attribute) and n.attr == '_m1_teacher_age'
                   for gate in gates for n in ast.walk(gate))
