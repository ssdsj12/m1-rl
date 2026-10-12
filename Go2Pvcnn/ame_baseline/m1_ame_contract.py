"""Tensor-only M1 action and observation contract."""
from __future__ import annotations

import torch
from math import atan2, sin, cos, isfinite
from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES,
    M1_WHEEL_RADIUS_M, M1_ABAD_LOWER, M1_ABAD_UPPER,
    M1_HIP_LOWER, M1_HIP_UPPER, M1_KNEE_LOWER, M1_KNEE_UPPER,
)
from extension.parallelism.rl_adapter import resolve_named_indices, select_named_joint_state

# The previous 0.25 rad envelope only raised the wheel centre by a few cm,
# so the learned policy could not clear even the small 3--6 cm obstacles.
# Keep the action head at 16 dimensions, but give hip/knee targets enough
# authority for the MPC teacher's 18--20 cm wheel-centre swing.  A 0.65 rad
# envelope clipped a reachable 0.20 m lift (about 0.91 rad at the knee) and
# made the teacher slide. Joint limits still bound the resulting target.
# Keep the policy head in [-1, 1] while retaining the full M1 IK target
# range; the previous 1.0 rad scale clipped the knee lift for 10 cm boxes.
M1_LEG_ACTION_SCALE_RAD = 1.50
# One wheel action unit requests 1 m/s at the tire. The 2 m/s cap includes
# headroom for the existing 1 m/s translation plus yaw command.
M1_WHEEL_ACTION_SCALE_RAD_S = 1.0 / M1_WHEEL_RADIUS_M
M1_WHEEL_SPEED_LIMIT_RAD_S = 20.0
# User approved the pinned bare-M1 stance, replacing the 585mm mesh calibration.
# Front knees point inward (-X); rear knees point inward (+X). All four
# source joint axes have the same sign, so copying angles is NOT mirroring.
M1_TRAINING_JOINT_POS = ((0., .30, -.60, 0.) * 2
                         + (0., -.30, .60, 0.) * 2)
# Reference spawn root height, not total robot height or settled support height.
M1_TRAINING_ROOT_Z_M = .62
# No user-imposed extra air gap. Actual nonpenetration, collision accounting,
# measured passage and stable far-side landing remain mandatory.
M1_REQUIRED_TOP_MARGIN_M = 0.0


def m1_training_contract(*, fixed_abad=False):
    """Pose/reset semantics required in newly trained checkpoints."""
    from .m1_reference_robot import REFERENCE_ROBOT_COMMIT
    from .m1_stall_slip import reward_contract
    from .m1_collision_budget import collision_budget_contract
    contract = dict(version=3, stance='reference_front_rear_inward_root062',
                reference_robot_commit=REFERENCE_ROBOT_COMMIT,
                policy_state_dim=85, critic_state_dim=88, learning_signal_version=1,
                reward_contract=reward_contract(),
                robot_physics=dict(leg_motor='DCMotor',leg_pd=[120.,5.5],leg_effort=150.,
                    leg_velocity=20.,wheel_pd=[0.,30.],wheel_effort=200.,wheel_velocity=20.,
                    wheel_shape='cylinder_y',wheel_radius=.0959,wheel_width=.0465,
                    solver_iterations=[4,2],friction=[1.,1.],restitution=0.,mass_jitter=False),
                joint_names=list(M1_ASSET_JOINT_NAMES),
                joint_pos=list(M1_TRAINING_JOINT_POS), root_z=M1_TRAINING_ROOT_Z_M,
                obstacle_collision_reset=False,
                collision_budget=collision_budget_contract(),
                required_top_margin_m=M1_REQUIRED_TOP_MARGIN_M)
    if fixed_abad:
        from .m1_fixed_abad import M1_ABAD_JOINT_NAMES, M1_HIP_KNEE_JOINT_NAMES
        contract.update(version=4, fixed_abad_joint_names=list(M1_ABAD_JOINT_NAMES),
                        fixed_abad_targets=[0.]*4, policy_joint_names=list(M1_HIP_KNEE_JOINT_NAMES))
    return contract


