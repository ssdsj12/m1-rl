"""Execute production anchor statements without booting Isaac Sim."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace

import torch

from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS
from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, m1_fk,
)


def test_anchor_capture_and_row_local_phase_handoff(monkeypatch):
    monkeypatch.setenv('M1_TEACHER_HOLD_FOOT_USE_CURRENT', '1')
    path = Path(__file__).resolve().parents[1] / 'ame_baseline/ame_env_wrapper.py'
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'AmeRslRlEnvWrapper')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'get_mpc_teacher_action')
    start = next(i for i, n in enumerate(method.body) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'held_planner')
    end = next(i for i, n in enumerate(method.body) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript) and isinstance(n.targets[0].slice, ast.Constant) and n.targets[0].slice.value == 'hold_foot_pos_w')
    code = compile(ast.Module(body=method.body[start:end+1], type_ignores=[]), str(path), 'exec')
    cols = [M1_ASSET_JOINT_NAMES.index(n) for n in M1_PLANNER_JOINT_NAMES]
    joints = torch.tensor(M1_TRAINING_JOINT_POS).reshape(1, 16).repeat(2, 1)
    root = torch.tensor([[0., 0., .55], [8., 0., .55]])
    rpy = torch.zeros(2, 3)
    state = SimpleNamespace(num_envs=2, _m1_teacher_hold_pose=joints.clone(),
                            _m1_teacher_hold_foot_w=None, _m1_teacher_hold_foot_phase=None)
    context = dict(torch=torch, os=os, m1_fk=m1_fk, self=state,
                   robot=SimpleNamespace(data=SimpleNamespace(root_pos_w=root)),
                   reference={'m1_root_pos_w': root.clone()}, root_rpy=rpy,
                   current_pos=joints, planner_cols=cols, phase_slot=torch.tensor([0, 0]))
    exec(code, context)
    first = m1_fk(root, rpy, joints[:, cols]).foot_pos_w
    torch.testing.assert_close(state._m1_teacher_hold_foot_w, first)
    root[:, 2] -= .1
    context['reference']['m1_root_pos_w'] = root.clone()
    exec(code, context)
    torch.testing.assert_close(state._m1_teacher_hold_foot_w, first)
    context['phase_slot'] = torch.tensor([1, 0])
    exec(code, context)
    changed = m1_fk(root, rpy, joints[:, cols]).foot_pos_w
    torch.testing.assert_close(state._m1_teacher_hold_foot_w[0], changed[0])
    torch.testing.assert_close(state._m1_teacher_hold_foot_w[1], first[1])
