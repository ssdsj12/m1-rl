from pathlib import Path
from types import SimpleNamespace as NS
import importlib.util
import torch
from ame_baseline import m1_ame_contract as c
from extension.parallelism.m1_kinematics import M1_WHEEL_RADIUS_M


def test_reference_pose_and_new_learning_contract():
    assert c.M1_TRAINING_ROOT_Z_M == .62
    assert c.M1_TRAINING_JOINT_POS == (0.,.3,-.6,0.)*2+(0.,-.3,.6,0.)*2
    assert M1_WHEEL_RADIUS_M == .0959
    info=c.m1_training_contract()
    assert info['version'] == 2
    assert info['policy_state_dim'] == 85 and info['critic_state_dim'] == 88
    assert info['reference_robot_commit'] == '8aeb845f73e39fd1e121758522ef05ee2378150f'
    assert info['learning_signal_version'] == 1


def test_reference_configuration_replaces_inherited_randomization_and_pd():
    assert importlib.util.find_spec('ame_baseline.m1_reference_robot') is not None
    from ame_baseline.m1_reference_robot import configure_reference_robot
    cfg=NS(scene=NS(robot=NS(spawn=NS(articulation_props=NS()),actuators={}),
                    terrain=NS(physics_material=NS())),
           events=NS(physics_material=NS(params={}),add_base_mass=object(),
                     reset_robot_joints=NS(params={})))
    configure_reference_robot(cfg, dc_motor_cls=NS, implicit_cls=NS)
    legs=cfg.scene.robot.actuators['legs']; wheels=cfg.scene.robot.actuators['wheels']
    assert (legs.stiffness,legs.damping,legs.effort_limit,legs.saturation_effort,legs.velocity_limit)==(120.,5.5,150.,150.,20.)
    assert (wheels.stiffness,wheels.damping,wheels.effort_limit_sim,wheels.velocity_limit_sim)==(0.,30.,200.,20.)
    assert cfg.scene.robot.spawn.articulation_props.solver_velocity_iteration_count==2
    assert cfg.events.add_base_mass is None
    assert cfg.events.physics_material.params['static_friction_range']==(1.,1.)
    assert cfg.events.physics_material.params['restitution_range']==(0.,0.)
    assert cfg.events.reset_robot_joints.params['velocity_range']==(0.,0.)


def test_runtime_uses_reference_config_and_real_cylinder_overlay():
    base=Path(__file__).parents[1]/'ame_baseline'
    assert 'configure_reference_robot(self)' in (base/'m1_ame_env_cfg.py').read_text()
    src=(base/'m1_ame_assets.py').read_text()
    assert 'apply_reference_wheel_colliders(robot_prim)' in src
    assert 'UsdGeom.Cylinder.Define' in src


def test_checkpoint_rejects_old_585mm_even_when_actions_match():
    import pytest
    old=dict(c.m1_training_contract(),version=1,stance='front_rear_inward_585mm')
    with pytest.raises(ValueError,match='training contract'):
        c.validate_training_contract({'m1_training_contract':old},c.m1_training_contract())
