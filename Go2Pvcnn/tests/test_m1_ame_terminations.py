from types import SimpleNamespace

import torch

from ame_baseline.m1_ame_terminations import nonfinite_robot_state


def _env_with_robot_state():
    data = SimpleNamespace(
        root_state_w=torch.zeros(4, 13),
        joint_pos=torch.zeros(4, 16),
        joint_vel=torch.zeros(4, 16),
    )
    return SimpleNamespace(scene={"robot": SimpleNamespace(data=data)})


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
