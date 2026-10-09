import numpy as np
import pytest

from ame_baseline.m1_wbc_execution_adapter import pd_handoff_acceleration_contract
from ame_baseline.m1_wbc_qp import solve_wbc


def test_opt_in_base_priority_preserves_hard_envelope_and_default():
    target = np.linspace(-.1, .1, 22)
    old = pd_handoff_acceleration_contract(target_qdd=target)
    new = pd_handoff_acceleration_contract(target_qdd=target, base_priority=True)
    assert len(old['tasks']) == 1
    assert len(new['tasks']) == 2
    for key in ('accel_lower', 'accel_upper'):
        np.testing.assert_array_equal(new[key], old[key])
    np.testing.assert_array_equal(new['tasks'][0][0], np.eye(22)[:6])
    np.testing.assert_array_equal(new['tasks'][1][0], np.eye(22)[6:])
    np.testing.assert_array_equal(np.r_[new['tasks'][0][1], new['tasks'][1][1]], target)
    target[:] = 0
    assert np.any(new['tasks'][0][1])


def test_real_qp_joint_damping_does_not_override_reachable_base_target():
    # Positive definite coupled inertia: unactuated x obeys xdd+.5*qdd_j=-1.
    # Equal 22-DOF least squares accepts xdd=-.8 to avoid joint acceleration.
    # Base-first can meet xdd=0 at qdd_j=-2, within exactly the same bounds.
    mass = np.eye(22); mass[0, 6] = mass[6, 0] = .5
    bias = np.zeros(22); bias[0] = 1
    inputs = dict(mass=mass, bias=bias, jac=np.empty((0, 3, 22)),
                  frames=np.empty((0, 3, 3)), mu=np.empty(0),
                  normal_min=np.empty(0), normal_max=np.empty(0),
                  effort_lower=np.full(16, -10.), effort_upper=np.full(16, 10.),
                  contact_matrix=np.empty((0, 22)), contact_rhs=np.empty(0))
    old = solve_wbc(**inputs, **pd_handoff_acceleration_contract())
    assert old['valid'] and old['qdd'][0] < -.7
    new = solve_wbc(**inputs, **pd_handoff_acceleration_contract(base_priority=True))
    assert new['valid'], new['reason']
    assert abs(new['qdd'][0]) < 1e-5
    assert abs(new['qdd'][6] + 2) < 1e-5
    assert np.max(np.abs(new['dynamics_residual'])) < 1e-5


def test_base_priority_still_rejects_out_of_envelope_targets():
    target = np.zeros(22); target[0] = 2.01
    with pytest.raises(ValueError, match='inside the hard acceleration envelope'):
        pd_handoff_acceleration_contract(target_qdd=target, base_priority=True)
