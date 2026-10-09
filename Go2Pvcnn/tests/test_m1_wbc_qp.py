import importlib.util
from pathlib import Path
import numpy as np
import pytest


def solver():
    p = Path(__file__).parents[1]/'ame_baseline/m1_wbc_qp.py'
    assert p.exists(), 'constrained WBC oracle missing'
    s = importlib.util.spec_from_file_location('m1_wbc_qp', p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m.solve_wbc


def standing():
    jac = np.zeros((4, 3, 22))
    for i, (x, y) in enumerate(((.3,.2),(.3,-.2),(-.3,.2),(-.3,-.2))):
        jac[i, :, :3] = np.eye(3)
        jac[i, :, 3:6] = [[0, 0, -y], [0, 0, x], [y, -x, 0]]
        jac[i, 2, 6+i] = 1
    h = np.zeros(22); h[2] = 392.4
    return dict(mass=np.eye(22), bias=h, jac=jac,
        frames=np.tile(np.eye(3), (4,1,1)), mu=np.full(4,.6),
        normal_min=np.full(4,30.), normal_max=np.full(4,200.),
        accel_lower=np.zeros(22), accel_upper=np.zeros(22),
        effort_lower=np.full(16,-120.), effort_upper=np.full(16,120.),
        contact_matrix=np.empty((0,22)), contact_rhs=np.empty(0), tasks=())


def test_balances_gravity_and_joint_reaction_without_clipping():
    r = solver()(**standing())
    assert r['valid'], r['reason']
    np.testing.assert_allclose(r['force'][:, 2], 98.1, atol=1e-4)
    np.testing.assert_allclose(r['effort'][:4], -98.1, atol=1e-4)
    assert r['max_violation'] <= 1e-5


def test_solver_binds_event_identity_to_both_valid_and_rejected_results():
    identity = dict(env_id=0, episode=4, step=8, phase='LIFT', leg='FBL', obstacle_id='obs-2')
    valid = solver()(**standing(), identity=identity)
    assert valid['valid'] and valid['identity'] == identity
    data = standing(); data['effort_lower'][:] = -.1; data['effort_upper'][:] = .1
    rejected = solver()(**data, identity=identity)
    assert not rejected['valid'] and rejected['identity'] == identity


def test_solver_rejects_malformed_event_identity():
    with pytest.raises(ValueError, match='identity'):
        solver()(**standing(), identity={'env_id': 0, 'step': 1})


def test_unilateral_acceleration_bound_cannot_be_overridden_by_task():
    d=standing(); d['accel_lower'][10]=-2; d['accel_upper'][10]=2
    a=np.eye(22)[[10]]
    d.update(separation_matrix=a,separation_lower=np.array([.3]),
             tasks=((a,np.array([-1.]),np.ones(1)),))
    r=solver()(**d)
    assert r['valid'],r['reason']
    assert .3-1e-5 <= r['qdd'][10] <= .3+1e-5
    d['accel_upper'][10]=.2
    r=solver()(**d)
    assert not r['valid'] and r['effort'] is None


def test_tangential_load_and_conservative_cone():
    data = standing(); data['bias'][0] = 20
    r = solver()(**data)
    assert r['valid'], r['reason']
    np.testing.assert_allclose(r['force'][:, 0].sum(), 20, atol=1e-4)
    assert np.all(np.linalg.norm(r['force'][:, :2], axis=1) <= .6*r['force'][:, 2]+1e-5)
    data['mu'][:] = .01
    r = solver()(**data)
    assert not r['valid'] and r['effort'] is None


@pytest.mark.parametrize('failure', ['no_support','effort_limit','slew_interval'])
def test_infeasible_returns_no_actuation(failure):
    d = standing()
    if failure == 'no_support':
        d.update(jac=np.empty((0,3,22)),frames=np.empty((0,3,3)),
                 mu=np.empty(0),normal_min=np.empty(0),normal_max=np.empty(0))
    elif failure == 'effort_limit':
        d['effort_lower'][:] = -50; d['effort_upper'][:] = 50
    else:
        d['effort_lower'][:] = -.1; d['effort_upper'][:] = .1
    r = solver()(**d)
    assert not r['valid']
    assert r['qdd'] is None and r['force'] is None and r['effort'] is None


def test_lower_priority_cannot_reverse_higher_priority_acceleration():
    d = standing()
    d['accel_lower'][10] = -2; d['accel_upper'][10] = 2
    a = np.eye(22)[[10]]
    d['tasks'] = ((a,np.array([1.]),np.ones(1)),(a,np.array([-1.]),np.ones(1)))
    r = solver()(**d)
    assert r['valid'], r['reason']
    assert abs(r['qdd'][10]-1) < 1e-5


@pytest.mark.parametrize('bad', ['nan','indefinite','frames','negative_mu','bounds'])
def test_bad_contract_is_not_solved(bad):
    d = standing()
    if bad == 'nan': d['bias'][0] = np.nan
    elif bad == 'indefinite': d['mass'][0,0] = -1
    elif bad == 'frames': d['frames'][0,0,0] = 2
    elif bad == 'negative_mu': d['mu'][0] = -.1
    else: d['effort_lower'][0] = 130
    with pytest.raises(ValueError): solver()(**d)


def test_contact_acceleration_equation_is_hard_even_against_task():
    d = standing()
    d['accel_lower'][10] = -2; d['accel_upper'][10] = 2
    a = np.eye(22)[[10]]
    d.update(contact_matrix=a,contact_rhs=np.array([.5]),
             tasks=((a,np.array([-1.]),np.ones(1)),))
    r = solver()(**d)
    assert r['valid'], r['reason']
    assert abs(r['qdd'][10]-.5) < 1e-5


def test_normal_force_capacity_is_hard():
    d = standing(); d['normal_max'][:] = 80
    r = solver()(**d)
    assert not r['valid'] and r['force'] is None


def test_no_contacts_is_valid_for_free_fall_not_static_support():
    d = standing()
    d.update(jac=np.empty((0,3,22)),frames=np.empty((0,3,3)),mu=np.empty(0),
             normal_min=np.empty(0),normal_max=np.empty(0))
    d['accel_lower'][2] = -400; d['accel_upper'][2] = 0
    r = solver()(**d)
    assert r['valid'], r['reason']
    assert r['force'].shape == (0,3)
    np.testing.assert_allclose(r['qdd'][2], -392.4, atol=1e-4)


def test_solved_status_does_not_bypass_independent_residual_check(monkeypatch):
    # Corrupt a genuine external solver result to exercise the trust boundary.
    import osqp
    original = osqp.OSQP.solve
    def corrupted(instance):
        result = original(instance)
        result.x[22] += 1
        return result
    monkeypatch.setattr(osqp.OSQP, 'solve', corrupted)
    r = solver()(**standing())
    assert not r['valid'] and r['effort'] is None
    assert r['reason'] == 'independent_constraint_check'


def test_group_load_floor_is_per_wheel_not_per_contact_point():
    d = standing()
    d.update(jac=np.repeat(d['jac'],2,axis=0),frames=np.tile(np.eye(3),(8,1,1)),
             mu=np.full(8,.6),normal_min=np.zeros(8),normal_max=np.full(8,60.),
             group_ids=np.repeat(np.arange(4),2),group_min=np.full(4,90.),
             group_max=np.full(4,110.))
    r = solver()(**d)
    assert r['valid'],r['reason']
    np.testing.assert_allclose(r['force'][:,2].reshape(4,2).sum(1),98.1,atol=1e-4)
    d['group_min'][:] = 105.
    r = solver()(**d)
    assert not r['valid'] and r['effort'] is None


def test_solver_carries_explicit_native_joint_order_on_valid_and_rejected_output():
    names = tuple(f'native_joint_{i}' for i in range(16))
    solved = solver()(**standing(), joint_names=names)
    assert solved['valid']
    assert solved['joint_names'] == names
    infeasible = standing()
    infeasible['normal_max'][:] = 80.
    rejected = solver()(**infeasible, joint_names=names)
    assert not rejected['valid']
    assert rejected['joint_names'] == names
    with pytest.raises(ValueError, match='joint_names'):
        solver()(**standing(), joint_names=names[:-1] + (names[0],))


def test_slew_limited_handoff_can_use_bounded_transient_acceleration():
    d = standing()
    d['bias'][0] = 20.0
    d['mu'][:] = 0.0
    expected_effort = np.zeros(16)
    expected_effort[:4] = -98.1
    d['effort_lower'][:] = expected_effort
    d['effort_upper'][:] = expected_effort
    d['accel_lower'][0] = -25.0
    d['accel_upper'][0] = 25.0
    result = solver()(**d)

    assert result['valid'], result['reason']
    assert -25.0 <= result['qdd'][0] <= 25.0
    assert result['qdd'][0] < -19.9
    np.testing.assert_allclose(result['effort'], expected_effort, atol=1e-7)
