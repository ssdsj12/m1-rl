from types import SimpleNamespace

import torch

from ame_baseline.m1_ame_terminations import nonfinite_robot_state
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES


def _env_with_robot_state():
    data = SimpleNamespace(
        root_state_w=torch.zeros(4, 13),
        body_state_w=torch.zeros(4, 17, 13),
        joint_pos=torch.zeros(4, 16),
        joint_vel=torch.zeros(4, 16),
        joint_acc=torch.zeros(4, 16),
        applied_torque=torch.zeros(4, 16),
    )
    return SimpleNamespace(scene={"robot": SimpleNamespace(data=data, joint_names=M1_ASSET_JOINT_NAMES)})


def test_nonfinite_robot_state_is_false_when_all_state_is_finite():
    env = _env_with_robot_state()

    invalid = nonfinite_robot_state(env, SimpleNamespace(name="robot"))

    assert invalid.dtype == torch.bool
    assert invalid.tolist() == [False, False, False, False]


def test_nonfinite_robot_state_marks_only_affected_environments():
    env = _env_with_robot_state()
    env.scene["robot"].data.root_state_w[0, 4] = torch.nan
    env.scene["robot"].data.joint_pos[1, 7] = torch.inf
    env.scene["robot"].data.joint_vel[2, 9] = -torch.inf

    invalid = nonfinite_robot_state(env, SimpleNamespace(name="robot"))

    assert invalid.tolist() == [True, True, True, False]


def test_nonfinite_robot_state_marks_reward_state_and_extreme_outliers():
    env = _env_with_robot_state()
    env.scene["robot"].data.body_state_w[0, 3, 7] = torch.nan
    env.scene["robot"].data.joint_acc[1, 2] = 1.0e9
    env.scene["robot"].data.applied_torque[2, 5] = -1.0e8

    invalid = nonfinite_robot_state(env, SimpleNamespace(name="robot"))

    assert invalid.tolist() == [True, True, True, False]


def test_continuous_wheel_angle_is_not_numerical_explosion_but_nonfinite_is():
    env = _env_with_robot_state()
    env.scene["robot"].data.joint_pos[0, 3] = 1e5
    env.scene["robot"].data.joint_pos[1, 0] = 1e5
    env.scene["robot"].data.joint_pos[2, 3] = torch.inf
    invalid = nonfinite_robot_state(env, SimpleNamespace(name="robot"))
    assert invalid.tolist() == [False, True, True, False]
