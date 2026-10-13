"""Opt-in student config; effective backend contracts are checked before rollout."""
import os

from .m1_teacher_contract import PHASES, PROFILE, student_contract


def validate_profile_environment():
    if os.environ.get('M1_FIXED_ABAD', '0') != '0':
        raise ValueError(f'{PROFILE} conflicts with M1_FIXED_ABAD')
    if 'M1_FIXED_WHEEL_SPEED_M_S' in os.environ:
        raise ValueError(f'{PROFILE} conflicts with M1_FIXED_WHEEL_SPEED_M_S')


def student_training_contract():
    """Keep the reference physics, observation and pose contract intact."""
    from .m1_ame_contract import m1_training_contract
    from .m1_collision_budget import collision_budget_contract
    contract = m1_training_contract()
    collision = collision_budget_contract(cost_per_step=2.)
    contract.update(version=5, profile=PROFILE, stage_sequence=[0, 3],
                    collision_budget=collision, student_contract=student_contract())
    return contract


def configure_teacher_student_profile(cfg, *, training_phase='bc'):
    """Apply after the current M1 config's complete post-init chain."""
    validate_profile_environment()
    if training_phase not in PHASES:
        raise ValueError('Unknown M1 student training phase')
    from .m1_ame_actions import M1AmeActionsCfg
    from .m1_mixed_course import configure_flat_first_terrain
    cfg.actions = M1AmeActionsCfg()
    cfg.action_dim = 16
    cfg.m1_fixed_abad = False
    cfg.m1_fixed_wheel_speed_m_s = None
    configure_flat_first_terrain(cfg)
    cfg.m1_training_profile = PROFILE
    cfg.m1_learning_stage_sequence = (0, 3)
    cfg.m1_collision_cost_per_step = 2.
    cfg.m1_collision_budget = 20.
    cfg.m1_student_contract = student_contract()
    cfg.m1_training_contract = student_training_contract()
    cfg.training_phase = training_phase
    command = cfg.commands.base_velocity
    for ranges in (command.ranges, command.limit_ranges):
        ranges.lin_vel_x = (.30, .30)
        ranges.lin_vel_y = (0., 0.)
        ranges.ang_vel_z = (0., 0.)
    command.rel_standing_envs = 0.
    command.heading_command = False
    cfg.curriculum.lin_vel_cmd_levels = None
    return cfg


def build_teacher_student_env_cfg(*, training_phase='bc'):
    # Reject stale shell settings before the legacy post-init consumes them.
    validate_profile_environment()
    from .m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    return configure_teacher_student_profile(
        M1AmeCrossLargeComplexEnvCfg(), training_phase=training_phase)


def require_teacher_student_backend(env):
    """Fail closed unless actual backends expose the requested contracts.

    CollisionBudget.contract must describe its effective instance settings;
    LearningCurriculumGate.stage_sequence must also appear in state_dict().
    Checking the config alone would silently accept the old 5/s and 0..4 code.
    """
    budget = getattr(env, '_m1_collision_budget', None)
    gate = getattr(env, '_m1_learning_gate', None)
    if (getattr(budget, 'contract', None) != student_training_contract()['collision_budget']
            or getattr(gate, 'stage_sequence', None) != (0, 3)
            or gate.state_dict().get('stage_sequence') != [0, 3]):
        raise RuntimeError('M1 student profile requires Task 2 per-control-step collision '
                           'and persisted (0, 3) curriculum backends before rollout')
