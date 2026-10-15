"""Actual v29 frames: retain feasible requested lift in the committed intent."""
import json
from pathlib import Path
import pytest
import torch
from ame_baseline.m1_reference_teacher import ReferenceTeacher, TeacherConfig, TeacherState
from ame_baseline.m1_teacher_feedback import BodyFeedbackConfig
from scripts.probe_m1_teacher import _dynamic_unpack

def replay(frame):
    data=json.loads((Path(__file__).parent/'fixtures/m1_v29_active_intent.json').read_text())
    config=data['config']; config['feedback']=BodyFeedbackConfig(**config['feedback'])
    row=next(r for r in data['cases'] if r['frame']==frame)
    c=row['dynamic_support']
    state=TeacherState(**_dynamic_unpack(c['input'],'cpu'))
    teacher=ReferenceTeacher(TeacherConfig(**config))
    teacher._rows=[_dynamic_unpack(c['pre'],'cpu')]
    # Zero-delta v33 transition tests this frozen solve, not historical continuity.
    teacher._rows[0]['support_capture_root_z']=state.root_pos_w[:,2].clone()
    out=teacher._step_row(state,0,None)
    return teacher,out,row

@pytest.mark.parametrize('frame',[125,128])
def test_feasible_active_intent_is_not_attenuated_by_support_beta(frame):
    teacher,out,row=replay(frame)
    assert bool(out.valid[0])
    requested=row['teacher_diagnostic']['dynamic_requested_z']
    accepted=teacher._rows[0]['accepted'].wheels_w[0,row['active_wheel'],2]
    assert abs(float(accepted)-requested)<=1e-6

@pytest.mark.parametrize('frame,expected',[(129,True),(133,True)])
def test_no_new_request_or_invalid_support_preserves_existing_gate(frame,expected):
    teacher,out,row=replay(frame)
    assert bool(out.valid[0])==expected
    if expected:
        accepted=teacher._rows[0]['accepted'].wheels_w[0,row['active_wheel'],2]
        assert abs(float(accepted)-row['teacher_diagnostic']['dynamic_requested_z'])<=1e-6


def test_heading_restores_feasible_134_without_relaxing_residual_gate():
    from scripts.probe_m1_teacher import diagnostic_json
    teacher,out,row=replay(134)
    assert bool(out.valid[0])
    d=diagnostic_json(out.diagnostic[0].tolist())
    for j in range(4):
        assert d[f'ik_residual_m_{j}']<=.0001
    assert abs(d['execution_heading_delta'])<=.050000001
    state=TeacherState(**_dynamic_unpack(row['dynamic_support']['input'],'cpu'))
    q=torch.tensor([[d[f'attempted_q_{j}'] for j in range(12)]])
    assert ((q-state.last_applied_leg_target).abs()<=.0500001).all()

