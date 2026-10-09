import importlib.util
from pathlib import Path
import torch
import pytest
from extension.parallelism.m1_kinematics import m1_fk


def lift_function():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_single_lift.py'
    assert path.exists(), 'bounded single-leg lift missing'
    spec = importlib.util.spec_from_file_location('single_lift', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.lift_target


def inputs():
    root = torch.tensor([[0., 0., .554]]).repeat(4, 1)
    rpy = torch.zeros_like(root)
    joint = torch.tensor([[0., -.57, 1.1]*4]).repeat(4, 1)
    return dict(root=root, rpy=rpy, anchor_w=m1_fk(root, rpy, joint).foot_pos_w,
                selected_leg=torch.arange(4), previous_joint=joint,
                height=torch.zeros(4), force=torch.full((4, 4), 100.),
                tilt=torch.zeros(4, 2), tilt_rate=torch.zeros(4, 2),
                margin=torch.full((4,), .025), dt=.02)


def test_only_selected_wheel_target_rises_others_stay_fixed():
    args = inputs()
    result = lift_function()(**args)
    assert result['valid'].all(), result['reason']
    achieved = m1_fk(args['root'], args['rpy'], result['joint']).foot_pos_w
    delta = achieved - args['anchor_w']
    for row in range(4):
        assert 0 < result['height'][row].item() <= .0016001
        assert delta[row, row, 2].item() == pytest.approx(result['height'][row].item(), abs=1e-5)
        torch.testing.assert_close(delta[row, [i for i in range(4) if i != row]], torch.zeros(3, 3), atol=1e-5, rtol=0)
    assert ((result['joint'] - args['previous_joint']).abs() <= .010001).all()


def test_opt_in_retiming_reaches_clearance_and_returns_with_traverse_reserve():
    args=inputs(); fn=lift_function(); steps=0
    for target in (.16, 0.):
        for _ in range(200):
            previous=args['previous_joint'].clone()
            result=fn(**args,target_height=target,vertical_speed=.12)
            assert result['valid'].all(),result['reason']
            assert ((result['joint']-previous).abs()<=.010001).all()
            args['height'],args['previous_joint']=result['height'],result['joint']
            steps+=1
            if ((result['height']-target).abs()<1e-6).all():break
        else: pytest.fail('trajectory did not arrive')
    assert steps<=180, f'{steps} steps leaves insufficient nominal traverse reserve'


@pytest.mark.parametrize('speed',[0.,-.1,.121,float('nan'),float('inf')])
def test_invalid_retiming_speed_rejected(speed):
    with pytest.raises(ValueError,match='vertical_speed'):
        lift_function()(**inputs(),vertical_speed=speed)


def test_lift_preserves_accepted_unload_frame():
    from ame_baseline.m1_selected_world import selected_world_target
    args=inputs(); live=args['root'].clone(); live[:,2]-=.01
    corrected=selected_world_target(root=args['root'],rpy=args['rpy'],
        live_root=live,live_rpy=args['rpy'],target=args['anchor_w'],
        nominal=args['previous_joint'],previous=args['previous_joint'],
        selected=args['selected_leg'],dt=.1,vertical_only=True)
    assert corrected['valid'].all()
    # Finish the bounded unload correction before testing the phase handoff.
    for _ in range(3):
        corrected=selected_world_target(root=args['root'],rpy=args['rpy'],
            live_root=live,live_rpy=args['rpy'],target=args['anchor_w'],
            nominal=args['previous_joint'],previous=corrected['joint'],
            selected=args['selected_leg'],dt=.1,vertical_only=True,
            previous_frame=corrected['frame'])
        assert corrected['valid'].all()
    torch.testing.assert_close(corrected['frame']['root'],live)
    args['previous_joint']=corrected['joint']
    feedback=dict(live_root=live,live_rpy=args['rpy'],previous_frame=corrected['frame'],vertical_only=True)
    result=lift_function()(**args,world_feedback=feedback)
    assert result['valid'].all(),result['reason']
    assert (result['height']>0).all()
    assert ((result['joint']-args['previous_joint']).abs()<=.010001).all()
    torch.testing.assert_close(result['world_frame']['root'],live)


def test_controlled_lowering_preserves_stance_and_joint_slew():
    from extension.parallelism.m1_kinematics import m1_ik
    args=inputs(); args['height'].fill_(.05)
    raised=args['anchor_w'].clone();raised[torch.arange(4),torch.arange(4),2]+=.05
    args['previous_joint']=m1_ik(args['root'],args['rpy'],raised)[0].reshape(4,12)
    result=lift_function()(**args,target_height=0.)
    assert result['valid'].all()
    assert (result['height']<args['height']).all()
    assert ((result['joint']-args['previous_joint']).abs()<=.010001).all()
    actual=m1_fk(args['root'],args['rpy'],result['joint']).foot_pos_w
    for row in range(4):
        other=[leg for leg in range(4) if leg!=row]
        torch.testing.assert_close(actual[row,other],args['anchor_w'][row,other],atol=1e-5,rtol=0)


def test_contact_hold_does_not_continue_lowering():
    args=inputs()
    result=lift_function()(**args,target_height=0.,advance_mask=torch.zeros(4,dtype=torch.bool))
    assert result['valid'].all()
    torch.testing.assert_close(result['height'],args['height'])


@pytest.mark.parametrize('speed',[.08,.12])
def test_ground_search_is_slow_bounded_and_can_hold_contact(speed):
    args=inputs()
    for _ in range(40):
        old=args['height'].clone()
        result=lift_function()(**args,target_height=-.005,vertical_speed=speed)
        assert result['valid'].all()
        assert (result['height']>=-.005001).all()
        assert ((old-result['height'])<=.000201).all()
        args['height']=result['height'];args['previous_joint']=result['joint']
    torch.testing.assert_close(args['height'],torch.full((4,),-.005))
    held=lift_function()(**args,target_height=-.005,advance_mask=torch.zeros(4,dtype=torch.bool),vertical_speed=speed)
    torch.testing.assert_close(held['height'],args['height'])


def test_selected_contact_can_unload_but_other_support_loss_refuses():
    args = inputs()
    args['force'][torch.arange(4), torch.arange(4)] = 0
    assert lift_function()(**args)['valid'].all()
    args['force'][0, 1] = 0
    result = lift_function()(**args)
    assert not result['valid'][0]
    assert result['valid'][1:].all()
    torch.testing.assert_close(result['joint'][0], args['previous_joint'][0])
    assert result['height'][0] == 0


@pytest.mark.parametrize('field', ['tilt', 'tilt_rate', 'margin', 'nan'])
def test_unstable_or_missing_observations_fail_closed(field):
    args = inputs()
    if field == 'tilt': args['tilt'][0, 0] = .16
    if field == 'tilt_rate': args['tilt_rate'][0, 0] = .21
    if field == 'margin': args['margin'][0] = -.001
    if field == 'nan': args['margin'][0] = float('nan')
    result = lift_function()(**args)
    assert not result['valid'][0]
    assert result['valid'][1:].all()


def test_reaches_18cm_command_without_advancing_other_feet():
    args = inputs()
    for _ in range(200):
        result = lift_function()(**args)
        assert result['valid'].all(), result['reason']
        args['height'], args['previous_joint'] = result['height'], result['joint']
    torch.testing.assert_close(result['height'], torch.full((4,), .18))


def test_unreachable_anchor_is_not_accepted_as_finite_ik():
    args = inputs()
    args['anchor_w'][0, 0, 0] += 5
    result = lift_function()(**args)
    assert not result['valid'][0]
    assert result['valid'][1:].all()


def feedback_inputs(args):
    return dict(reference_root=args['root'].clone(), reference_rpy=args['rpy'].clone(),
                live_root=args['root'].clone(), live_rpy=args['rpy'].clone(),
                previous_root=args['root'].clone(), previous_rpy=args['rpy'].clone())


def feedback_function():
    import inspect
    fn = lift_function()
    assert 'pose_feedback' in inspect.signature(fn).parameters, 'pose feedback missing'
    return fn


def test_feedback_zero_error_preserves_original_target():
    args = inputs()
    expected = lift_function()(**args)
    actual = feedback_function()(**args, pose_feedback=feedback_inputs(args))
    torch.testing.assert_close(actual['joint'], expected['joint'])
    torch.testing.assert_close(actual['root'], args['root'])


def test_feedback_counters_sag_and_roll_without_integrating_drift():
    args = inputs()
    feedback = feedback_inputs(args)
    feedback['live_root'][:, 2] -= .006
    feedback['live_rpy'][:, 0] += .02
    fn = feedback_function()
    for _ in range(35):
        result = fn(**args, pose_feedback=feedback)
        assert result['valid'].all(), result['reason']
        assert ((result['joint'] - args['previous_joint']).abs() <= .010001).all()
        args['previous_joint'], args['height'] = result['joint'], result['height']
        feedback['previous_root'], feedback['previous_rpy'] = result['root'], result['rpy']
    torch.testing.assert_close(result['root'][:, 2], args['root'][:, 2] + .006)
    torch.testing.assert_close(result['rpy'][:, 0], torch.full((4,), -.02))


def test_feedback_large_pose_error_rejects_instead_of_unbounded_compensation():
    args = inputs()
    feedback = feedback_inputs(args)
    feedback['live_root'][0, 2] -= .1
    result = feedback_function()(**args, pose_feedback=feedback)
    assert not result['valid'][0]
    assert result['valid'][1:].all()
    torch.testing.assert_close(result['joint'][0], args['previous_joint'][0])


def test_support_hold_does_not_advance_height_or_block_other_rows():
    import inspect
    args = inputs()
    fn = lift_function()
    assert 'advance_mask' in inspect.signature(fn).parameters, 'support hold missing'
    result = fn(**args, advance_mask=torch.tensor([False, True, False, True]))
    assert result['valid'].all()
    torch.testing.assert_close(result['height'][[0, 2]], torch.zeros(2))
    assert (result['height'][[1, 3]] > 0).all()
    torch.testing.assert_close(result['joint'][[0, 2]], args['previous_joint'][[0, 2]], atol=1e-6, rtol=0)
