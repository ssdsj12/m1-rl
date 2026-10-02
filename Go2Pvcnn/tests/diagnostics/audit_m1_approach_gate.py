"""CPU-only reproduction of the live wrapper approach gate; no simulation."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

import torch

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES,
)
from extension.parallelism.rl_adapter import resolve_named_indices

source = Path('ame_baseline/ame_env_wrapper.py')
tree = ast.parse(source.read_text())
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
method = next(n for n in cls.body if isinstance(n, ast.FunctionDef)
              and n.name == 'get_mpc_teacher_action')
scope = {'torch': torch, '__package__': 'ame_baseline'}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), scope)

default = torch.zeros(1, 16)
reference = dict(joint_angles=torch.zeros(1, 12),
                 contact_state=torch.tensor([[False, True, True, True]]),
                 phase_index=torch.tensor([1]), valid_mask=torch.tensor([True]))
reference['joint_angles'][0, 2] = 0.6
manager = NS(refresh_from_env=lambda env: None,
             current_reference=lambda frame_offset: reference)
robot = NS(joint_names=M1_ASSET_JOINT_NAMES,
           data=NS(default_joint_pos=default, joint_pos=default.clone(),
                   root_quat_w=torch.tensor([[1., 0., 0., 0.]])))
w = NS(unwrapped=NS(_trajectory_manager=manager, scene={'robot': robot}),
       num_envs=1, _m1_teacher_max_steps=2048,
       get_obstacle_presence=lambda: (torch.tensor([True]), torch.tensor([False])))
for name in ('_m1_initial_teacher_fallback_used', '_m1_obstacle_event_seen',
             '_m1_short_trigger_seen', '_m1_teacher_active'):
    setattr(w, name, torch.zeros(1, dtype=torch.bool))
for name in ('_m1_short_trigger_clear_steps', '_m1_teacher_age'):
    setattr(w, name, torch.zeros(1, dtype=torch.long))
cols = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
rows = []
with patch('ame_baseline.m1_obstacle_rewards.m1_teacher_obstacle_presence',
           return_value=(torch.tensor([False]), torch.tensor([False]))):
    for call in range(3):
        action, valid = scope['get_mpc_teacher_action'](w)
        rows.append(dict(call=call, near_trigger=False, valid=bool(valid[0]),
                         leg_action_max=float(action[:, cols].abs().max())))
print(json.dumps({'source': str(source.resolve()), 'calls': rows,
                  'premature_swing_reproduced': any(r['leg_action_max'] > 0 for r in rows)}))
