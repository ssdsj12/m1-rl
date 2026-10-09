import ast
from pathlib import Path
from types import SimpleNamespace as NS
import torch


def test_roll_observer_resolves_named_forces_and_whole_body_velocity():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='read_wheel_substep')
    native=torch.arange(96).reshape(8,4,3).float()
    mass=torch.tensor([[1.,3.]]).expand(8,-1)
    vel=torch.tensor([[[2.,0.,0.],[0.,4.,0.]]]).expand(8,-1,-1)
    backend=NS(get_dof_positions=lambda:torch.zeros(8,16),get_dof_velocities=lambda:torch.zeros(8,16),get_masses=lambda:mass)
    data=NS(joint_pos=torch.zeros(8,16),joint_vel=torch.zeros(8,16),body_com_lin_vel_w=vel,root_ang_vel_w=torch.ones(8,3),
        computed_torque=torch.ones(8,16),joint_pos_target=torch.zeros(8,16),joint_vel_target=torch.zeros(8,16))
    view=NS(get_contact_data=lambda dt:(torch.tensor([12.]),torch.tensor([[1.,2.,0.]]),torch.tensor([[0.,0.,1.]]),torch.tensor([.001]),torch.tensor([1]),torch.tensor([0])))
    scope=dict(robot=NS(root_physx_view=backend,data=data),wheel_joint_ids=[3,0,2,1],wheel_sensor_ids=[2,0,3,1],
        sensor=NS(contact_physx_view=NS(get_net_contact_forces=lambda dt:native)),cfg=NS(sim=NS(dt=.005)),roll_transient_views={'FBL_FOOT_LINK':view})
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<roll observer>','exec'),scope)
    got=scope['read_wheel_substep']()
    assert got['com_velocity'][7]==[.5,3.,0.]
    assert got['wheel_normal_force_xyz'][7]==native[7,[2,0,3,1]].tolist()
    assert got['root_angular_velocity'][7]==[1.,1.,1.]
    assert got['row7_contacts']['FBL_FOOT_LINK'][0]['normal']==[12.]
    assert got['row7_computed_torque']==[1.]*16
