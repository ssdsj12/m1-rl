import numpy as np
import pytest
from ame_baseline import m1_wbc_contact_step as module


def preview(**kwargs):
    function=getattr(module,'near_contact_gap_constraints',None)
    assert callable(function), 'unloaded approaching points need a bounded gap preview'
    return function(**kwargs)


def data():
    jac=np.zeros((1,3,22));jac[0,:,:3]=np.eye(3)
    return dict(jac=jac,normals=np.array([[0.,0.,1.]]),
        material_bias=np.zeros((1,3)),velocity=np.array([[0.,0.,-.02]]),
        gap=np.array([.0001]),dt=.001,preview_steps=20)


def test_checks_every_substep_not_just_endpoint():
    d=data(); r=preview(**d)
    times=np.arange(1,21)*d['dt'];c=.5*times*(times+d['dt'])
    terminal_only=-(d['gap'][0]+times[-1]*d['velocity'][0,2])/c[-1]
    assert np.min(d['gap'][0]+times*d['velocity'][0,2]+c*terminal_only)<0
    actual=r['separation_lower'][0]
    assert actual>terminal_only
    assert np.min(d['gap'][0]+times*d['velocity'][0,2]+c*actual)>=-1e-12
    assert np.min(d['gap'][0]+times*d['velocity'][0,2]+c*(actual-.001))<0


def test_uses_material_bias_and_never_adds_fictitious_contact_force():
    d=data();baseline=preview(**d)
    d['material_bias'][0,2]=.4;actual=preview(**d)
    np.testing.assert_allclose(actual['separation_lower'],baseline['separation_lower']-.4)
    np.testing.assert_allclose(actual['separation_matrix'],d['jac'][:,2])
    assert set(actual)=={'separation_matrix','separation_lower'}


def test_one_step_matches_material_point_semiimplicit_nonpenetration():
    d=data();d['preview_steps']=1;d['material_bias'][0,2]=.13
    actual=preview(**d)
    np.testing.assert_allclose(actual['separation_lower'],(-d['gap']/d['dt']-d['velocity'][:,2])/d['dt']-.13)


@pytest.mark.parametrize('steps',[0,-1,1.5,True])
def test_rejects_invalid_preview_count(steps):
    d=data();d['preview_steps']=steps
    with pytest.raises(ValueError):preview(**d)


def test_empty_near_geometry_returns_empty_inequalities():
    actual=preview(jac=np.empty((0,3,22)),normals=np.empty((0,3)),
        material_bias=np.empty((0,3)),velocity=np.empty((0,3)),gap=np.empty(0),dt=.001,preview_steps=20)
    assert actual['separation_matrix'].shape==(0,22)
    assert actual['separation_lower'].shape==(0,)
