from types import SimpleNamespace

import pytest
import torch

from ame_baseline.m1_ame_rewards import (
    m1_action_rate_l2,
    m1_energy,
    m1_joint_acc_l2,
    m1_joint_pos_limits,
    m1_joint_position_penalty,
    m1_joint_torques_l2,
    m1_joint_vel_l2,
)
from extension.parallelism.m1_kinematics import (
    M1_ABAD_UPPER,
    M1_ASSET_JOINT_NAMES,
    M1_WHEEL_RADIUS_M,
)
import ame_baseline.m1_ame_rewards as rewards


def _joint_index(name: str) -> int:
    return M1_ASSET_JOINT_NAMES.index(name)


def _fake_env(batch: int = 1):
    data = SimpleNamespace(
        joint_pos=torch.zeros(batch, 16),
        default_joint_pos=torch.zeros(batch, 16),
        joint_vel=torch.zeros(batch, 16),
        joint_acc=torch.zeros(batch, 16),
        applied_torque=torch.zeros(batch, 16),
        root_lin_vel_b=torch.zeros(batch, 3),
    )
    robot = SimpleNamespace(data=data, joint_names=M1_ASSET_JOINT_NAMES)
    return SimpleNamespace(
        scene={"robot": robot},
        cfg=SimpleNamespace(asset_joint_names=M1_ASSET_JOINT_NAMES),
        action_manager=SimpleNamespace(
            action=torch.zeros(batch, 16),
            prev_action=torch.zeros(batch, 16),
        ),
        command_manager=SimpleNamespace(
            get_command=lambda name: torch.zeros(batch, 3),
        ),
    )


def test_m1_squared_motion_terms_split_planner_and_wheel_scales_by_name():
    env = _fake_env()
    planner_index = _joint_index("FBL_ABAD_JOINT")
    wheel_index = _joint_index("FBL_FOOT_JOINT")
    for values in (env.scene["robot"].data.joint_vel, env.scene["robot"].data.joint_acc):
        values[0, planner_index] = 2.0
        values[0, wheel_index] = 10.0
    env.action_manager.action[0, planner_index] = 2.0
    env.action_manager.action[0, wheel_index] = 10.0

    expected = 4.0 + 100.0 * M1_WHEEL_RADIUS_M**2
    assert m1_joint_vel_l2(env).item() == pytest.approx(expected)
    assert m1_joint_acc_l2(env).item() == pytest.approx(expected)
    assert m1_action_rate_l2(env).item() == pytest.approx(expected)


def test_m1_torque_and_energy_include_named_wheels_in_physical_units():
    env = _fake_env()
    planner_index = _joint_index("FBL_ABAD_JOINT")
    wheel_index = _joint_index("FBL_FOOT_JOINT")
    env.scene["robot"].data.applied_torque[0, planner_index] = 3.0
    env.scene["robot"].data.applied_torque[0, wheel_index] = 4.0
    env.scene["robot"].data.joint_vel[0, planner_index] = 2.0
    env.scene["robot"].data.joint_vel[0, wheel_index] = 10.0

    assert m1_joint_torques_l2(env).item() == pytest.approx(3.0**2 + 4.0**2)
    assert m1_energy(env).item() == pytest.approx(3.0 * 2.0 + 4.0 * 10.0)


def test_m1_posture_and_limits_ignore_wheel_angle():
    env = _fake_env()
    wheel_index = _joint_index("FBL_FOOT_JOINT")
    planner_index = _joint_index("FBL_ABAD_JOINT")
    env.scene["robot"].data.joint_pos[0, wheel_index] = 1.0e6

    assert m1_joint_position_penalty(
        env, stand_still_scale=5.0, velocity_threshold=0.3
    ).item() == pytest.approx(0.0)
    assert m1_joint_pos_limits(env).item() == pytest.approx(0.0)

    env.scene["robot"].data.joint_pos[0, planner_index] = M1_ABAD_UPPER[0] + 0.1
    assert m1_joint_position_penalty(
        env, stand_still_scale=5.0, velocity_threshold=0.3
    ).item() == pytest.approx(5.0 * (M1_ABAD_UPPER[0] + 0.1))
    assert m1_joint_pos_limits(env).item() == pytest.approx(0.1, abs=1.0e-6)


