"""Real action implementation, with only the external Isaac boundary replaced."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS

import pytest
import torch

from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES


@pytest.fixture
def runtime(monkeypatch):
    class JointAction:
        def __init__(self, cfg, env):
            self._asset = env.robot
            self._joint_names = cfg.joint_names
            self._joint_ids = [env.robot.joint_names.index(n) for n in self._joint_names]
            self._raw_actions = torch.zeros(2, len(self._joint_ids))
            self._processed_actions = self._raw_actions.clone()
        @property
        def action_dim(self):
            return len(self._joint_ids)
        @property
        def processed_actions(self):
            return self._processed_actions
        def reset(self, env_ids=None):
            self._raw_actions[:] = 0
    class JointActionCfg:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    for name, attrs in {
        'isaaclab.envs.mdp.actions.joint_actions': {'JointAction': JointAction},
        'isaaclab.envs.mdp.actions.actions_cfg': {'JointActionCfg': JointActionCfg},
        'isaaclab.utils': {'configclass': lambda c: c},
    }.items():
        module = ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location('ame_baseline._fixed_runtime_test',
        Path(__file__).parents[1] / 'ame_baseline/m1_ame_actions.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixed_targets_survive_actions_and_reset(runtime):
    assert hasattr(runtime, 'M1FixedWheelLegActionCfg')
    robot = NS(joint_names=list(M1_ASSET_JOINT_NAMES),
               data=NS(default_joint_pos=torch.zeros(2, 16)))
    robot.set_joint_position_target = lambda target, joint_ids: setattr(robot, 'legs', (target.clone(), joint_ids))
    robot.set_joint_velocity_target = lambda target, joint_ids: setattr(robot, 'wheels', (target.clone(), joint_ids))
    cfg = runtime.M1FixedWheelLegActionCfg(asset_name='robot', fixed_wheel_speed_m_s=.3)
    term = runtime.M1FixedWheelLegAction(cfg, NS(robot=robot))
    assert term.action_dim == 12
    for i in range(20):
        actions = torch.rand(2, 12) * .4 - .2  # inside existing joint limits
        term.process_actions(actions)
        term.apply_actions()
        torch.testing.assert_close(robot.legs[0], actions * 1.5)
        torch.testing.assert_close(robot.wheels[0], torch.full((2, 4), .3 / .095958))
        assert robot.wheels[1] == [3, 7, 11, 15]
    term.reset()
    term.apply_actions()
    torch.testing.assert_close(robot.wheels[0], torch.full((2, 4), .3 / .095958))
    with pytest.raises(ValueError, match='12'):
        term.process_actions(torch.zeros(2, 16))


def test_fixed_config_has_constant_command_and_no_curriculum(runtime):
    assert hasattr(runtime, 'configure_fixed_wheel_control')
    command = NS(ranges=NS(), limit_ranges=NS(), rel_standing_envs=.2, heading_command=True)
    cfg = NS(actions=NS(), commands=NS(base_velocity=command),
             curriculum=NS(lin_vel_cmd_levels=object()), planner_owned_reference_cache=False,
             use_batched_reference_trajectory=False, planner_backend=None)
    runtime.configure_fixed_wheel_control(cfg, .3)
    assert cfg.action_dim == 12
    assert cfg.actions.JointPositionAction.joint_names == list(M1_PLANNER_JOINT_NAMES)
    assert command.ranges.lin_vel_x == command.limit_ranges.lin_vel_x == (.3, .3)
    assert command.ranges.lin_vel_y == command.ranges.ang_vel_z == (0., 0.)
    assert command.rel_standing_envs == 0
    assert not command.heading_command
    assert cfg.curriculum.lin_vel_cmd_levels is None


def test_fixed_mode_rejects_planner_owner(runtime):
    assert hasattr(runtime, 'configure_fixed_wheel_control')
    with pytest.raises(ValueError, match='planner'):
        runtime.configure_fixed_wheel_control(NS(planner_owned_reference_cache=True), .3)
