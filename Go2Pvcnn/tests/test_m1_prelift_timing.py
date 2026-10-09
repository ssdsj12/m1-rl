import ast
from pathlib import Path
import torch
from types import SimpleNamespace


def arc(progress, early=True):
    source = Path(__file__).with_name('teacher_before.py')
    if not source.exists():
        source = Path(__file__).resolve().parents[1] / 'ame_baseline/m1_mpc_teacher.py'
    tree = ast.parse(source.read_text())
    branch = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                  and 'M1_TEACHER_PRELIFT' in ast.unparse(n.test))
    values = dict(torch=torch, phase_progress=torch.tensor(progress),
                  lift_amplitude=1., advance_distance=1.,
                  os=SimpleNamespace(environ={'M1_TEACHER_EARLY_TRAVERSE': str(int(early))}))
    exec(compile(ast.Module(body=branch.body, type_ignores=[]), '<arc>', 'exec'), values)
    return values['lift'], values['advance']


def test_forward_target_finishes_before_descent():
    height, forward = arc([.70, .75, .875, 1.])
    assert torch.allclose(forward, torch.ones_like(forward)), forward
    assert height[-1] == 0


def test_no_forward_motion_during_initial_lift():
    height, forward = arc([0., .125, .25, .30])
    assert (forward == 0).all()
    assert torch.all(height[1:] >= height[:-1])


def test_traverse_maintains_full_target_height():
    height, forward = arc([.30, .40, .50, .60, .70])
    assert torch.allclose(height, torch.ones_like(height))
    assert torch.all(forward[1:] >= forward[:-1])


def test_failed_physics_experiment_does_not_change_default():
    _, forward = arc([.70], early=False)
    assert torch.allclose(forward, torch.tensor([0.60641399]))
