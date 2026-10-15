"""Catch missing/reversed yaw feedback without prescribing an active swing."""
import math
import pytest
import torch
from ame_baseline.m1_teacher_execution_targets import execution_targets
from ame_baseline.m1_teacher_pose import BodyPose, PoseReference, _rotation
from test_m1_teacher_execution_targets import fixture


@pytest.mark.parametrize('dtype', [torch.float32, torch.float64])
@pytest.mark.parametrize('active', range(4))
@pytest.mark.parametrize('yaw,command_yaw,want', [
    (.1, 0., .05), (-.1, 0., -.05), (.02, 0., .02),
    (0., .02, -.02), (.1, .1, 0.),
    (math.pi-.01, -math.pi+.01, -.02),
])
def test_support_heading_signed_bounded_world_response(dtype, active, yaw, command_yaw, want):
    q, cmd, measured = fixture(dtype)
    quat=lambda a: q.new_tensor([[math.cos(a/2), 0., 0., math.sin(a/2)]])
    cmd=PoseReference(BodyPose(cmd.body.pos_w, quat(command_yaw)), cmd.wheels_w)
    measured=BodyPose(measured.pos_w, quat(yaw))
    result=execution_targets(cmd, measured, torch.tensor([active]), q,
        q.new_tensor([.25]), torch.tensor([1]), support_reference_w_z=cmd.wheels_w[:,:,2])
    world=measured.pos_w[:,None]+torch.einsum('bij,bkj->bki', _rotation(measured.quat_w), result.body_goal)
    # Independent analytic XY rotation of wheel vectors about the measured root.
    relative=cmd.wheels_w-cmd.body.pos_w[:,None]
    expected=relative.clone()
    expected[:,:,0]=math.cos(want)*relative[:,:,0]-math.sin(want)*relative[:,:,1]
    expected[:,:,1]=math.sin(want)*relative[:,:,0]+math.cos(want)*relative[:,:,1]
    expected=expected+measured.pos_w[:,None]
    expected[:,:,2]=cmd.wheels_w[:,:,2]
    expected[:,active]=cmd.wheels_w[:,active]
    torch.testing.assert_close(world, expected, atol=2e-7, rtol=2e-6)
    torch.testing.assert_close(result.heading_delta, q.new_tensor([want]), atol=2e-7, rtol=2e-6)


@pytest.mark.parametrize('field', ['execution_heading_delta', 'execution_body_goal_3_y', 'execution_body_goal_3_z'])
def test_independent_heading_evidence_rejects_tamper(field):
    from test_m1_teacher_support_translation import evidence_sample
    p, teacher, sample = evidence_sample()
    assert 'execution_heading_delta' in sample['teacher_diagnostic']
    assert p.verify_feedback_transaction(sample, teacher.cfg) == []
    sample['teacher_diagnostic'][field] += .01
    with pytest.raises(ValueError):
        p.verify_execution_geometry(sample, teacher.cfg)


@pytest.mark.parametrize('mode,height', [(0,False),(1,False),(2,False),(2,True)])
def test_disabled_heading_retains_zero_diagnostic(mode,height):
    q,c,m=fixture()
    m=BodyPose(m.pos_w,q.new_tensor([[math.cos(.1),0.,0.,math.sin(.1)]]))
    kw={'support_reference_w_z':c.wheels_w[:,:,2]} if height else {}
    out=execution_targets(c,m,torch.tensor([0]),q,q.new_ones(1),torch.tensor([mode]),**kw)
    assert torch.equal(out.heading_delta,q.new_zeros(1))


@pytest.mark.parametrize('scale',[1.,1.0002])
def test_nonzero_yaw_evidence_uses_normalized_valid_quaternion(scale):
    from test_m1_teacher_support_translation import evidence_sample
    p,teacher,sample=evidence_sample(yaw=.02,quat_scale=scale)
    assert abs(sample['teacher_diagnostic']['execution_heading_delta'])>.001
    p.verify_execution_geometry(sample,teacher.cfg)


