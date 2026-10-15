"""Catch lost submillimetre lift, wrong-leg tolerances and unsafe catchup."""
import pytest
import torch
from ame_baseline.m1_teacher_ik import body_feet, solve_constrained_ik, IKConfig
from ame_baseline.m1_teacher_pose import BodyPose, PoseReference, backtrack_feedback_reference


def joints(dtype=torch.float64):
    return torch.tensor([[0.,.3,-.6,0.,.3,-.6,0.,-.3,.6,0.,-.3,.6]],dtype=dtype)


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('active',range(4))
def test_small_lift_solved_only_for_tight_leg(dtype,active):
    q=joints(dtype); target=body_feet(q); target[:,:,2]+=.0004
    tol=q.new_full((1,4),.002); tol[0,active]=.0001
    r=solve_constrained_ik(q,target,q,tolerance_m=tol)
    assert r.valid.item()
    assert r.iterations[0,active]>0
    assert r.residual_m[0,active]<=.0001
    other=[j for j in range(4) if j!=active]
    assert (r.iterations[0,other]==0).all()
    assert (r.q-q).abs().max()>0
    legacy=solve_constrained_ik(q,target,q)
    assert (legacy.iterations==0).all()


@pytest.mark.parametrize('bad',['shape','dtype','zero','negative','nan','loose'])
def test_bad_tolerance_rejected(bad):
    q=joints(); t=q.new_full((1,4),.002)
    if bad=='shape':t=t[:,:3]
    elif bad=='dtype':t=t.float()
    elif bad=='zero':t[0,0]=0
    elif bad=='negative':t[0,0]=-.1
    elif bad=='nan':t[0,0]=float('nan')
    else:t[0,0]=.003
    with pytest.raises(ValueError):solve_constrained_ik(q,body_feet(q),q,tolerance_m=t)


@pytest.mark.parametrize('mode',[0,1,2])
@pytest.mark.parametrize('active',range(4))
def test_transaction_uses_tight_precision_only_in_lift_mode(mode,active):
    q=joints(); root=q.new_tensor([[0.,0.,.62]]); quat=q.new_tensor([[1.,0.,0.,0.]])
    old=PoseReference(BodyPose(root,quat),body_feet(q)+root[:,None])
    wheels=old.wheels_w.clone(); wheels[:,active,2]+=.0004
    req=PoseReference(old.body,wheels)
    r=backtrack_feedback_reference(old,req,q.new_zeros(1,3),q.new_zeros(1,3),q.new_zeros(1),q,q,q,.02,IKConfig(),
        measured=old.body,active_wheel=torch.tensor([active]),execution_mode=torch.tensor([mode]),execution_valid=lambda ik,u:ik.valid)
    assert r.valid.item()
    assert ((r.command_ik.q-q).abs()<=.05).all()
    if mode==1:
        assert r.command_ik.residual_m[0,active]<=.0001
        assert r.command_ik.iterations[0,active]>0
    else:assert (r.command_ik.q==q).all()


def test_tight_tolerance_does_not_bypass_branch_or_workspace():
    q=joints(); tol=q.new_full((1,4),.0001)
    t=body_feet(q); t[:,0,2]=2
    assert not solve_constrained_ik(q,t,q,tolerance_m=tol).valid.item()
    branch=q.clone(); branch[:,2]*=-1
    assert not solve_constrained_ik(q,body_feet(q),branch,tolerance_m=tol).valid.item()


def lift_floor(accepted=.081,measured=.098,maximum=.30,force=45.,floor=True):
    from ame_baseline.m1_teacher_dynamic_support import measured_lift_step
    t=lambda x:torch.tensor([x],dtype=torch.float64)
    return measured_lift_step(t(accepted),t(measured),t(maximum),t(force),t(.015),t(force),t(.015),torch.tensor([False]),t(.02),
        rate_m_s=.02,lead_m=.02,force_floor_n=30.,force_band_n=15.,margin_floor_m=.01,margin_band_m=.005,measured_floor=floor)


def test_request_reconciles_measured_floor_without_faking_physical_progress():
    r=lift_floor()
    assert r.next_z.item()==pytest.approx(.0984)
    assert r.increment.item()==pytest.approx(.0004)
    assert lift_floor(floor=False).next_z.item()==pytest.approx(.0814)
    assert lift_floor(force=30).next_z.item()==pytest.approx(.081)
    assert lift_floor(accepted=.125).next_z.item()==pytest.approx(.125)


@pytest.mark.parametrize('accepted,measured',[(.3,.3),(.29,.31),(.31,.29)])
def test_measured_floor_never_relabels_ceiling_as_lift(accepted,measured):
    r=lift_floor(accepted=accepted,measured=measured)
    assert r.next_z.item()==pytest.approx(accepted)
    assert r.increment.item()==0
    assert r.freeze_code.item()==3


def test_combined_reserve_uses_weakest_candidate_and_invalid_rows_freeze():
    from ame_baseline.m1_teacher_dynamic_support import combined_tripod_reserve
    loads=torch.tensor([[47.43,45.76,36.75],[50.,30.,50.],[50.,float('nan'),50.],[50.,50.,50.]],dtype=torch.float64)
    valid=torch.ones((4,3),dtype=torch.bool);valid[3,2]=False
    assert combined_tripod_reserve(loads,valid).tolist()==pytest.approx([.45,0.,0.,0.])