def test_m1_regularizers_resolve_reordered_asset_state_by_joint_name():
    env = _fake_env()
    robot = env.scene["robot"]
    robot.joint_names = tuple(reversed(M1_ASSET_JOINT_NAMES))
    planner_index = robot.joint_names.index("FBL_ABAD_JOINT")
    wheel_index = robot.joint_names.index("FBL_FOOT_JOINT")
    robot.data.joint_vel[0, planner_index] = 2.0
    robot.data.joint_vel[0, wheel_index] = 10.0

    expected = 4.0 + 100.0 * M1_WHEEL_RADIUS_M**2
    assert m1_joint_vel_l2(env).item() == pytest.approx(expected)


def _rolling_env():
    env = _fake_env(batch=3)
    names = tuple(f"{prefix}_FOOT_LINK" for prefix in ("RAR", "FBL", "RBL", "FAR"))
    robot = env.scene["robot"]
    robot.body_names = names
    robot.data.body_link_lin_vel_w = torch.zeros(3, 4, 3)
    robot.data.body_ang_vel_w = torch.zeros(3, 4, 3)
    robot.data.body_quat_w = torch.tensor([1., 0., 0., 0.]).expand(3, 4, 4).clone()
    robot.data.body_link_lin_vel_w[:, :, 0] = 1.0
    robot.data.body_ang_vel_w[0, :, 1] = 1.0 / M1_WHEEL_RADIUS_M
    forces = torch.zeros(3, 1, 4, 3)
    forces[:2, :, :, 2] = 10.0
    env.scene["contact_forces"] = SimpleNamespace(
        body_names=tuple(reversed(names)),
        data=SimpleNamespace(net_forces_w_history=forces),
    )
    return env


def test_wheel_rolling_is_free_locked_sliding_penalized_airborne_ignored():
    env = _rolling_env()
    actual = rewards.m1_wheel_rolling_residual_l2(env)
    torch.testing.assert_close(actual, torch.tensor([0., 4., 0.]))


def test_wheel_rolling_residual_detects_lateral_slip_and_reverse_spin():
    env = _rolling_env()
    robot = env.scene["robot"]
    robot.data.body_link_lin_vel_w[0, :, 1] = 0.5
    robot.data.body_ang_vel_w[1, :, 1] = -1.0 / M1_WHEEL_RADIUS_M
    actual = rewards.m1_wheel_rolling_residual_l2(env)
    torch.testing.assert_close(actual, torch.tensor([1., 16., 0.]))


def test_air_time_only_rewards_wheels_at_small_obstacles():
    env = _rolling_env()
    robot = env.scene["robot"]
    robot.data.root_pos_w = torch.zeros(3, 3)
    robot.data.body_pos_w = torch.zeros(3, 4, 3)
    side = 31
    axis = torch.arange(side) * .1 - 1.5
    yy, xx = torch.meshgrid(axis, axis, indexing="ij")
    hits = torch.stack((xx, yy, torch.zeros_like(xx)), -1).reshape(1, -1, 3).expand(3, -1, -1)
    semantic = torch.zeros(3, side, side)
    semantic[1, 15, 15] = 1
    semantic[2, 15, 15] = 2
    env.scene["semantic_height_scanner"] = SimpleNamespace(
        cfg=SimpleNamespace(pattern_cfg=SimpleNamespace(resolution=.1)),
        data=SimpleNamespace(ray_hits_w=hits, semantic_map=semantic, valid_mask=None),
    )
    sensor = env.scene["contact_forces"]
    sensor.data.last_air_time = torch.full((3, 4), .7)
    sensor.data.last_contact_time = torch.ones(3, 4)
    sensor.compute_first_contact = lambda dt: torch.ones(3, 4, dtype=torch.bool)
    env.step_dt = .02
    env.command_manager.get_command = lambda name: torch.tensor([[.5, 0., 0.]]).expand(3, -1)
    actual = rewards.m1_obstacle_air_time(env, threshold=.5)
    torch.testing.assert_close(actual, torch.tensor([0., .8, 0.]))
