import importlib.util
from pathlib import Path
import numpy as np
import pytest


def bounds():
    p=Path(__file__).parents[1]/'ame_baseline/m1_wbc_joint_bounds.py'
    assert p.exists(), 'authored joint-state bound adapter missing'
    spec=importlib.util.spec_from_file_location('bounds',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m.joint_step_bounds


def test_velocity_and_position_intersection_not_fixed_acceleration_number():
    r=bounds()(position=[.99,0],velocity=[.1,-.1],position_limits=[[-1,1],[-1,1]],
               velocity_limits=[.5,.2],dt=.1)
    np.testing.assert_allclose(r['lower'],[-6,-1])
    np.testing.assert_allclose(r['upper'],[0,3],atol=1e-12)
    for a in (r['lower'],r['upper']):
        v=np.array([.1,-.1])+.1*a;q=np.array([.99,0])+.1*v
        assert (np.abs(v)<=np.array([.5,.2])+1e-12).all()
        assert (np.abs(q)<=1+1e-12).all()


def test_invalid_state_limits_or_dt_rejected_not_clipped():
    data=dict(position=[0.],velocity=[0.],position_limits=[[-1,1]],velocity_limits=[.5],dt=.005)
    for change in ({'dt':0},{'position':[2.]},{'velocity_limits':[-1.]},{'velocity':[float('nan')]}):
        with pytest.raises(ValueError): bounds()(**(data|change))


def test_probe_keeps_original_shadow_and_logs_authored_bound_comparison():
    s=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert 'M1_WBC_STATE_BOUNDS ' in s
    assert 'get_dof_max_velocities()' in s
    assert 'joint_step_bounds(' in s
    assert 'M1_WBC_AUTHORED_STEP ' in s
    assert 'M1_WBC_LIVE_STEP ' in s
