"""Real IK candidates: refine only individually verified execution points."""
from dataclasses import replace
import pytest
import torch
from test_m1_teacher_load_feedback_transaction import fixture
from ame_baseline.m1_teacher_ik import IKConfig
from ame_baseline.m1_teacher_pose import backtrack_feedback_reference


@pytest.mark.parametrize('dtype', [torch.float32, torch.float64])
def test_safe_fraction_is_refined_without_bypassing_validator(dtype):
    q, ref = fixture()
    q=q.to(dtype)
    ref=replace(ref,body=replace(ref.body,pos_w=ref.body.pos_w.to(dtype),quat_w=ref.body.quat_w.to(dtype)),wheels_w=ref.wheels_w.to(dtype))
    requested=replace(ref,wheels_w=ref.wheels_w.clone())
    requested.wheels_w[0,0,2]+=.001
    calls=[]
    def valid(ik,u):
        calls.append(u.clone())
        return ik.valid & (u[:,0]<=.00095)
    out=backtrack_feedback_reference(ref,requested,q.new_zeros(1,3),q.new_tensor([[.001,0.,0.]]),
        q.new_zeros(1),q,q,q,.02,IKConfig(),execution_valid=valid,
        measured=ref.body,active_wheel=torch.tensor([0]),execution_mode=torch.tensor([1]))
    assert out.valid.item() and out.backtrack_index.item()==1
    assert out.execution_target.fraction.item()==pytest.approx(.9375)
    assert out.output[0,0].item()==pytest.approx(.0009375)
    expected=ref.wheels_w+.9375*(requested.wheels_w-ref.wheels_w)
    expected[:,0]=requested.wheels_w[:,0]
    assert torch.allclose(out.physical.wheels_w,expected)
    assert out.execution_target.intent_fraction.item()==1.
    assert (out.command_ik.q-q).abs().max()<=.05
    # Six support-search validations, active execution, then active intent.
    assert len(calls)==8
    assert torch.equal(calls[-1],out.output)
    assert out.execution_target.active_fraction.item()==1.


def test_refined_teacher_commits_the_actual_fraction():
    import copy
    import json
    from dataclasses import asdict
    from test_m1_teacher_load_feedback_evidence import sample
    p, teacher, row=sample()
    found=False
    for shift in (.02,.04,.06,.08):
        c=copy.deepcopy(row['feedback_context'])
        c['last_applied_q'][2]-=shift
        diagnostic,_,_=p.replay_feedback_transaction(json.dumps(c),json.dumps(asdict(teacher.cfg)),
            row['action_target_dtype'],row['phase'])
        d=json.loads(diagnostic)
        if d['reference_valid']!=1:continue
        beta=d['execution_fraction']
        if abs(beta-2.**(-d['backtrack_index']))<1e-6:continue
        found=True
        for j in range(4):
            old=c['load_feedback']['previous'][j]; proposed=c['load_feedback']['proposed'][j]
            assert d[f'load_selected_{j}']==pytest.approx(old+beta*(proposed-old),abs=1e-8)
        assert d['heave_selected']==pytest.approx(d['heave_previous']+beta*(d['heave_proposed']-d['heave_previous']),abs=1e-8)
        for j in range(4):
            assert d[f'height_selected_{j}']==pytest.approx(d[f'height_previous_{j}']+beta*(d[f'height_proposed_{j}']-d[f'height_previous_{j}']),abs=1e-7)
    assert found, 'fixture must exercise a real refined teacher transaction'


def test_load_auditor_uses_fraction_not_coarse_index():
    from test_m1_teacher_load_feedback_evidence import sample
    p,t,s=sample();d=s['teacher_diagnostic']
    d['backtrack_index']=1;d['execution_fraction']=.9375
    for j in range(4):
        old=d[f'load_previous_{j}'];proposed=d[f'load_proposed_{j}']
        d[f'load_selected_{j}']=d[f'load_committed_{j}']=old+.9375*(proposed-old)
    p.verify_load_feedback(s,t.cfg)
    d['execution_fraction']=.5
    with pytest.raises(ValueError):p.verify_load_feedback(s,t.cfg)


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_mixed_batch_freezes_full_rejected_and_mode_zero_rows(dtype):
    q,ref=fixture();q=q.to(dtype).repeat(4,1)
    ref=replace(ref,body=replace(ref.body,pos_w=ref.body.pos_w.to(dtype).repeat(4,1),
        quat_w=ref.body.quat_w.to(dtype).repeat(4,1)),wheels_w=ref.wheels_w.to(dtype).repeat(4,1,1))
    limits=q.new_tensor([2.,.00095,-1.,.0004]);calls=[]
    def valid(ik,u):
        calls.append(u.clone());return ik.valid & (u[:,0]<=limits)
    out=backtrack_feedback_reference(ref,ref,q.new_zeros(4,3),q.new_tensor([[.001,0.,0.]]).repeat(4,1),
        q.new_zeros(4),q,q,q,.02,IKConfig(),execution_valid=valid,measured=ref.body,
        active_wheel=torch.zeros(4,dtype=torch.long),execution_mode=torch.tensor([1,1,1,0]))
    assert out.valid.tolist()==[True,True,False,True]
    assert out.backtrack_index.tolist()==[0,1,-1,2]
    assert out.execution_target.fraction.tolist()==pytest.approx([1.,.9375,1/128,.25])
    assert torch.allclose(out.output[:,0],out.execution_target.fraction*.001)
    # Preserve the support search budget; active validation uses committed output.
    assert len(calls[:-1])==12
    assert torch.equal(calls[-1],out.output)
    assert out.execution_target.active_fraction.tolist()==pytest.approx([1.,1.,1/128,.25])
    assert ((out.command_ik.q-q).abs().amax(-1)[out.valid]<=.05).all()


def test_nonmonotonic_callback_keeps_last_individually_valid_point():
    q,ref=fixture();calls=[]
    def valid(ik,u):
        calls.append(float(u[0,0]));return ik.valid & ((u[:,0]>=.00049)&(u[:,0]<=.00076))
    out=backtrack_feedback_reference(ref,ref,q.new_zeros(1,3),q.new_tensor([[.001,0.,0.]]),
        q.new_zeros(1),q,q,q,.02,IKConfig(),execution_valid=valid,measured=ref.body,
        active_wheel=torch.tensor([0]),execution_mode=torch.tensor([1]))
    assert out.valid.item() and out.execution_target.fraction.item()==.75
    assert out.output[0,0].item()==pytest.approx(.00075)
    assert len(calls[:-1])==6
    assert calls[:-1]==pytest.approx([.001,.0005,.00075,.000875,.0008125,.00078125])
    assert calls[-1]==pytest.approx(.00075)
    assert out.execution_target.active_fraction.item()==1.


@pytest.mark.parametrize('accept',[True,False])
def test_no_extra_candidates_for_full_step_or_entirely_rejected(accept):
    q,ref=fixture();calls=[]
    def valid(ik,u):
        calls.append(1);return ik.valid & accept
    out=backtrack_feedback_reference(ref,ref,q.new_zeros(1,3),q.new_zeros(1,3),
        q.new_zeros(1),q,q,q,.02,IKConfig(),execution_valid=valid,measured=ref.body,
        active_wheel=torch.tensor([0]),execution_mode=torch.tensor([1]))
    assert bool(out.valid)==accept and len(calls)==(1 if accept else 8)
