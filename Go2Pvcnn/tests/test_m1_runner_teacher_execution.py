"""Exercise the actual runner assembly block, not a duplicate helper."""
import ast
import os
from pathlib import Path
import torch
import pytest


@pytest.mark.parametrize('legacy_blend', [None, '0.50'])
def test_selected_teacher_leg_command_is_not_blended_with_student(monkeypatch, legacy_blend):
    if legacy_blend is None:
        monkeypatch.delenv('M1_MPC_TEACHER_BLEND', raising=False)
    else:
        monkeypatch.setenv('M1_MPC_TEACHER_BLEND', legacy_blend)
    path = Path(__file__).parents[1] / 'rsl_rl/rsl_rl/runners/on_policy_runner.py'
    tree = ast.parse(path.read_text())
    block = next(node.body for node in ast.walk(tree) if isinstance(node, ast.If)
                 and any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'leg_mask' for t in n.targets) for n in node.body))
    start = next(i for i, n in enumerate(block) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'leg_mask')
    end = next(i for i, n in enumerate(block) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'teacher_blended') + 1
    student = torch.zeros((2, 16))
    teacher = torch.linspace(-.8, .8, 32).reshape(2, 16)
    scope = dict(torch=torch, os=os, actions=student, teacher_action=teacher)
    exec(compile(ast.Module(body=block[start:end], type_ignores=[]), str(path), 'exec'), scope)
    mask = scope['leg_mask']
    torch.testing.assert_close(scope['teacher_blended'][:, mask], teacher[:, mask])
