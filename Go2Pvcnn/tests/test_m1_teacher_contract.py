"""CPU contracts for the opt-in teacher/student profile (no simulator launch)."""
from copy import deepcopy
import importlib
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
import torch

from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_WHEEL_RADIUS_M


def contract_module():
    name = 'ame_baseline.m1_teacher_contract'
    assert importlib.util.find_spec(name) is not None, 'teacher/student contract is not implemented'
    return importlib.import_module(name)


def profile_module():
    name = 'ame_baseline.m1_teacher_profile'
    assert importlib.util.find_spec(name) is not None, 'teacher/student profile is not implemented'
    return importlib.import_module(name)


def checkpoint(phase='bc'):
    return dict(m1_student_contract=contract_module().student_contract(),
                ame_num_actions=16, training_phase=phase)


def test_exact_student_contract_and_defensive_copy():
    m = contract_module()
    assert m.PHASES == ('bc', 'withdrawal', 'critic_calibration', 'ppo')
    assert m.REFERENCE == '8aeb845f73e39fd1e121758522ef05ee2378150f'
    assert m.student_contract() == dict(version=1, profile='teacher_student_16_10cm',
        action_dim=16, joint_names=list(M1_ASSET_JOINT_NAMES), fixed_abad=False,
        fixed_wheel_speed_m_s=None, stage_sequence=[0, 3], teacher_source=m.REFERENCE,
        collision_cost_per_step=2., collision_budget=20.)
    saved = checkpoint()
    validated = m.require_contract(saved, expected_phase='bc')
    validated['joint_names'].clear()
    assert saved['m1_student_contract'] == m.student_contract()


@pytest.mark.parametrize('actions', [8, 12, 16])
def test_rejects_old_checkpoints_even_when_action_count_matches(actions):
    with pytest.raises(ValueError, match='contract'):
        contract_module().require_contract(dict(ame_num_actions=actions), expected_phase='ppo')


@pytest.mark.parametrize('mutation', [
    lambda c: c.update(training_phase='unknown'),
    lambda c: c.update(training_phase='ppo'),
    lambda c: c.update(ame_num_actions=12),
    lambda c: c['m1_student_contract'].update(teacher_source='other'),
    lambda c: c['m1_student_contract'].update(stage_sequence=[0, 1, 3]),
    lambda c: c['m1_student_contract'].update(extra=True),
])
def test_resume_requires_exact_contract_and_same_phase(mutation):
    saved = checkpoint()
    mutation(saved)
    with pytest.raises(ValueError):
        contract_module().require_contract(saved, expected_phase='bc')


def test_all_documented_phases_validate_but_unknown_runtime_phase_does_not():
    m = contract_module()
    for phase in m.PHASES:
        assert m.require_contract(checkpoint(phase), expected_phase=phase) == m.student_contract()
    with pytest.raises(ValueError):
        m.require_contract(checkpoint(), expected_phase='unknown')


def test_action_columns_pose_and_scales_are_unchanged():
    from ame_baseline.m1_ame_contract import (m1_action_targets, M1_TRAINING_JOINT_POS,
        M1_LEG_ACTION_SCALE_RAD, M1_WHEEL_ACTION_SCALE_RAD_S, M1_WHEEL_SPEED_LIMIT_RAD_S)
    assert len(contract_module().student_contract()['joint_names']) == 16
    assert M1_TRAINING_JOINT_POS == (0., .3, -.6, 0.) * 2 + (0., -.3, .6, 0.) * 2
    assert (M1_LEG_ACTION_SCALE_RAD, M1_WHEEL_ACTION_SCALE_RAD_S, M1_WHEEL_SPEED_LIMIT_RAD_S) == (1.5, 1. / M1_WHEEL_RADIUS_M, 20.)
    pose = torch.tensor(M1_TRAINING_JOINT_POS)[None]
    actions = torch.zeros_like(pose)
    actions[:, [3, 7, 11, 15]] = torch.tensor([.1, -.2, .3, 100.])
    targets = m1_action_targets(actions, pose)
    torch.testing.assert_close(targets[:, [3, 7, 11, 15]], torch.tensor([[.1/M1_WHEEL_RADIUS_M, -.2/M1_WHEEL_RADIUS_M, .3/M1_WHEEL_RADIUS_M, 20.]]))
    torch.testing.assert_close(targets[:, [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14]], pose[:, [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14]])


