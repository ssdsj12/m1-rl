import importlib.util
from pathlib import Path
import numpy as np
import pytest


def mode_adapter():
    p=Path(__file__).parents[1]/'ame_baseline/m1_wbc_modes.py'
    assert p.exists(), 'explicit attach/release mode adapter missing'
    s=importlib.util.spec_from_file_location('modes',p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m.contact_mode_constraints


def pair():
    j=np.zeros((2,3,22)); j[:,:,:3]=np.eye(3)
    # Two polygon vertices: x=-.05 and+.05 at z=-.1. Wheel axis worldY.
    j[:,0,6]=-.1; j[:,2,6]=[.05,-.05]
    return dict(jac=j,frames=np.tile(np.eye(3),(2,1,1)),bias=np.zeros((2,3)),
        attached=np.array([False,True]),normal_max=np.full(2,500.),
        separation_accel_min=np.zeros(2))


def test_release_keeps_normal_nonpenetration_but_has_zero_force_capacity():
    r=mode_adapter()(**pair())
    assert r['normal_max'].tolist()==[0.,500.]
    assert r['contact_matrix'].shape==(3,22)
    assert r['separation_matrix'].shape==(1,22)
    np.testing.assert_allclose(r['separation_matrix'][0],pair()['jac'][0,2])


def test_bias_is_subtracted_for_both_attached_and_released_points():
    d=pair(); d['bias'][:]=[1.,2.,3.]; d['separation_accel_min'][0]=.2
    r=mode_adapter()(**d)
    np.testing.assert_allclose(r['contact_rhs'],[-1.,-2.,-3.])
    np.testing.assert_allclose(r['separation_lower'],[-2.8])


def test_forward_polygon_pivot_is_feasible_only_with_rear_point_release():
    from test_m1_wbc_qp import solver,standing
    args=pair(); mode=mode_adapter()(**args)
    d=standing(); d.update(jac=args['jac'],frames=args['frames'],mu=np.full(2,.6),
        normal_min=np.zeros(2),normal_max=mode['normal_max'])
    qdd=np.zeros(22); qdd[0]=.05; qdd[2]=.025; qdd[6]=.5
    d.update(accel_lower=qdd.copy(),accel_upper=qdd.copy(),
        **{key:value for key,value in mode.items() if key!='normal_max'})
    r=solver()(**d)
    assert r['valid'],r['reason']
    np.testing.assert_allclose(r['force'][0],0.,atol=1e-5)
    assert r['force'][1,2]>390
    assert (args['jac'][0]@r['qdd'])[2]>.049
    args['attached'][:]=True
    d.update(mode_adapter()(**args))
    locked=solver()(**d)
    assert not locked['valid'] and locked['effort'] is None


@pytest.mark.parametrize('fault',['mask','normal','bias','capacity','lower'])
def test_invalid_modes_reject(fault):
    d=pair()
    if fault=='mask': d['attached']=np.array([0,1])
    elif fault=='normal': d['frames'][0,2,2]=2.
    elif fault=='bias': d['bias'][0,0]=np.nan
    elif fault=='capacity': d['normal_max'][0]=-1.
    else: d['separation_accel_min']=np.zeros(1)
    with pytest.raises(ValueError): mode_adapter()(**d)
