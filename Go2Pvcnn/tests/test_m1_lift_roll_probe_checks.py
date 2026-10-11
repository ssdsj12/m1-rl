"""Counterexamples for native placement measurements, not reward changes."""
import importlib
import torch
import pytest


def checker():
    name = 'ame_baseline.m1_lift_roll_probe_checks'
    assert importlib.util.find_spec(name) is not None, 'placement evidence checker missing'
    return importlib.import_module(name)


def frame(**overrides):
    values = dict(wheel_force=torch.tensor([[[0., 0., 100.]] * 4]),
                  bottom=torch.zeros(1, 4), ground=torch.zeros(1),
                  margin=torch.full((1, 4), .01), expected=torch.ones(1, 4, dtype=torch.bool),
                  nonwheel_force=torch.zeros(1, 3, 3), clearance=torch.tensor([.04]),
                  root_error=torch.zeros(1), angle_error=torch.zeros(1), joint_error=torch.zeros(1))
    values.update(overrides)
    return checker().assess_frame(**values)


def test_horizontal_side_contact_is_not_ground_support():
    result = frame(wheel_force=torch.tensor([[[100., 0., 0.]] * 4]))
    assert not result['ground_support']


@pytest.mark.parametrize('kwargs', [dict(bottom=torch.full((1, 4), .03)),
                                  dict(margin=torch.full((1, 4), -.001))])
def test_obstacle_top_or_side_is_not_flat_ground_support(kwargs):
    assert not frame(**kwargs)['ground_support']


def test_initial_collision_cannot_be_erased_by_later_clear_frames():
    history = checker().PlacementEvidence()
    history.record(frame(nonwheel_force=torch.ones(1, 3, 3)))
    for _ in range(8):
        history.record(frame())
    assert not history.result()['geometry_verified']


def test_pose_extruded_away_from_requested_sample_is_unverified():
    assert not frame(root_error=torch.tensor([.021]))['pose_verified']
    assert not frame(angle_error=torch.tensor([.10]))['pose_verified']
    assert not frame(joint_error=torch.tensor([.041]))['pose_verified']


def test_settling_support_failure_is_not_geometry_impossibility():
    history = checker().PlacementEvidence()
    for _ in range(8):
        history.record(frame(wheel_force=torch.zeros(1, 4, 3)))
    result = history.result()
    assert result['geometry_verified'] and not result['support_verified']
    assert not result['verified']


def test_ground_supported_pose_passes_after_settling():
    history = checker().PlacementEvidence()
    history.record(frame(wheel_force=torch.zeros(1, 4, 3)))
    for _ in range(5):
        history.record(frame())
    assert history.result()['verified']


def measured_frame(root=(.017, 0., -.013), joint=.057):
    return dict(frame(root_error=torch.tensor([.0214]),joint_error=torch.tensor([joint])),
                root_delta=[list(root)],joint_delta=[[joint]*12],
                root_quat=[[1.,0.,0.,0.]],requested_joints=[[0.]*12],
                physics_dt=.005)


def paired_result(actual, reference):
    assert hasattr(checker(), 'compare_placement'), 'paired loaded baseline comparator missing'
    return checker().compare_placement(actual, reference)


def test_loaded_common_mode_settling_is_not_obstacle_extrusion():
    frames=[measured_frame() for _ in range(8)]
    result=paired_result(frames,frames)
    assert result['verified'] and result['calibrated_pose_verified']
    assert not result['absolute_pose_verified']


def test_extra_pose_displacement_cannot_cancel_by_opposite_direction():
    ref=[measured_frame() for _ in range(8)]
    actual=[measured_frame(root=(-.017,0.,-.013)) for _ in range(8)]
    assert not paired_result(actual,ref)['calibrated_pose_verified']


@pytest.mark.parametrize('bad', ['unsupported','moving','rotating','collision','target','length',
                               'nan_quaternion','nan_dt','zero_dt'])
def test_invalid_baseline_never_certifies_candidate(bad):
    import copy
    actual=[measured_frame() for _ in range(8)]
    reference=copy.deepcopy(actual)
    if bad=='unsupported':
        reference[-1]['ground_support']=False
    elif bad=='moving':
        reference[-1]['root_delta'][0][0]+=.003
    elif bad=='rotating':
        import math
        for i in range(8):
            angle=.005*i
            reference[i]['root_quat'][0]=[math.cos(angle/2),0.,math.sin(angle/2),0.]
        actual=copy.deepcopy(reference)
    elif bad=='nan_quaternion':
        reference[-1]['root_quat'][0][0]=float('nan')
    elif bad=='nan_dt':
        reference[-1]['physics_dt']=float('nan')
    elif bad=='zero_dt':
        reference[-1]['physics_dt']=0.
    elif bad=='collision':
        reference[0]['geometry_verified']=False
    elif bad=='target':
        reference[0]['requested_joints'][0][0]=.1
    elif bad=='length':
        reference.pop()
    assert not paired_result(actual,reference)['verified']


def test_paired_calibration_preserves_early_collision_and_joint_extrusion():
    import copy
    ref=[measured_frame() for _ in range(8)]
    actual=copy.deepcopy(ref)
    actual[0]['geometry_verified']=False
    assert not paired_result(actual,ref)['verified']
    actual=copy.deepcopy(ref)
    actual[0]['joint_delta'][0][0]+=.041
    assert not paired_result(actual,ref)['calibrated_pose_verified']


def test_scaled_quaternions_do_not_hide_relative_angle():
    import math
    ref=[measured_frame() for _ in range(8)]
    actual=[measured_frame() for _ in range(8)]
    for a,b in zip(actual,ref):
        b['root_quat'][0]=[1.00009,0.,0.,0.]
        angle=math.radians(5.2)
        a['root_quat'][0]=[1.00009*math.cos(angle/2),0.,1.00009*math.sin(angle/2),0.]
    assert not paired_result(actual,ref)['calibrated_pose_verified']


@pytest.mark.parametrize('mode', ['empty','invalid_reference','candidate_failure','good','reference_only'])
def test_native_summary_distinguishes_invalid_fixture_from_layout_evidence(mode):
    assert hasattr(checker(),'summarize_native'), 'native evidence classification missing'
    recoveries=[dict(verified=True,baseline_valid=True,runtime_ready=True) for _ in range(96)]
    folds=[dict(verified=True,baseline_valid=True) for _ in range(120)]
    if mode=='empty':recoveries=[];folds=[]
    if mode=='invalid_reference':folds[0].update(verified=False,baseline_valid=False)
    if mode=='candidate_failure':folds[0]['verified']=False
    result=checker().summarize_native(recoveries,folds,reference_only=mode=='reference_only')
    assert result['accepted'] is (mode=='good')
    assert result['assessment']==dict(empty='incomplete',invalid_reference='inconclusive_fixture',
        candidate_failure='placement_failed',good='placement_verified',reference_only='controls_only')[mode]
