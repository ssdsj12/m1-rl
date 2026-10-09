import importlib.util
from pathlib import Path
import numpy as np
import pytest


def adapter():
    path=Path(__file__).parents[1]/'ame_baseline/m1_wbc_contact_step.py'
    assert path.exists(), 'live velocity-step contact constraints missing'
    spec=importlib.util.spec_from_file_location('step',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m.contact_step_constraints


def data():
    j=np.zeros((2,3,22));j[0,:,:3]=np.eye(3);j[1,:,3:6]=np.eye(3)
    return dict(jac=j,frames=np.tile(np.eye(3),(2,1,1)),bias=np.zeros((2,3)),
        velocity=np.array([[.01,0,-.002],[0,0,-.003]]),gap=np.array([-.00001,.00002]),
        attached=np.array([True,False]),normal_max=np.array([100.,100.]),dt=.005)


def test_attached_velocity_converges_and_gap_recovers_in_semiimplicit_step():
    d=data();r=adapter()(**d)
    acc=np.linalg.lstsq(r['contact_matrix'],r['contact_rhs'],rcond=None)[0]
    predicted=d['velocity']+d['dt']*(d['jac']@acc+d['bias'])
    np.testing.assert_allclose(predicted[0],[0,0,.002],atol=1e-12)
    assert abs(d['gap'][0]+d['dt']*predicted[0,2])<1e-12


def test_attached_tangent_slip_is_corrected_over_explicit_horizon():
    from ame_baseline.m1_wbc_contact_step import contact_step_constraints
    jac=np.zeros((1,3,22));jac[0,:,:3]=np.eye(3)
    result=contact_step_constraints(jac=jac,frames=np.eye(3)[None],
        bias=np.zeros((1,3)),velocity=np.array([[.005,-.006,0.]]),
        gap=np.zeros(1),attached=np.array([True]),normal_max=np.array([500.]),
        dt=.001,tangent_velocity_time_constant=.02)
    np.testing.assert_allclose(result['contact_rhs'],[-.25,.30,0.],atol=1e-12)
    # The stabilized no-slip correction must not demand that small measured
    # velocity residuals disappear inside a single 1 ms physics tick.
    next_velocity=np.array([[.005,-.006,0.]])+.001*result['contact_rhs'].reshape(1,3)
    np.testing.assert_allclose(next_velocity,[[.00475,-.00570,0.]],atol=1e-12)


@pytest.mark.parametrize('horizon',[0.,-0.1,float('nan')])
def test_invalid_tangent_velocity_horizon_is_rejected(horizon):
    from ame_baseline.m1_wbc_contact_step import contact_step_constraints
    d=data()
    with pytest.raises(ValueError,match='tangent velocity time constant'):
        contact_step_constraints(**d,tangent_velocity_time_constant=horizon)


def test_released_point_has_zero_force_and_bounded_predicted_gap():
    d=data();d['bias'][1,2]=.1;r=adapter()(**d)
    acc=np.linalg.lstsq(r['separation_matrix'],r['separation_lower'],rcond=None)[0]
    next_v=d['velocity']+d['dt']*(d['jac']@acc+d['bias'])
    assert abs(d['gap'][1]+d['dt']*next_v[1,2])<1e-12
    np.testing.assert_allclose(r['normal_max'],[100,0])


def test_invalid_dt_and_missing_motion_are_rejected():
    for dt in (0.,-1.,float('nan')):
        d=data();d['dt']=dt
        with pytest.raises(ValueError): adapter()(**d)
    d=data();d['velocity'][0,0]=float('nan')
    with pytest.raises(ValueError): adapter()(**d)


def test_live_probe_uses_full_bias_and_no_velocity_reset():
    s=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert 'M1_WBC_LIVE_STEP ' in s
    assert "bias=native['bias'][0]" in s
    assert 'contact_step_constraints(' in s
    assert 'kinematic_bias(kinematic_model' in s


def test_normal_only_ablation_is_explicitly_not_a_rolling_controller():
    from ame_baseline.m1_wbc_contact_step import normal_only_contact_step_constraints
    jac=np.zeros((1,3,22));jac[0,:,:3]=np.eye(3)
    frames=np.eye(3)[None]
    bias=np.array([[1.,2.,3.]])
    velocity=np.array([[0.4,-0.2,0.]])
    result=normal_only_contact_step_constraints(jac=jac,frames=frames,bias=bias,
        velocity=velocity,gap=np.zeros(1),attached=np.array([True]),
        normal_max=np.array([500.]),dt=.01)
    assert result['contact_matrix'].shape==(1,22)
    np.testing.assert_allclose(result['contact_matrix'][0],jac[0,2])
    np.testing.assert_allclose(result['contact_rhs'],[-3.])


def test_pd_handoff_probe_executes_baseline_and_keeps_ablation_counterfactual():
    source=(Path(__file__).parents[1]/'scripts/probe_m1_wbc_pd_handoff.py').read_text()
    assert 'welded = contact_step_constraints(**measured)' in source
    assert 'normal_only_contact_step_constraints(' in source


def test_pd_handoff_probe_uses_transported_rolling_rows_as_active_model():
    source=(Path(__file__).parents[1]/'scripts/probe_m1_wbc_pd_handoff.py').read_text()
    assert 'rolling = rolling_contact_step_constraints(' in source
    assert 'geometry_velocity = smooth_wheel_geometry_velocity(' in source
    assert 'geometry_velocity=geometry_velocity' in source
    assert 'return rolling' in source
    assert 'rolling_tangent_axis_ablation_not_applied' in source
    assert 'unbounded_effort_shadow_not_applied' in source
    assert 'base_priority_shadow_not_applied' in source
    assert 'forced_target_x_shadow_not_applied' in source
    assert 'safety_then_x_priority_shadow_not_applied' in source
    assert 'forced_target_x_native_effort_shadow_not_applied' in source
    assert 'support_then_x_shadow_not_applied' in source
    assert 'support_indices = np.asarray([1, 2, 3, 4, 5]' in source
    assert '--tangent_velocity_time_constant' in source
    assert 'tangent_velocity_time_constant=args.tangent_velocity_time_constant' in source


def test_rolling_contact_step_integrates_patch_migration_into_full_contact_rows():
    from ame_baseline.m1_wbc_contact_step import rolling_contact_step_constraints
    jac=np.zeros((1,3,22));jac[0,:,:3]=np.eye(3);jac[0,0,6]=-.1
    result=rolling_contact_step_constraints(jac=jac,frames=np.eye(3)[None],
        com_bias=np.zeros((1,3)),angular_bias=np.zeros((1,3)),
        omega=np.array([[0.,2.,0.]]),arm=np.array([[0.,0.,-.1]]),
        material_velocity=np.zeros((1,3)),geometry_velocity=np.array([[.2,0.,0.]]),
        velocity=np.zeros((1,3)),gap=np.zeros(1),attached=np.array([True]),
        normal_max=np.array([500.]),dt=.01)
    assert result['contact_matrix'].shape==(3,22)
    np.testing.assert_allclose(result['contact_matrix'],jac[0],atol=1e-12)
    np.testing.assert_allclose(result['contact_rhs'],0.,atol=1e-12)
    qdd=np.zeros(22);qdd[0]=.05;qdd[6]=.5
    np.testing.assert_allclose(result['contact_matrix']@qdd,result['contact_rhs'],atol=1e-12)


def test_contact_rows_project_to_local_tangent_and_normal_axes_without_changing_equation():
    from ame_baseline.m1_wbc_contact_step import project_contact_rows_to_local_frames
    angle=.37
    rotation=np.array([[np.cos(angle),-np.sin(angle),0.],
                       [np.sin(angle), np.cos(angle),0.],
                       [0.,0.,1.]])
    frames=rotation[None]
    jac=np.arange(66,dtype=np.float64).reshape(1,3,22)/17.
    rhs=np.array([[.3,-.2,.1]])
    local_jac,local_rhs=project_contact_rows_to_local_frames(
        jac=jac,frames=frames,rhs=rhs)
    np.testing.assert_allclose(local_jac[0],rotation.T@jac[0],atol=1e-12)
    np.testing.assert_allclose(local_rhs[0],rotation.T@rhs[0],atol=1e-12)
    qdd=np.linspace(-.4,.6,22)
    np.testing.assert_allclose(local_jac[0]@qdd-local_rhs[0],
        rotation.T@(jac[0]@qdd-rhs[0]),atol=1e-12,
        err_msg='projection must preserve the contact-equation residual')


def test_smooth_wheel_geometric_contact_velocity_is_center_velocity_tangent_to_surface():
    from ame_baseline.m1_wbc_contact_step import smooth_wheel_geometry_velocity
    center=np.array([[.2,.3,.4],[1.,2.,3.]])
    normals=np.array([[0.,0.,1.],[0.,1.,0.]])
    actual=smooth_wheel_geometry_velocity(center_velocity=center,normals=normals)
    np.testing.assert_allclose(actual,[[.2,.3,0.],[1.,0.,3.]])