@pytest.mark.parametrize('frame',[115,120,125,128,134])
def test_actual_v30_input_heading_retains_original_execution_bounds(frame):
    import json
    from pathlib import Path
    from ame_baseline.m1_reference_teacher import ReferenceTeacher,TeacherConfig,TeacherState
    from ame_baseline.m1_teacher_feedback import BodyFeedbackConfig
    from scripts.probe_m1_teacher import _dynamic_unpack,diagnostic_json
    data=json.loads((Path(__file__).parent/'fixtures/m1_v30_heading.json').read_text())
    cfg=data['config'];cfg['feedback']=BodyFeedbackConfig(**cfg['feedback'])
    row=next(r for r in data['cases'] if r['frame']==frame)
    context=row['dynamic_support']
    state=TeacherState(**_dynamic_unpack(context['input'],'cpu'))
    teacher=ReferenceTeacher(TeacherConfig(**cfg))
    teacher._rows=[_dynamic_unpack(context['pre'],'cpu')]
    # Zero-delta v33 transition; not a replay of the unknown historical origin.
    teacher._rows[0]['support_capture_root_z']=state.root_pos_w[:,2].clone()
    out=teacher._step_row(state,0,None)
    d=diagnostic_json(out.diagnostic[0].tolist())
    assert out.valid.item()
    assert abs(d['execution_heading_delta'])<=.050000001
    assert all(d[f'ik_residual_m_{j}']<=.0001 for j in range(4))
    target=state.leg_pos.new_tensor([[d[f'attempted_q_{j}'] for j in range(12)]])
    assert ((target-state.last_applied_leg_target).abs()<=.0500001).all()


@pytest.mark.parametrize('measured_offset,command_offset',[(.02,.02),(.00735,.01525)])
def test_float32_wrap_roundoff_does_not_reject_geometry_evidence(measured_offset,command_offset):
    from ame_baseline.m1_teacher_ik import body_feet
    from test_m1_teacher_support_translation import evidence_sample
    p,teacher,sample=evidence_sample()
    q,cmd,m=fixture(torch.float32)
    quat=lambda a:q.new_tensor([[math.cos(a/2),0.,0.,math.sin(a/2)]])
    cq=quat(math.pi-command_offset);mq=quat(-math.pi+measured_offset)
    cmd=PoseReference(BodyPose(cmd.body.pos_w,cq),cmd.body.pos_w[:,None]+torch.einsum('bij,bkj->bki',_rotation(cq),body_feet(q)))
    m=BodyPose(cmd.body.pos_w,mq)
    target=execution_targets(cmd,m,torch.tensor([0]),q,q.new_ones(1),torch.tensor([1]),support_reference_w_z=cmd.wheels_w[:,:,2])
    d=sample['teacher_diagnostic'];c=sample['feedback_context']
    c.update(control_phase=2,execution_enabled=True,active_wheel=0,
             measured_root=m.pos_w[0].tolist(),measured_quat=mq[0].tolist(),last_applied_q=q[0].tolist())
    # A coherent rejected transaction is sufficient: it must still authenticate
    # producer geometry, without falsely claiming a physically valid action.
    for name in ('accepted_before','requested','retained_physical'):
        c[name]['wheels']=cmd.wheels_w[0].tolist()
    d.update(execution_mode=1,execution_fraction=1.,execution_active_fraction=1.,execution_intent_fraction=1.,
             execution_heading_delta=float(target.heading_delta[0]),reference_valid=0,load_enabled=1,height_enabled=1,heave_proposed=0.)
    d['height_origin']=float(m.pos_w[0,2])
    for axis,value in zip(('x','y','z','qw','qx','qy','qz'),torch.cat((cmd.body.pos_w,cq),-1)[0].tolist()):
        d['command_attempted_root_'+axis]=value
    for j in range(4):
        d[f'height_proposed_{j}']=float(cmd.wheels_w[0,j,2]);d[f'load_attempted_{j}']=0.
        d[f'execution_tolerance_m_{j}']=.0001
        d[f'ik_residual_m_{j}']=float((body_feet(q)-target.body_step).norm(dim=-1)[0,j])
        for k,axis in enumerate('xyz'):
            for prefix in ('command_attempted','attempted','accepted'):
                d[f'{prefix}_world_wheel_{j}_{axis}']=float(cmd.wheels_w[0,j,k])
            d[f'execution_body_goal_{j}_{axis}']=float(target.body_goal[0,j,k])
            d[f'execution_body_step_{j}_{axis}']=float(target.body_step[0,j,k])
    for j in range(12):d[f'attempted_q_{j}']=float(q[0,j])
    for name,points in (('start',body_feet(q)),('goal',target.body_goal),('solved',body_feet(q))):
        world=m.pos_w[:,None]+torch.einsum('bij,bkj->bki',_rotation(mq),points)
        d[f'execution_active_world_{name}_z']=float(world[0,0,2])
    p.verify_execution_geometry(sample,teacher.cfg)
    d['execution_heading_delta']+=.001
    with pytest.raises(ValueError):p.verify_execution_geometry(sample,teacher.cfg)
