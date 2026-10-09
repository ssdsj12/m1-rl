import importlib.util
from pathlib import Path

import numpy as np
import pytest


def module():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_wbc_execution_adapter.py'
    assert path.exists(), 'grounded single-owner WBC execution adapter is missing'
    spec = importlib.util.spec_from_file_location('wbc_execution_adapter', path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class FakeView:
    def __init__(self, *, stiffness=None, damping=None, readback=None):
        self.stiffness = np.zeros((1, 16)) if stiffness is None else np.asarray(stiffness)
        self.damping = np.zeros((1, 16)) if damping is None else np.asarray(damping)
        self.readback = np.zeros((1, 16)) if readback is None else np.asarray(readback)
        self.projected = np.zeros((1, 16))

    def get_dof_stiffnesses(self):
        return self.stiffness

    def get_dof_dampings(self):
        return self.damping

    def get_dof_actuation_forces(self):
        return self.readback

    def get_dof_projected_joint_forces(self):
        return self.projected

    def get_dof_max_forces(self):
        return np.full((1, 16), 50.)


class FakeRobot:
    def __init__(self, view, *, corrupt_readback=False):
        self.data = type('Data', (), {'joint_pos': np.zeros((1, 16)),
            'joint_effort_limits': np.full((1, 16), 50.),
            'root_pos_w': np.zeros((1, 3)),
            'root_quat_w': np.array([[1., 0., 0., 0.]]),
            'root_vel_w': np.zeros((1, 6)),
            'joint_vel': np.zeros((1, 16))})()
        self.view = view
        self.joint_names = tuple(f'joint_{i}' for i in range(16))
        self.writes = 0
        self.corrupt_readback = corrupt_readback

    def set_joint_effort_target(self, command):
        self.command = np.asarray(command).copy()

    def write_data_to_sim(self):
        self.writes += 1
        self.view.readback = self.command.copy()
        if self.corrupt_readback:
            self.view.readback[0, 0] += .1

    def write_joint_stiffness_to_sim(self, value):
        self.view.stiffness = np.zeros((1, 16))

    def write_joint_damping_to_sim(self, value):
        self.view.damping = np.zeros((1, 16))


IDENTITY = dict(env_id=0, episode=3, step=0, phase='STAND_INIT', leg=None, obstacle_id=None)


def solution(effort=None, identity=IDENTITY):
    tau = np.zeros(16) if effort is None else np.asarray(effort, dtype=float)
    return dict(valid=True, reason='solved', qdd=np.zeros(22), effort=tau,
                force=np.zeros((4, 3)), dynamics_residual=np.zeros(22),
                identity=dict(identity), joint_names=tuple(f'joint_{i}' for i in range(16)))


def apply(*, view=None, robot=None, sol=None, identity=None, expected=None,
          previous=None, step=0, dt=.001, sim_steps=None, physics_steps=None,
          effort_rate=None, effort_limits=None, residual_tolerance=.02,
          handoff=None, env=None):
    view = FakeView() if view is None else view
    robot = FakeRobot(view) if robot is None else robot
    identity = (IDENTITY | {'step': step}) if identity is None else identity
    expected = identity if expected is None else expected
    actual_sim_steps = step if sim_steps is None else sim_steps
    actual_physics_steps = step if physics_steps is None else physics_steps
    actual_env = env
    if actual_env is None:
        actual_env = type('Env', (), {'num_envs': 1,
            'sim': type('Sim', (), {'current_time_step_index': actual_sim_steps,
                                    'current_time': actual_sim_steps * dt})()})()
    kwargs = dict(env=actual_env,
        robot=robot, view=view, solution=solution(identity=identity) if sol is None else sol,
        identity=identity, expected_identity=expected,
        previous=previous, step=step, physics_steps=actual_physics_steps, dt=dt,
    )
    if handoff is not None:
        kwargs['handoff'] = handoff
    if effort_rate is not None:
        kwargs['effort_rate'] = effort_rate
    if effort_limits is not None:
        kwargs['effort_limits'] = effort_limits
    if residual_tolerance != .02:
        kwargs['residual_tolerance'] = residual_tolerance
    return module().apply_wbc_command(**kwargs)


def capture_handoff(*, view=None, robot=None, step=8, dt=.001):
    view = FakeView(stiffness=np.full((1, 16), 800.), damping=np.full((1, 16), 40.)) if view is None else view
    robot = FakeRobot(view) if robot is None else robot
    identity = IDENTITY | {'step': step}
    env = type('Env', (), {'num_envs': 1,
        'sim': type('Sim', (), {'current_time_step_index': step,
                                'current_time': step * dt})()})()
    return module().capture_pd_handoff(env=env, robot=robot, view=view,
        identity=identity, expected_identity=identity, step=step,
        physics_steps=step, dt=dt), env, robot, view, identity


def test_fresh_zero_pd_initial_command_is_written_and_read_back_before_first_tick():
    result = apply(sol=solution(np.full(16, .01)))
    assert result['record']['owner'] == 'explicit_total'
    assert result['record']['step'] == 0
    assert result['record']['episode'] == 3
    assert result['readback_error'] == 0


@pytest.mark.parametrize('change', [
    {'valid': False}, {'qdd': np.zeros(21)}, {'effort': np.full(16, np.nan)},
    {'dynamics_residual': np.full(22, .021)},
])
def test_invalid_or_inconsistent_wbc_solution_is_rejected_before_actuator_write(change):
    candidate = solution() | change
    view = FakeView()
    robot = FakeRobot(view)
    with pytest.raises(ValueError):
        apply(view=view, robot=robot, sol=candidate)
    assert robot.writes == 0


@pytest.mark.parametrize('drive', ['stiffness', 'damping'])
def test_initialization_rejects_nonfresh_tick_or_any_pd_drive(drive):
    with pytest.raises(ValueError, match='previous'):
        apply(step=1)
    with pytest.raises(ValueError, match='fresh|simulation time'):
        apply(physics_steps=1, sim_steps=1)
    view = FakeView(**{drive: np.ones((1, 16))})
    robot = FakeRobot(view)
    with pytest.raises(ValueError, match='implicit'):
        apply(view=view, robot=robot)
    assert robot.writes == 0


def test_stale_identity_and_missing_previous_total_effort_reject_before_write():
    view = FakeView()
    robot = FakeRobot(view)
    with pytest.raises(ValueError, match='identity'):
        apply(view=view, robot=robot, expected=IDENTITY | {'step': 1})
    with pytest.raises(ValueError, match='previous'):
        apply(view=view, robot=robot, step=1,
              identity=IDENTITY | {'step': 1})
    assert robot.writes == 0


def test_continuous_command_enforces_slew_and_returns_real_readback_history():
    previous = dict(command=np.zeros(16), step=0, episode=3, owner='explicit_total')
    next_identity = IDENTITY | {'step': 1}
    result = apply(sol=solution(np.full(16, .01), next_identity), identity=next_identity,
                   expected=IDENTITY | {'step': 1}, previous=previous, step=1)
    assert result['record']['step'] == 1
    np.testing.assert_allclose(result['record']['command'], np.full(16, .01))
    view = FakeView()
    robot = FakeRobot(view)
    with pytest.raises(ValueError, match='max_slew_excess_nm'):
        apply(view=view, robot=robot, sol=solution(np.full(16, .03), next_identity),
              identity=next_identity, expected=next_identity,
              previous=previous, step=1)
    assert robot.writes == 0


def test_native_readback_mismatch_is_rejected_before_caller_can_advance_physics():
    view = FakeView()
    robot = FakeRobot(view, corrupt_readback=True)
    with pytest.raises(ValueError, match='max_error_nm'):
        apply(view=view, robot=robot, sol=solution(np.full(16, .01)))
    assert robot.writes == 1


def test_float32_native_effort_readback_rounding_is_accepted_with_micro_nm_tolerance():
    view = FakeView(stiffness=np.full((1, 16), 800.), damping=np.full((1, 16), 40.))
    view.projected[:] = 12.0
    handoff, env, robot, view, identity = capture_handoff(view=view)
    robot.data.joint_pos = np.zeros((1, 16), dtype=np.float32)
    requested = np.full(16, 12.0051234)

    result = apply(view=view, robot=robot, sol=solution(requested, identity),
        identity=identity, expected=identity, step=8, sim_steps=8, physics_steps=8,
        handoff=handoff, env=env)
    assert result['readback_error'] <= 1e-6
    assert result['readback_error'] > 1e-7
    assert np.any(view.stiffness == 0.) and robot.writes == 1


def test_wbc_feedback_target_uses_generalized_com_velocity_not_root_origin_velocity():
    helper = module().support_damping_target
    result = helper(
        root_com_velocity=np.array([.08, -.04, .02, .1, -.2, .3]),
        joint_velocity=np.full(16, .25),
        gain=2.0,
        linear_limit=.5,
        angular_limit=2.0,
        joint_limit=20.0)
    np.testing.assert_allclose(result[:3], [-.16, .08, -.04])
    np.testing.assert_allclose(result[3:6], [-.2, .4, -.6])
    np.testing.assert_allclose(result[6:], -.5)

def test_multi_environment_execution_is_rejected():
    view = FakeView()
    robot = FakeRobot(view)
    with pytest.raises(ValueError, match='exactly one'):
        module().apply_wbc_command(env=type('Env', (), {'num_envs': 8})(),
            robot=robot, view=view, solution=solution(), identity=IDENTITY,
            expected_identity=IDENTITY, previous=None, step=0, physics_steps=0,
            dt=.001)
    assert robot.writes == 0


def test_fresh_boundary_is_checked_against_native_simulation_clock_not_caller_counter():
    view = FakeView()
    robot = FakeRobot(view)
    with pytest.raises(ValueError, match='simulation time'):
        apply(view=view, robot=robot, sim_steps=1)
    assert robot.writes == 0


def test_first_command_must_obey_slew_from_measured_native_total_effort():
    view = FakeView()
    robot = FakeRobot(view)
    with pytest.raises(ValueError, match='slew'):
        apply(view=view, robot=robot, sol=solution(np.full(16, .03)))
    assert robot.writes == 0


def test_solution_identity_must_match_current_step_not_only_adapter_arguments():
    next_identity = IDENTITY | {'step': 1}
    previous = dict(command=np.zeros(16), step=0, episode=3, owner='explicit_total')
    with pytest.raises(ValueError, match='solution identity'):
        apply(sol=solution(np.full(16, .01), IDENTITY), identity=next_identity,
              expected=next_identity, previous=previous, step=1)


def test_caller_cannot_raise_effort_slew_limit_or_residual_tolerance():
    candidate = solution(np.full(16, .1))
    candidate['dynamics_residual'] = np.full(22, .1)
    view = FakeView()
    robot = FakeRobot(view)
    with pytest.raises((TypeError, ValueError)):
        apply(view=view, robot=robot, sol=candidate, effort_rate=np.full(16, 2000.),
              effort_limits=np.full(16, 500.), residual_tolerance=1.)
    assert robot.writes == 0


def test_native_effort_limits_not_caller_limits_bound_command():
    view = FakeView()
    robot = FakeRobot(view)
    with pytest.raises((TypeError, ValueError)):
        apply(view=view, robot=robot, sol=solution(np.full(16, 60.)),
              effort_limits=np.full(16, 1000.))
    assert robot.writes == 0
    with pytest.raises(ValueError, match='native effort limits'):
        apply(view=view, robot=robot, sol=solution(np.full(16, 60.)))
    assert robot.writes == 0


def test_same_tick_pd_handoff_uses_measured_projected_effort_and_disables_drives_atomically():
    view = FakeView(stiffness=np.full((1, 16), 800.), damping=np.full((1, 16), 40.))
    view.projected[:] = 2.
    handoff, env, robot, view, identity = capture_handoff(view=view)
    result = apply(view=view, robot=robot, sol=solution(np.full(16, 2.005), identity),
        identity=identity, expected=identity, step=8, sim_steps=8, physics_steps=8,
        handoff=handoff)
    assert result['record']['owner'] == 'explicit_total'
    assert result['record']['handoff_source'] == 'native_projected_pd'
    assert result['record']['step'] == 8
    assert np.count_nonzero(view.stiffness) == np.count_nonzero(view.damping) == 0
    np.testing.assert_allclose(result['record']['command'], np.full(16, 2.005))
    assert env.sim.current_time_step_index == 8


def test_handoff_rejects_changed_state_clock_gains_and_joint_order_before_disabling_pd():
    for mutate, match in (
        (lambda robot, view, env: robot.data.root_pos_w.__setitem__((0, 0), .01), 'state'),
        (lambda robot, view, env: setattr(env.sim, 'current_time_step_index', 9), 'native'),
        (lambda robot, view, env: view.stiffness.__setitem__((0, 0), 700.), 'gain'),
    ):
        handoff, env, robot, view, identity = capture_handoff()
        mutate(robot, view, env)
        with pytest.raises(ValueError, match=match):
            apply(view=view, robot=robot, sol=solution(np.full(16, .005), identity),
                identity=identity, expected=identity, step=8, sim_steps=8,
                physics_steps=8, handoff=handoff, env=env)
        assert np.any(view.stiffness) and robot.writes == 0
    handoff, env, robot, view, identity = capture_handoff()
    wrong_order = solution(np.full(16, .005), identity)
    wrong_order['joint_names'] = tuple(reversed(robot.joint_names))
    with pytest.raises(ValueError, match='joint order'):
        apply(view=view, robot=robot, sol=wrong_order, identity=identity,
            expected=identity, step=8, sim_steps=8, physics_steps=8, handoff=handoff)
    assert np.any(view.stiffness) and robot.writes == 0


def test_handoff_rejects_slew_mismatch_without_dropping_pd_support():
    view = FakeView(stiffness=np.full((1, 16), 800.), damping=np.full((1, 16), 40.))
    view.projected[:] = 2.
    handoff, env, robot, view, identity = capture_handoff(view=view)
    with pytest.raises(ValueError, match='slew'):
        apply(view=view, robot=robot, sol=solution(np.full(16, 2.03), identity),
            identity=identity, expected=identity, step=8, sim_steps=8,
            physics_steps=8, handoff=handoff)
    assert np.any(view.stiffness) and np.any(view.damping) and robot.writes == 0


def test_pd_handoff_acceleration_contract_is_finite_bounded_and_zero_preferred():
    contract = module().pd_handoff_acceleration_contract()

    lower = contract['accel_lower']
    upper = contract['accel_upper']
    tasks = contract['tasks']
    assert lower.shape == upper.shape == (22,)
    assert np.isfinite(lower).all() and np.isfinite(upper).all()
    assert np.all(lower < 0.) and np.all(upper > 0.)
    np.testing.assert_allclose(lower, -upper)
    assert np.max(np.abs(lower[:3])) <= 2.0
    assert np.max(np.abs(lower[3:6])) <= 8.0
    assert np.max(np.abs(lower[6:])) <= 100.0
    assert len(tasks) == 1
    task_a, task_b, task_w = tasks[0]
    np.testing.assert_allclose(task_a, np.eye(22))
    np.testing.assert_allclose(task_b, np.zeros(22))
    assert np.isfinite(task_w).all() and np.all(task_w > 0.)


def test_pd_handoff_acceleration_contract_accepts_only_bounded_feedback_target():
    target = np.zeros(22)
    target[0] = -.08
    target[4] = .12
    contract = module().pd_handoff_acceleration_contract(target_qdd=target)
    np.testing.assert_allclose(contract['tasks'][0][1], target)
    target[0] = -2.01
    with pytest.raises(ValueError, match='inside the hard acceleration envelope'):
        module().pd_handoff_acceleration_contract(target_qdd=target)
