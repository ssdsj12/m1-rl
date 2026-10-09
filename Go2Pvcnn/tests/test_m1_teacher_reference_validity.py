"""A safety hold may execute, but must not become a valid imitation label."""
import ast
from pathlib import Path
from types import SimpleNamespace
import torch


ROOT = Path(__file__).parents[1]


def test_runner_does_not_learn_from_executable_invalid_hold():
    path = ROOT / 'rsl_rl/rsl_rl/runners/on_policy_runner.py'
    tree = ast.parse(path.read_text())
    block = next(n.body for n in ast.walk(tree) if isinstance(n, ast.If)
                 and any(isinstance(x, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'use_teacher' for t in x.targets) for x in n.body))
    start = next(i for i,n in enumerate(block) if isinstance(n, ast.Assign)
                 and ast.unparse(n.targets[0]) == 'teacher_valid'
                 and isinstance(n.value, ast.BinOp))
    end = next(i for i,n in enumerate(block) if isinstance(n, ast.Assign)
               and ast.unparse(n.targets[0]) == 'use_teacher') + 1
    transition = SimpleNamespace()
    actor = SimpleNamespace(env=SimpleNamespace(_m1_teacher_reference_valid=torch.tensor([True, False])),
                            alg=SimpleNamespace(transition=transition))
    scope = dict(self=actor, torch=torch, actions=torch.zeros(2,16),
                 teacher_valid=torch.tensor([True,True]), teacher_action_finite=torch.tensor([True,True]), ratio=1.)
    exec(compile(ast.Module(body=block[start:end],type_ignores=[]), str(path), 'exec'), scope)
    targets = {'self.alg.transition.imitation_weight', 'self.alg.transition.plan_valid'}
    statements = [n for n in block if isinstance(n,ast.Assign) and ast.unparse(n.targets[0]) in targets]
    exec(compile(ast.Module(body=statements,type_ignores=[]),str(path),'exec'), scope)
    assert scope['use_teacher'].tolist() == [True, True], 'safety control ownership must be retained'
    assert transition.imitation_weight.tolist() == [1.,0.], 'fallback hold is not a valid teacher target'
    assert transition.plan_valid.tolist() == [1.,0.]


def test_wrapper_keeps_pre_safety_reference_certificate():
    tree = ast.parse((ROOT/'ame_baseline/ame_env_wrapper.py').read_text())
    method = next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='get_mpc_teacher_action')
    assignments = [n for n in ast.walk(method) if isinstance(n,ast.Assign)]
    snapshots = [n for n in assignments if any(ast.unparse(t)=='reference_valid' for t in n.targets)]
    assert snapshots, 'snapshot raw IK/reference validity before safety/fallback can re-enable control'
    safety = next(n for n in ast.walk(method) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='apply_m1_teacher_safety')
    assert snapshots[0].lineno < safety.lineno
    assert any(any(ast.unparse(t)=='self._m1_teacher_reference_valid' for t in n.targets) for n in assignments)