@pytest.mark.parametrize('variable,value', [('M1_FIXED_ABAD', '1'), ('M1_FIXED_ABAD', 'junk'), ('M1_FIXED_WHEEL_SPEED_M_S', '.30')])
def test_stale_fixed_action_environment_is_rejected(monkeypatch, variable, value):
    monkeypatch.setenv(variable, value)
    with pytest.raises(ValueError, match=variable):
        profile_module().validate_profile_environment()


def test_unset_or_explicit_false_fixed_abad_is_compatible(monkeypatch):
    monkeypatch.delenv('M1_FIXED_WHEEL_SPEED_M_S', raising=False)
    monkeypatch.setenv('M1_FIXED_ABAD', '0')
    profile_module().validate_profile_environment()


def test_training_contract_preserves_physics_pose_observations():
    from ame_baseline.m1_ame_contract import m1_training_contract
    base = m1_training_contract()
    updated = profile_module().student_training_contract()
    for key in base.keys() - {'version', 'collision_budget'}:
        assert updated[key] == base[key], key
    assert updated['version'] == 5
    assert updated['profile'] == 'teacher_student_16_10cm'
    assert updated['stage_sequence'] == [0, 3]
    assert updated['collision_budget']['cost_per_step'] == 2.
    assert updated['collision_budget']['episode_budget'] == 20.
    assert 'rate_per_s' not in updated['collision_budget']
    assert m1_training_contract() == base


def test_existing_backends_fail_closed():
    from ame_baseline.m1_collision_budget import CollisionBudget
    from ame_baseline.m1_learning_curriculum import LearningCurriculumGate
    env = NS(_m1_collision_budget=CollisionBudget(1, 'cpu', .02),
             _m1_learning_gate=LearningCurriculumGate(1, 'cpu'))
    with pytest.raises(RuntimeError, match='Task 2'):
        profile_module().require_teacher_student_backend(env)


def test_profile_is_applied_after_existing_config_initialization(monkeypatch):
    # Isaac config imports require a running Kit. Replace only that boundary;
    # execute the real profile and verify its final configuration, not the stubs.
    import sys
    monkeypatch.delenv('M1_FIXED_WHEEL_SPEED_M_S', raising=False)
    monkeypatch.delenv('M1_FIXED_ABAD', raising=False)
    class Actions:
        def __init__(self):
            self.JointPositionAction = NS(joint_names=list(M1_ASSET_JOINT_NAMES), preserve_order=True)
    def existing_cfg():
        return NS(action_dim=8, m1_fixed_abad=True, m1_fixed_wheel_speed_m_s=.3,
                  commands=NS(base_velocity=NS(ranges=NS(), limit_ranges=NS())),
                  curriculum=NS(), scene=NS(robot=NS(init_state=NS(pos=(0., 0., .62)))),
                  actions=NS(JointPositionAction=NS(joint_names=['old'])))
    monkeypatch.setitem(sys.modules, 'ame_baseline.m1_ame_actions', NS(M1AmeActionsCfg=Actions))
    monkeypatch.setitem(sys.modules, 'ame_baseline.m1_ame_env_cfg', NS(M1AmeCrossLargeComplexEnvCfg=existing_cfg))
    from ame_baseline import m1_mixed_course
    monkeypatch.setattr(m1_mixed_course, 'configure_flat_first_terrain', lambda cfg: setattr(cfg, 'm1_flat_first', True))
    cfg = profile_module().build_teacher_student_env_cfg(training_phase='withdrawal')
    assert cfg.action_dim == 16 and cfg.m1_fixed_abad is False
    assert cfg.m1_fixed_wheel_speed_m_s is None
    assert isinstance(cfg.actions, Actions)
    assert cfg.actions.JointPositionAction.joint_names == list(M1_ASSET_JOINT_NAMES)
    assert cfg.m1_learning_stage_sequence == (0, 3) and cfg.m1_flat_first
    assert cfg.m1_collision_cost_per_step == 2. and cfg.m1_collision_budget == 20.
    assert cfg.training_phase == 'withdrawal'
    assert cfg.m1_student_contract == contract_module().student_contract()
    for ranges in (cfg.commands.base_velocity.ranges, cfg.commands.base_velocity.limit_ranges):
        assert (ranges.lin_vel_x, ranges.lin_vel_y, ranges.ang_vel_z) == ((.3, .3), (0., 0.), (0., 0.))
    assert cfg.commands.base_velocity.heading_command is False
    assert cfg.commands.base_velocity.rel_standing_envs == 0.
    assert cfg.curriculum.lin_vel_cmd_levels is None


