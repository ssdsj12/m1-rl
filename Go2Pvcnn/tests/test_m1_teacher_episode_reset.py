"""Replay the real wrapper's post-step lifecycle block without Isaac startup."""
import ast
from pathlib import Path
from types import SimpleNamespace

import torch


def test_done_rows_clear_teacher_lifecycle_without_resetting_live_rows():
    source = Path(__file__).resolve().parents[1] / 'ame_baseline/ame_env_wrapper.py'
    cls = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef))
    step = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'step')
    start = next(i for i, n in enumerate(step.body) if isinstance(n, ast.AugAssign)
                 and isinstance(n.target, ast.Attribute) and n.target.attr == '_m1_teacher_active')
    end = next(i for i, n in enumerate(step.body) if isinstance(n, ast.Assign)
               and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'rewards')
    bool_names = ['_m1_teacher_active', '_m1_obstacle_event_seen',
                  '_m1_initial_teacher_fallback_used', '_m1_short_trigger_seen',
                  '_small_candidate_prev', '_small_candidate_seen',
                  '_small_candidate_lift_seen', '_small_candidate_clearance_seen',
                  '_large_candidate_seen']
    age_names = ['_m1_teacher_age', '_m1_teacher_elapsed', '_m1_teacher_no_candidate_steps',
                 '_m1_short_trigger_clear_steps', '_m1_obstacle_clear_steps']
    strict_tracker = SimpleNamespace(reset=lambda rows: None)
    anchor_names = ['_m1_teacher_hold_foot_phase', '_m1_teacher_hold_foot_leg']
    wrapper = SimpleNamespace(**{n: torch.ones(3, dtype=torch.bool) for n in bool_names},
                              **{n: torch.full((3,), 7, dtype=torch.long) for n in age_names},
                              **{n: torch.full((3,), 2, dtype=torch.long) for n in anchor_names},
                              _m1_strict_crossing=strict_tracker)
    scope = dict(self=wrapper, torch=torch, done=torch.tensor([True, False, True]),
                 crossing_complete=torch.zeros(3, dtype=torch.bool),
                 strict_crossing_complete=torch.zeros(3, dtype=torch.bool),
                 teacher_phase_done=torch.zeros(3, dtype=torch.bool))
    exec(compile(ast.Module(body=step.body[start:end], type_ignores=[]), str(source), 'exec'), scope)
    for name in bool_names + age_names:
        value = getattr(wrapper, name)
        assert not bool(value[[0, 2]].any()), f'{name} leaked into next episode: {value}'
        assert int(value[1]) == (1 if name in bool_names else 7), name
    for name in anchor_names:
        assert getattr(wrapper, name).tolist() == [-1, 2, -1]
