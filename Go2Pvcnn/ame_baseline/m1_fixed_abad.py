"""Eight policy joints, four fixed ABAD targets and fixed wheel commands."""
import torch
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES
from .m1_ame_contract import validate_fixed_wheel_speed

M1_HIP_KNEE_JOINT_NAMES = tuple(n for n in M1_PLANNER_JOINT_NAMES if not n.endswith('ABAD_JOINT'))
M1_ABAD_JOINT_NAMES = tuple(n for n in M1_PLANNER_JOINT_NAMES if n.endswith('ABAD_JOINT'))


def expand_fixed_abad_actions(actions, speed_m_s=.30):
    if actions.ndim != 2 or actions.shape[-1] != 8:
        raise ValueError('fixed ABAD policy actions must have shape [B,8]')
    if not bool(torch.isfinite(actions).all()):
        raise ValueError('Non-finite fixed ABAD actions')
    speed = validate_fixed_wheel_speed(speed_m_s)
    result = actions.new_zeros((actions.shape[0], 16))
    result[:, [M1_ASSET_JOINT_NAMES.index(n) for n in M1_HIP_KNEE_JOINT_NAMES]] = actions
    result[:, [M1_ASSET_JOINT_NAMES.index(n) for n in M1_WHEEL_JOINT_NAMES]] = speed
    return result


def fixed_abad_contract(speed_m_s=.30):
    return dict(version=2, mode='fixed_wheel_fixed_abad_hip_knee',
                policy_joint_names=list(M1_HIP_KNEE_JOINT_NAMES),
                fixed_joint_names=list(M1_ABAD_JOINT_NAMES), fixed_joint_targets=[0.]*4,
                wheel_joint_names=list(M1_WHEEL_JOINT_NAMES),
                wheel_speed_m_s=validate_fixed_wheel_speed(speed_m_s),
                executed_history_joint_names=list(M1_ASSET_JOINT_NAMES))
