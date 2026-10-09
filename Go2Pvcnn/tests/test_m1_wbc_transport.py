import importlib.util
from pathlib import Path
import numpy as np
import pytest


def transport():
    p=Path(__file__).parents[1]/'ame_baseline/m1_wbc_transport.py'
    assert p.exists(), 'moving contact evaluation-point derivative missing'
    s=importlib.util.spec_from_file_location('transport',p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m.contact_acceleration_bias


def circular():
    z=np.zeros((1,3)); omega=np.array([[0.,2.,0.]])
    arm=np.array([[0.,0.,-.1]])
    return dict(com_bias=z.copy(),angular_bias=z.copy(),omega=omega,arm=arm,
        material_velocity=z.copy(),geometry_velocity=np.array([[.2,0.,0.]]))


def test_smooth_pure_rolling_cancels_material_centripetal_bias():
    r=transport()(**circular())
    np.testing.assert_allclose(r['material_bias'],[[0.,0.,.4]],atol=1e-12)
    np.testing.assert_allclose(r['transport_bias'],[[0.,0.,-.4]],atol=1e-12)
    np.testing.assert_allclose(r['total_bias'],0.,atol=1e-12)


def test_fixed_polygon_vertex_must_not_use_smooth_wheel_migration():
    d=circular(); d['geometry_velocity'][:]=0.
    r=transport()(**d)
    np.testing.assert_allclose(r['total_bias'],[[0.,0.,.4]],atol=1e-12)
    # Pivoting polygon needs a center acceleration, unlike a smooth circle.


def test_matches_independent_velocity_field_difference_with_slip():
    rng=np.random.default_rng(12); k=12
    c,p,v,w,a,alpha,vg=[rng.normal(size=(k,3)) for _ in range(7)]
    def field(t):
        return v+a*t+np.cross(w+alpha*t,p+vg*t-(c+v*t+.5*a*t*t))
    vm=field(0.); dt=1e-5
    expected=(field(dt)-field(-dt))/(2*dt)
    r=transport()(com_bias=a,angular_bias=alpha,omega=w,arm=p-c,
                  material_velocity=vm,geometry_velocity=vg)
    np.testing.assert_allclose(r['total_bias'],expected,atol=1e-8,rtol=0)


def test_common_translational_frame_velocity_does_not_change_bias():
    d=circular(); a=transport()(**d)
    d['material_velocity']+=3.; d['geometry_velocity']+=3.
    b=transport()(**d)
    np.testing.assert_allclose(a['total_bias'],b['total_bias'],atol=1e-12)


@pytest.mark.parametrize('fault',['nan','shape','missing'])
def test_invalid_or_missing_migration_is_not_silently_zero(fault):
    d=circular()
    if fault=='nan': d['geometry_velocity'][0,0]=np.nan
    elif fault=='shape': d['geometry_velocity']=np.zeros((2,3))
    else: del d['geometry_velocity']
    with pytest.raises((ValueError,TypeError)): transport()(**d)


def test_transported_constraint_permits_coupled_forward_and_wheel_acceleration():
    from test_m1_wbc_qp import solver, standing
    d=standing(); d['jac'][:]=0.
    for i in range(4):
        d['jac'][i,:,:3]=np.eye(3)
        d['jac'][i,0,6+i]=-.1
    r=transport()(**circular())
    d['contact_matrix']=d['jac'].reshape(-1,22)
    d['contact_rhs']=-np.tile(r['total_bias'],(4,1)).ravel()
    qdd=np.zeros(22); qdd[0]=.05; qdd[6:10]=.5
    d['accel_lower']=qdd.copy(); d['accel_upper']=qdd.copy()
    result=solver()(**d)
    assert result['valid'],result['reason']
    np.testing.assert_allclose(result['qdd'],qdd,atol=1e-5)
    # The tempting material-point a=0 constraint falsely rejects pure rolling.
    d['contact_rhs']=-np.tile(r['material_bias'],(4,1)).ravel()
    wrong=solver()(**d)
    assert not wrong['valid'] and wrong['effort'] is None