def test_execution_evidence_reports_and_independently_rejects_forgery():
    from test_m1_teacher_measured_ik_evidence import bound_sample
    import copy
    p,t,s=bound_sample(); d=s['teacher_diagnostic']
    assert d['execution_tolerance_m_0']==pytest.approx(.0001)
    assert d['execution_tolerance_m_1']==pytest.approx(.002)
    for name in ('start','goal','solved'):
        assert isinstance(d['execution_active_world_'+name+'_z'],float)
    p.verify_execution_geometry(s,t.cfg)
    for key in ('execution_tolerance_m_0','execution_active_world_start_z','execution_active_world_goal_z','execution_active_world_solved_z'):
        bad=copy.deepcopy(s);bad['teacher_diagnostic'][key]+=.01
        with pytest.raises(ValueError):p.verify_execution_geometry(bad,t.cfg)


def test_combined_reserve_is_bound_by_independent_tripod_audit():
    from test_m1_teacher_dynamic_support_evidence import sample
    import copy
    p,t,s=sample(); d=s['teacher_diagnostic']
    expected=min(d['tripod_reserve'],max(0.,min(1.,(d['tripod_selected_anchor_min_n']-30)/15)),max(0.,min(1.,(d['tripod_selected_measured_min_n']-30)/15)))
    assert d['tripod_combined_reserve']==pytest.approx(expected,abs=1e-6)
    assert p.verify_tripod_sample(s,t.cfg)==[]
    bad=copy.deepcopy(s);bad['teacher_diagnostic']['tripod_combined_reserve']+=.2
    assert p.verify_tripod_sample(bad,t.cfg)
    assert isinstance(d['dynamic_actual_lift_m'],float)
    bad=copy.deepcopy(s);bad['teacher_diagnostic']['dynamic_actual_lift_m']+=.1
    assert p.verify_tripod_sample(bad,t.cfg)


@pytest.mark.parametrize('index',range(4))
def test_native_frozen_inputs_keep_bounded_execution_and_actual_progress(index):
    import json
    from pathlib import Path
    from ame_baseline.m1_reference_teacher import ReferenceTeacher,TeacherConfig,TeacherState,TEACHER_DIAGNOSTIC_FIELDS
    from ame_baseline.m1_teacher_feedback import BodyFeedbackConfig
    from test_m1_teacher_probe_contract import probe
    raw=json.loads((Path(__file__).parent/'fixtures/reconciliation_v17_native.json').read_text())
    config=raw['teacher_config'];config['feedback']=BodyFeedbackConfig(**config['feedback'])
    teacher=ReferenceTeacher(TeacherConfig(**config));p=probe();c=raw['contexts'][index]
    s=TeacherState(**p._dynamic_unpack(c['input'],'cpu'));teacher._rows=[p._dynamic_unpack(c['pre'],'cpu')]
    p.observe_dynamic_support(teacher)
    out=teacher.step(s); d=p.diagnostic_json(out.diagnostic[0].tolist())
    assert out.valid.item(),d
    assert ((teacher._rows[0]['last_q']-s.last_applied_leg_target).abs()<=2.5*s.dt[0]).all()
    assert d['dynamic_requested_z']>=d['dynamic_measured_z']
    assert d['dynamic_reserve']<=d['tripod_combined_reserve']+1e-6
    assert d['dynamic_actual_lift_m']<.003
    if index==0:
        # This saved BALANCE input has not reached the newly selected lower
        # support pose. It must not be promoted to LIFT merely by old timing.
        assert s.root_pos_w[0,2]-teacher._rows[0]['goal'].body.pos_w[0,2]>.03
        assert d['preparation_ready']==0
        assert teacher._rows[0]['phase']==1
    else:
        assert teacher._rows[0]['phase']==2
    sample=dict(dynamic_support=p.dynamic_context_for(teacher,s,0),teacher_diagnostic=d)
    assert p.verify_tripod_sample(sample,teacher.cfg)==[]


def test_mixed_batch_tightens_only_its_own_active_leg():
    q=joints().repeat(3,1);root=q.new_tensor([[0.,0.,.62]]).repeat(3,1);quat=q.new_tensor([[1.,0.,0.,0.]]).repeat(3,1)
    old=PoseReference(BodyPose(root,quat),body_feet(q)+root[:,None])
    target=old.wheels_w.clone();target[:,:,2]+=.0004
    r=backtrack_feedback_reference(old,PoseReference(old.body,target),q.new_zeros(3,3),q.new_zeros(3,3),q.new_zeros(3),q,q,q,.02,IKConfig(),
        measured=old.body,active_wheel=torch.tensor([0,2,3]),execution_mode=torch.tensor([1,1,2]),execution_valid=lambda ik,u:ik.valid)
    assert r.valid.all()
    assert r.command_ik.iterations[0,0]>0 and r.command_ik.iterations[1,2]>0
    assert (r.command_ik.iterations[2]==0).all()
    assert (r.command_ik.iterations[0,1:]==0).all()
    assert (r.command_ik.iterations[1,[0,1,3]]==0).all()