def bare_runner(phase):
    from ame_baseline.ame_runner import AmeOnPolicyRunner
    actor = torch.nn.Linear(2, 16)
    actor.std = torch.nn.Parameter(torch.ones(16))
    actor.map_dim, actor.actor_state_dim, actor.critic_state_dim = 4, 2, 3
    runner = object.__new__(AmeOnPolicyRunner)
    runner.alg = NS(actor_critic=actor, optimizer=torch.optim.Adam(actor.parameters()))
    runner.device = 'cpu'
    runner.empirical_normalization = False
    runner.current_learning_iteration = 4
    runner.logger_type = 'tensorboard'
    runner.env = NS(unwrapped=NS(cfg=NS(m1_student_contract=contract_module().student_contract(),
        training_phase=phase, m1_training_contract=profile_module().student_training_contract())))
    return runner


def test_runner_roundtrip_and_cross_phase_rejection_before_mutation(tmp_path):
    source = bare_runner('bc')
    path = tmp_path / 'student.pt'
    source.save(path)
    saved = torch.load(path, map_location='cpu', weights_only=False)
    assert saved['m1_student_contract'] == contract_module().student_contract()
    assert saved['training_phase'] == 'bc' and saved['ame_num_actions'] == 16
    resumed = bare_runner('bc')
    resumed.load(path)
    assert resumed.current_learning_iteration == 5
    for key, value in source.alg.actor_critic.state_dict().items():
        torch.testing.assert_close(resumed.alg.actor_critic.state_dict()[key], value)
    other = bare_runner('ppo')
    before = deepcopy(other.alg.actor_critic.state_dict())
    with pytest.raises(ValueError, match='phase'):
        other.load(path)
    assert not other.alg.optimizer.state
    for key, value in before.items():
        torch.testing.assert_close(other.alg.actor_critic.state_dict()[key], value)


def test_ppo_entry_requires_explicit_resume_and_phase():
    spec = importlib.util.spec_from_file_location('m1_train_entry', Path(__file__).parents[1] / 'scripts/train_m1_cross_large_complex_ame.py')
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    assert hasattr(entry, '_validate_student_training_request'), 'student PPO entry guard is missing'
    for resume, phase in [(False, 'ppo'), (True, 'bc'), (True, 'withdrawal'), (True, 'critic_calibration')]:
        with pytest.raises(ValueError):
            entry._validate_student_training_request(NS(training_profile='teacher_student_16_10cm', resume=resume, training_phase=phase))
    entry._validate_student_training_request(NS(training_profile='teacher_student_16_10cm', resume=True, training_phase='ppo'))
    entry._validate_student_training_request(NS(training_profile='legacy', resume=False, training_phase='ppo'))
