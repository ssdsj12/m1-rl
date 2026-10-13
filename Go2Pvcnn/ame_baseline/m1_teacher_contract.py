"""Versioned checkpoint boundary for the sixteen-action M1 student."""
from copy import deepcopy

from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES


PHASES = ('bc', 'withdrawal', 'critic_calibration', 'ppo')
REFERENCE = '8aeb845f73e39fd1e121758522ef05ee2378150f'
PROFILE = 'teacher_student_16_10cm'


def student_contract():
    return dict(version=1, profile=PROFILE, action_dim=16,
                joint_names=list(M1_ASSET_JOINT_NAMES), fixed_abad=False,
                fixed_wheel_speed_m_s=None, stage_sequence=[0, 3],
                teacher_source=REFERENCE, collision_cost_per_step=2.,
                collision_budget=20.)


def require_contract(checkpoint, *, expected_phase):
    """Ordinary resume never converts a legacy policy or changes its phase."""
    saved = checkpoint.get('m1_student_contract')
    if saved != student_contract() or checkpoint.get('ame_num_actions') != 16:
        raise ValueError('M1 student contract mismatch; explicit conversion is required')
    if expected_phase not in PHASES or checkpoint.get('training_phase') not in PHASES:
        raise ValueError('Unknown M1 student training phase')
    if checkpoint['training_phase'] != expected_phase:
        raise ValueError('M1 student training phase mismatch; explicit conversion is required')
    return deepcopy(saved)