@pytest.mark.parametrize('frame',[125,128])
def test_atomic_promotion_preserves_support_and_feedback(frame,monkeypatch):
    from ame_baseline import m1_teacher_active_intent as intent
    from ame_baseline.m1_reference_teacher import LEG_COLUMNS
    teacher,out,row=replay(frame)
    with monkeypatch.context() as patch:
        patch.setattr(intent,'improve_active_intent',lambda step,*args:step)
        previous,old,_=replay(frame)
    active=row['active_wheel']
    support=[LEG_COLUMNS[j] for j in range(12) if j//3!=active]
    assert torch.equal(out.action[:,support],old.action[:,support])
    a,b=teacher._rows[0],previous._rows[0]
    for key in ('support_load_offset','support_execution_z','support_heave','support_heave_error0'):
        assert torch.equal(a[key],b[key])
    assert torch.equal(a['feedback'].integral,b['feedback'].integral)
    assert torch.equal(a['feedback'].output,b['feedback'].output)
    assert torch.equal(a['accepted'].body.pos_w,b['accepted'].body.pos_w)
    assert torch.equal(a['accepted'].body.quat_w,b['accepted'].body.quat_w)
    other=[j for j in range(4) if j!=active]
    assert torch.equal(a['accepted'].wheels_w[:,other],b['accepted'].wheels_w[:,other])

@pytest.mark.parametrize('field,tampered',[
    ('execution_intent_fraction',0.),('execution_intent_fraction',1.1),
    ('execution_intent_fraction',.5),('execution_fraction',.5),
    ('command_attempted_world_wheel_0_z',.5),
    ('attempted_world_wheel_0_z',.5),('accepted_world_wheel_0_z',.5)])
@pytest.mark.parametrize('frame',[125,134])
def test_independent_audit_binds_intent_fraction(field,tampered,frame):
    from scripts.probe_m1_teacher import diagnostic_json,verify_execution_geometry,observe_feedback_transactions,feedback_context_for
    from ame_baseline.m1_reference_teacher import m1_action_targets
    data=json.loads((Path(__file__).parent/'fixtures/m1_v29_active_intent.json').read_text())
    config=data['config'];config['feedback']=BodyFeedbackConfig(**config['feedback'])
    row=next(r for r in data['cases'] if r['frame']==frame)
    state=TeacherState(**_dynamic_unpack(row['dynamic_support']['input'],'cpu'))
    teacher=ReferenceTeacher(TeacherConfig(**config))
    teacher._rows=[_dynamic_unpack(row['dynamic_support']['pre'],'cpu')]
    teacher._rows[0]['support_capture_root_z']=state.root_pos_w[:,2].clone()
    observe_feedback_transactions(teacher)
    out=teacher._step_row(state,0,None)
    row['teacher_diagnostic']=diagnostic_json(out.diagnostic[0].tolist())
    row['feedback_context']=feedback_context_for(teacher,state,0)
    row['applied_targets']=m1_action_targets(out.action,state.default_joint_pos)[0].tolist()
    verify_execution_geometry(row,teacher.cfg,replay_backend='cpu')
    row['teacher_diagnostic'][field]=tampered
    with pytest.raises(ValueError):
        verify_execution_geometry(row,teacher.cfg,replay_backend='cpu')

def synthetic(dtype=torch.float32):
    from ame_baseline.m1_teacher_pose import BodyPose,PoseReference,FeedbackReferenceStep
    from ame_baseline.m1_teacher_execution_targets import ExecutionTarget
    from ame_baseline.m1_teacher_ik import IKConfig,body_feet,solve_constrained_ik
    q=torch.tensor([[0.,.3,-.6,0.,.3,-.6,0.,-.3,.6,0.,-.3,.6]],dtype=dtype).repeat(3,1)
    body=BodyPose(torch.zeros(3,3,dtype=dtype),torch.tensor([[1.,0.,0.,0.]],dtype=dtype).repeat(3,1))
    feet=body_feet(q);goal=feet.clone();goal[:,0,2]+=.001
    old=PoseReference(body,feet);requested=PoseReference(body,goal)
    physical=PoseReference(body,feet+.01*(goal-feet))
    cfg=IKConfig();ik=solve_constrained_ik(q,feet,q,cfg)
    target=ExecutionTarget(physical.wheels_w,feet.clone(),torch.tensor([1,2,1]),torch.full((3,),.01,dtype=dtype))
    step=FeedbackReferenceStep(physical,physical,ik,ik,torch.zeros(3,3,dtype=dtype),
        torch.tensor([True,True,False]),torch.tensor([7,7,7]),torch.ones(3,dtype=torch.bool),target)
    return step,old,requested,body,q,cfg

@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_mixed_rows_promote_only_valid_crossing_and_preserve_support(dtype):
    from ame_baseline.m1_teacher_active_intent import improve_active_intent
    step,old,requested,body,q,cfg=synthetic(dtype)
    out=improve_active_intent(step,old,requested,body,torch.zeros(3,dtype=torch.long),q,q,q,.02,cfg,lambda ik,u:ik.valid)
    assert out.execution_target.intent_fraction[0]==1
    assert torch.equal(out.physical.wheels_w[0,0],requested.wheels_w[0,0])
    assert torch.equal(out.command_ik.q[:,3:],step.command_ik.q[:,3:])
    assert torch.equal(out.command_ik.q[1:],step.command_ik.q[1:])
    assert torch.equal(out.physical.wheels_w[1:],step.physical.wheels_w[1:])
    assert torch.equal(out.execution_target.intent_fraction[1:],step.execution_target.fraction[1:])

@pytest.mark.parametrize('case',['callback','no_request','nonfinite','nominal','branch'])
def test_rejected_refinement_retains_baseline(case):
    from ame_baseline.m1_teacher_active_intent import improve_active_intent
    from ame_baseline.m1_teacher_pose import PoseReference
    step,old,requested,body,q,cfg=synthetic()
    if case=='no_request':requested=old
    if case=='nonfinite':requested.wheels_w[:,0,2]=float('nan')
    if case=='nominal':requested.wheels_w[:,0,2]+=100
    branch=q.clone()
    if case=='branch':branch[:,2::3]*=-1
    out=improve_active_intent(step,old,requested,body,torch.zeros(3,dtype=torch.long),q,q,branch,.02,cfg,
        lambda ik,u:torch.zeros(3,dtype=torch.bool) if case=='callback' else ik.valid)
    assert torch.equal(out.physical.wheels_w,step.physical.wheels_w)
    assert torch.equal(out.command_ik.q,step.command_ik.q)
    assert torch.equal(out.execution_target.intent_fraction,step.execution_target.intent_fraction)
    assert_same_step(out,step)

def assert_same_step(a,b):
    from dataclasses import fields,is_dataclass
    if isinstance(a,torch.Tensor):assert torch.equal(a,b)
    elif is_dataclass(a):
        for field in fields(a):assert_same_step(getattr(a,field.name),getattr(b,field.name))
    else:assert a==b

@pytest.mark.parametrize('active',[0,1,2,3])
@pytest.mark.parametrize('mode',[0,1,2])
def test_all_legs_and_modes(active,mode):
    from dataclasses import replace
    from ame_baseline.m1_teacher_active_intent import improve_active_intent
    step,old,requested,body,q,cfg=synthetic()
    requested=replace(requested,wheels_w=old.wheels_w.clone())
    requested.wheels_w[:,active,2]+=.001
    physical=replace(old,wheels_w=old.wheels_w+.01*(requested.wheels_w-old.wheels_w))
    target=replace(step.execution_target,body_goal=physical.wheels_w,mode=torch.full((3,),mode))
    step=replace(step,physical=physical,command=physical,execution_target=target)
    out=improve_active_intent(step,old,requested,body,torch.full((3,),active),q,q,q,.02,cfg,lambda ik,u:ik.valid)
    if mode!=1:assert_same_step(out,step)
    else:
        assert out.execution_target.intent_fraction[0]==1
        other=[j for j in range(12) if j//3!=active]
        assert torch.equal(out.command_ik.q[:,other],step.command_ik.q[:,other])
        assert torch.equal(out.command_ik.q[2],step.command_ik.q[2])

def test_negligible_slew_never_changes_joint_command_or_claims_full_intent():
    from ame_baseline.m1_teacher_active_intent import improve_active_intent
    from ame_baseline.m1_teacher_ik import body_feet
    step,old,requested,body,q,cfg=synthetic()
    out=improve_active_intent(step,old,requested,body,torch.zeros(3,dtype=torch.long),q,q,q,1e-10,cfg,lambda ik,u:ik.valid)
    assert torch.equal(out.command_ik.q,q)
    assert out.execution_target.intent_fraction[0]<1
    assert (body_feet(out.command_ik.q)-out.execution_target.body_step).norm(dim=-1).max()<=.0001
