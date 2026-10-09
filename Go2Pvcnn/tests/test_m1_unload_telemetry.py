"""Exercise the actual nested observer without starting Isaac Sim."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS

import torch


def test_unload_observer_reports_mass_weighted_velocity_and_xyz_force():
    tree = ast.parse((Path(__file__).parents[1] / 'scripts/probe_m1_contact_prepare.py').read_text())
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'read_unload_substep')
    native = torch.arange(8 * 4 * 3).reshape(8, 4, 3).float()
    masses = torch.tensor([[1., 3.]]).expand(8, -1)
    velocities = torch.tensor([[[2., 0., 0.], [0., 4., 0.]]]).expand(8, -1, -1)
    data = NS(root_lin_vel_w=torch.zeros(8, 3), body_com_lin_vel_w=velocities,
              root_ang_vel_w=torch.ones(8, 3))
    scope = dict(sensor=NS(contact_physx_view=NS(get_net_contact_forces=lambda dt: native)),
                 cfg=NS(sim=NS(dt=.005)), wheel_sensor_ids=[2, 0, 3, 1],
                 robot=NS(data=data, root_physx_view=NS(get_masses=lambda: masses)),
                 unload_friction_views={})
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<observer>', 'exec'), scope)
    result = scope['read_unload_substep']()
    assert result['com_velocity'][0] == [.5, 3., 0.]
    assert result['wheel_normal_force_xyz'][0] == native[0, [2, 0, 3, 1]].tolist()
    assert result['root_angular_velocity'][0] == [1., 1., 1.]
    assert result['force'][0] == native[0, [2, 0, 3, 1], 2].tolist()
    data.body_com_pos_w=torch.zeros(8,2,3)
    scope['unload_friction_views']={(0,'FBL_FOOT_LINK'):NS(get_friction_data=lambda dt:
        (torch.tensor([[2.,0.,0.]]),torch.tensor([[0.,1.,0.]]),
         torch.tensor([[1]]),torch.tensor([[0]])))}
    observed=scope['read_unload_substep']()['friction_about_com']
    assert observed==[{'row':0,'wheel':'FBL_FOOT_LINK',
                      'pairs':[{'force':[2.,0.,0.],'moment':[0.,0.,-2.],'count':1}]}]