def validate_training_contract(checkpoint, expected):
    if expected is not None and checkpoint.get('m1_training_contract') != expected:
        raise ValueError('M1 training contract mismatch: stance/obstacle reset/top margin; use a compatible checkpoint')


def m1_last_leg_action(env):
    if getattr(env.cfg, 'm1_fixed_abad', False):
        executed = m1_last_action(env)
        return select_named_joint_state(executed, source_names=M1_ASSET_JOINT_NAMES,
                                        selected_names=M1_PLANNER_JOINT_NAMES)
    if getattr(env.cfg, 'm1_fixed_wheel_speed_m_s', None) is not None:
        action = env.action_manager.action
        if action.shape[-1] != 12:
            raise ValueError('fixed-wheel policy must have 12 leg actions')
        return action
    return select_named_joint_state(
        env.action_manager.action,
        source_names=env.cfg.asset_joint_names,
        selected_names=M1_PLANNER_JOINT_NAMES,
    )


def m1_last_action(env):
    """M1 policy history includes all 12 leg and 4 wheel commands."""
    speed = getattr(env.cfg, 'm1_fixed_wheel_speed_m_s', None)
    if getattr(env.cfg, 'm1_fixed_abad', False):
        from .m1_fixed_abad import expand_fixed_abad_actions
        return expand_fixed_abad_actions(env.action_manager.action, speed)
    if speed is not None:
        return expand_fixed_wheel_actions(env.action_manager.action, speed)
    return select_named_joint_state(
        env.action_manager.action,
        source_names=env.cfg.asset_joint_names,
        selected_names=M1_ASSET_JOINT_NAMES,
    )


def m1_wheel_surface_velocity(env):
    """Named wheel speeds in m/s; omit unbounded integrated wheel angles."""
    robot = env.scene["robot"]
    return select_named_joint_state(
        robot.data.joint_vel,
        source_names=tuple(robot.joint_names),
        selected_names=M1_WHEEL_JOINT_NAMES,
    ) * M1_WHEEL_RADIUS_M


def validate_fixed_wheel_speed(speed_m_s):
    speed = float(speed_m_s)
    if not isfinite(speed) or not 0.0 < speed <= 2.0:
        raise ValueError('fixed wheel surface speed must be finite and in (0, 2] m/s')
    return speed


def expand_fixed_wheel_actions(actions, speed_m_s=.30):
    """Executed 16-slot history/decoder input; never a PPO action distribution."""
    if actions.ndim != 2 or actions.shape[-1] != 12:
        raise ValueError('fixed-wheel policy actions must have shape [B,12]')
    speed = validate_fixed_wheel_speed(speed_m_s)
    legs = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    wheels = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES))
    executed = actions.new_zeros((actions.shape[0], 16))
    executed[:, legs] = actions
    executed[:, wheels] = speed / (M1_WHEEL_RADIUS_M * M1_WHEEL_ACTION_SCALE_RAD_S)
    return executed


def m1_action_targets(actions, default_joint_pos):
    """Interleaved leg position (rad) and wheel velocity (rad/s) targets."""
    if actions.shape[-1] != 16 or default_joint_pos.shape != actions.shape:
        raise ValueError("M1 actions/default_joint_pos must share shape [B,16]")
    legs = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    wheels = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES))
    lower = actions.new_tensor(tuple(v for triple in zip(M1_ABAD_LOWER, M1_HIP_LOWER, M1_KNEE_LOWER) for v in triple))
    upper = actions.new_tensor(tuple(v for triple in zip(M1_ABAD_UPPER, M1_HIP_UPPER, M1_KNEE_UPPER) for v in triple))
    targets = torch.empty_like(actions)
    targets[:, legs] = (default_joint_pos[:, legs] + M1_LEG_ACTION_SCALE_RAD * actions[:, legs]).clamp(lower, upper)
    targets[:, wheels] = (M1_WHEEL_ACTION_SCALE_RAD_S * actions[:, wheels]).clamp(-M1_WHEEL_SPEED_LIMIT_RAD_S, M1_WHEEL_SPEED_LIMIT_RAD_S)
    return targets
