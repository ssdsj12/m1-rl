import ast
import os
from pathlib import Path
from types import SimpleNamespace
import torch
import pytest


@pytest.mark.parametrize('slow,expected', [('0', .015), ('1', .010)])
def test_runner_preserves_teacher_phase_wheel_commands(monkeypatch, slow, expected):
    source = Path(__file__).with_name('on_policy_runner.py')
    if not source.exists():
        source = Path(__file__).resolve().parents[1] / 'rsl_rl/rsl_rl/runners/on_policy_runner.py'
    tree = ast.parse(source.read_text())
    branch = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                  and 'M1_TEACHER_FORWARD_WHEELS' in ast.unparse(n.test))
    monkeypatch.setenv('M1_TEACHER_PHASE_BLOCK', '8')
    monkeypatch.setenv('M1_TEACHER_SLOW_APPROACH', slow)
    monkeypatch.setenv('M1_TEACHER_APPROACH_SPEED', '.010')
    actions = torch.zeros(1, 16)
    teacher = torch.zeros_like(actions)
    teacher[:, 3::4] = .015
    mask = torch.ones(16, dtype=torch.bool); mask[3::4] = False
    # Wrapper has advanced age after computing the command. Recomputing
    # phase from this newer age must not accelerate the wheels.
    env = SimpleNamespace(_m1_teacher_age=torch.tensor([6]),
        get_obstacle_presence=lambda: (torch.tensor([True]), torch.tensor([False])),
        unwrapped=SimpleNamespace(command_manager=SimpleNamespace(
            get_command=lambda _: torch.tensor([[.10, 0., 0.]]))))
    values = dict(torch=torch, os=os, self=SimpleNamespace(env=env),
                  actions=actions, teacher_action=teacher,
                  teacher_blended=actions.clone(), leg_mask=mask)
    exec(compile(ast.Module(body=branch.body, type_ignores=[]), '<wheel>', 'exec'), values)
    assert torch.allclose(values['teacher_blended'][:, 3::4], torch.full((1, 4), expected))
