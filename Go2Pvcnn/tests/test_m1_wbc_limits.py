import importlib.util
from pathlib import Path
import numpy as np
import pytest


def module():
    p=Path(__file__).parents[1]/'ame_baseline/m1_wbc_limits.py'
    assert p.exists(), 'explicit speed and effort continuity policy missing'
    spec=importlib.util.spec_from_file_location('limits',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def test_speed_policy_uses_names_and_caps_unset_native_limits():
    legs=[f'leg{i}' for i in range(12)];wheels=[f'wheel{i}' for i in range(4)]
    names=(legs+wheels)[::-1]
    r=module().diagnostic_speed_limits(names=names,leg_names=legs,wheel_names=wheels,
        native_limits=np.full(16,5.9e36),leg_cap=.5,wheel_cap=20.)
    np.testing.assert_allclose(r,[20]*4+[.5]*12)


def test_effort_rate_intersects_limit_and_uses_previous_same_episode_tick():
    r=module().effort_step_bounds(previous=dict(command=np.array([9.99,-9.99]),
        step=7,episode=2,owner='explicit_total'),limits=[10,10],rate=[20,20],dt=.005,
        step=8,episode=2)
    np.testing.assert_allclose(r['lower'],[9.89,-10])
    np.testing.assert_allclose(r['upper'],[10,-9.89])


def test_qp_effort_interval_is_strictly_inside_hard_slew_interval_for_solver_tolerance():
    hard = dict(lower=np.array([-1., -2.]), upper=np.array([1., 2.]))
    interior = module().qp_effort_interior_bounds(bounds=hard, margin=1e-5)
    np.testing.assert_allclose(interior['lower'], [-.99999, -1.99999])
    np.testing.assert_allclose(interior['upper'], [.99999, 1.99999])
    assert np.all(interior['lower'] > hard['lower'])
    assert np.all(interior['upper'] < hard['upper'])
    with pytest.raises(ValueError, match='too narrow'):
        module().qp_effort_interior_bounds(
            bounds=dict(lower=np.array([0.]), upper=np.array([1e-5])), margin=1e-5)


@pytest.mark.parametrize('change',[{'step':6},{'episode':1},{'owner':'implicit_estimate'},
                                  {'command':np.array([11.,0.])}])
def test_unknown_stale_or_out_of_limit_previous_effort_rejected(change):
    previous=dict(command=np.zeros(2),step=7,episode=2,owner='explicit_total')|change
    with pytest.raises(ValueError):
        module().effort_step_bounds(previous=previous,limits=[10,10],rate=[20,20],
            dt=.005,step=8,episode=2)


def test_missing_history_cannot_initialize_from_zero_implicitly():
    with pytest.raises(ValueError):
        module().effort_step_bounds(previous=None,limits=[10,10],rate=[20,20],
            dt=.005,step=0,episode=2)


def test_native_probe_reports_force_sources_and_diagnostic_speed_policy():
    s=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert 'M1_WBC_EFFORT_SOURCES ' in s
    assert 'get_dof_projected_joint_forces()' in s
    assert 'diagnostic_speed_limits(' in s
    import ast
    assert any(alias.name=='M1_WHEEL_SPEED_LIMIT_RAD_S'
               for node in ast.walk(ast.parse(s)) if isinstance(node,ast.ImportFrom)
               for alias in node.names)
