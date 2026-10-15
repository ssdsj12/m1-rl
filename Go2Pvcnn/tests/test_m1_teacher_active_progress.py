"""Real v27 support-limited transactions must not throttle active IK progress."""
import json
from pathlib import Path
import pytest
import torch
from ame_baseline.m1_reference_teacher import ReferenceTeacher,TeacherConfig,TeacherState
from ame_baseline.m1_teacher_feedback import BodyFeedbackConfig
from scripts.probe_m1_teacher import _dynamic_unpack,diagnostic_json

@pytest.mark.parametrize('frame',[122,137,150])
def test_real_support_limited_transaction_allows_active_progress(frame,monkeypatch):
    data=json.loads((Path(__file__).parent/'fixtures/m1_v27_active_progress.json').read_text())
    config=dict(data['config']);config['feedback']=BodyFeedbackConfig(**config['feedback'])
    teacher=ReferenceTeacher(TeacherConfig(**config))
    r=next(r for r in data['cases'] if r['frame']==frame)
    c=r['dynamic_support'];teacher._rows=[_dynamic_unpack(c['pre'],'cpu')]
    state=TeacherState(**_dynamic_unpack(c['input'],'cpu'))
    # Explicit zero-delta v33 test transition, not reconstructed old capture history.
    teacher._rows[0]['support_capture_root_z']=state.root_pos_w[:,2].clone()
    from scripts.probe_m1_teacher import observe_feedback_transactions,feedback_context_for
    observe_feedback_transactions(teacher)
    out=teacher._step_row(state,0,None)
    d=diagnostic_json(out.diagnostic[0].tolist())
    assert bool(out.valid[0])
    assert d.get('execution_active_fraction',d['execution_fraction'])>d['execution_fraction']
    from ame_baseline import m1_teacher_active_progress as progress
    with monkeypatch.context() as patch:
        patch.setattr(progress,'improve_active_progress',lambda target,baseline,*args:(target,baseline))
        old_teacher=ReferenceTeacher(TeacherConfig(**config))
        old_teacher._rows=[_dynamic_unpack(c['pre'],'cpu')]
        old_teacher._rows[0]['support_capture_root_z']=state.root_pos_w[:,2].clone()
        old=old_teacher._step_row(state,0,None)
        old_d=diagnostic_json(old.diagnostic[0].tolist())
    # Active refinement must not change today's support solve. Its fraction
    # need not equal the historical v27 solve without heading feedback.
    assert d['execution_fraction']==old_d['execution_fraction']
    active=r['active_wheel']
    for j in range(12):
        if j//3!=active:
            assert d[f'attempted_q_{j}']==old_d[f'attempted_q_{j}']
    history_prefixes=('heave_','load_','height_','feedback_')
    for name in (key for key in d if key.startswith(history_prefixes)):
        assert d[name]==old_d[name]
    q=torch.tensor([d[f'attempted_q_{j}'] for j in range(12)])
    assert ((q-state.last_applied_leg_target[0]).abs()<=2.5*float(state.dt[0])).all()
    from ame_baseline.m1_reference_teacher import m1_action_targets
    from scripts.probe_m1_teacher import verify_execution_geometry
    decoded=m1_action_targets(out.action,state.default_joint_pos)
    old_decoded=m1_action_targets(old.action,state.default_joint_pos)
    support=torch.arange(12)//3!=active
    assert torch.equal(decoded[:,:12][:,support],old_decoded[:,:12][:,support])
    r['teacher_diagnostic']=d
    r['feedback_context']=feedback_context_for(teacher,state,0)
    r['applied_targets']=m1_action_targets(out.action,state.default_joint_pos)[0].tolist()
    verify_execution_geometry(r,TeacherConfig(**config),replay_backend='cpu')

@pytest.mark.parametrize('tampered',[1.1,0.,.5])
def test_geometry_audit_rejects_false_active_fraction(tampered):
    from scripts.probe_m1_teacher import verify_execution_geometry
    data=json.loads((Path(__file__).parent/'fixtures/m1_v27_active_progress.json').read_text())
    config=dict(data['config']);config['feedback']=BodyFeedbackConfig(**config['feedback'])
    r=data['cases'][0]
    r['teacher_diagnostic']['execution_active_fraction']=tampered
    with pytest.raises(ValueError):
        verify_execution_geometry(r,TeacherConfig(**config),replay_backend='cpu')

def active_case(active=0,mode=1):
    from ame_baseline.m1_teacher_ik import body_feet,solve_constrained_ik,IKConfig
    from ame_baseline.m1_teacher_execution_targets import ExecutionTarget
    q=torch.tensor([[0.,.3,-.6,0.,.3,-.6,0.,-.3,.6,0.,-.3,.6]])
    start=body_feet(q);goal=start.clone();goal[:,active,2]+=.01
    cfg=IKConfig();base=solve_constrained_ik(q,start,q,cfg)
    target=ExecutionTarget(goal,start.clone(),torch.tensor([mode]),torch.tensor([.01]))
    return q,cfg,base,target,torch.tensor([active])

@pytest.mark.parametrize('active',range(4))
def test_each_leg_boost_preserves_other_joints_and_residual(active):
    from ame_baseline.m1_teacher_active_progress import improve_active_progress
    from ame_baseline.m1_teacher_ik import body_feet
    q,cfg,base,target,leg=active_case(active)
    out,ik=improve_active_progress(target,base,q,q,leg,.02,cfg,torch.tensor([True]),lambda x:x.valid)
    assert out.active_fraction[0]>out.fraction[0]
    assert ik.valid.all()
    support=torch.arange(12)//3!=active
    assert torch.equal(ik.q[:,support],base.q[:,support])
    assert ((ik.q-q).abs()<=.05).all()
    assert (body_feet(ik.q)-out.body_step).norm(dim=-1).max()<=.0001

@pytest.mark.parametrize('mode',[0,2])
def test_non_lift_modes_return_original_objects(mode):
    from ame_baseline.m1_teacher_active_progress import improve_active_progress
    q,cfg,base,target,leg=active_case(mode=mode)
    out,ik=improve_active_progress(target,base,q,q,leg,.02,cfg,torch.tensor([True]),lambda x:pytest.fail('must not validate'))
    assert out is target and ik is base

@pytest.mark.parametrize('case',['ineligible','invalid_baseline','callback_reject','nan_goal'])
def test_no_promotion_when_any_gate_fails(case):
    from dataclasses import replace
    from ame_baseline.m1_teacher_active_progress import improve_active_progress
    q,cfg,base,target,leg=active_case()
    if case=='invalid_baseline':base=replace(base,valid=torch.tensor([False]))
    if case=='nan_goal':target.body_goal[:,0]=float('nan')
    eligible=torch.tensor([case!='ineligible'])
    out,ik=improve_active_progress(target,base,q,q,leg,.02,cfg,eligible,
        lambda x:torch.tensor([case!='callback_reject']))
    assert torch.equal(out.body_step,target.body_step)
    assert torch.equal(out.active_fraction,target.fraction)
    assert torch.equal(ik.q,base.q)
