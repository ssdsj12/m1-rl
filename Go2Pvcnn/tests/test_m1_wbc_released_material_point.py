import numpy as np
from ame_baseline.m1_wbc_contact_step import rolling_contact_step_constraints


def case(attached):
    count=len(attached)
    jac=np.zeros((count,3,22)); jac[:,:,:3]=np.eye(3)
    jac[:,0,6]=-.1
    return dict(jac=jac,frames=np.tile(np.eye(3),(count,1,1)),
        com_bias=np.zeros((count,3)),angular_bias=np.zeros((count,3)),
        omega=np.tile([0.,2.,0.],(count,1)),arm=np.tile([0.,0.,-.1],(count,1)),
        material_velocity=np.zeros((count,3)),geometry_velocity=np.tile([.2,0.,0.],(count,1)),
        velocity=np.zeros((count,3)),gap=np.zeros(count),attached=np.asarray(attached),
        normal_max=np.full(count,500.),dt=.01)


def test_released_point_predicts_its_material_separation_not_migrating_patch():
    data=case([False])
    actual=rolling_contact_step_constraints(**data)
    # A material point at the bottom of a rolling wheel accelerates upward:
    # omega cross (omega cross arm) = [0,0,.4].  The geometric lowest
    # location moves to different material and has zero transported bias.
    np.testing.assert_allclose(actual['material_bias'],[[0.,0.,.4]],atol=1e-12)
    np.testing.assert_allclose(actual['total_bias'],0.,atol=1e-12)
    np.testing.assert_allclose(actual['separation_lower'],[-.4],atol=1e-12)
    assert actual['normal_max'].tolist()==[0.]
    assert actual['contact_matrix'].shape==(0,22)


def test_mixed_modes_keep_attached_transport_and_released_material_bias():
    actual=rolling_contact_step_constraints(**case([True,False]))
    np.testing.assert_allclose(actual['contact_rhs'],[0.,0.,0.],atol=1e-12)
    np.testing.assert_allclose(actual['separation_lower'],[-.4],atol=1e-12)
    assert actual['normal_max'].tolist()==[500.,0.]


def test_released_material_bound_still_prevents_predicted_penetration():
    data=case([False]); data['gap'][0]=-1e-5; data['velocity'][0,2]=-.002
    actual=rolling_contact_step_constraints(**data)
    qdd=np.zeros(22); qdd[2]=actual['separation_lower'][0]
    acceleration=data['jac'][0]@qdd+actual['material_bias'][0]
    next_v=data['velocity'][0]+data['dt']*acceleration
    next_gap=data['gap'][0]+data['dt']*next_v[2]
    assert abs(next_gap)<1e-12
