"""Coherent mode must execute selected support posture, not legacy height overrides."""
from dataclasses import replace
import pytest
import torch
from ame_baseline import m1_reference_teacher as m
from test_m1_teacher_bounded_attitude_transaction import frozen_teacher

@pytest.mark.parametrize('flag',[1,None,'yes'])
def test_reject_nonbool_coherent_mode(flag):
    with pytest.raises(ValueError,match='coherent'):
        m.TeacherConfig(coherent_support_pose=flag)

def test_reject_coherent_without_bounded_pose():
    with pytest.raises(ValueError,match='coherent'):
        m.TeacherConfig(coherent_support_pose=True)

def coherent_teacher():
    t,s=frozen_teacher()
    t.cfg=replace(t.cfg,coherent_support_pose=True)
    return t,s

def test_real_transaction_has_one_posture_geometry():
    t,s=coherent_teacher()
    history=('support_execution_z','support_capture_root_z','support_heave','support_attitude_error0')
    before={k:t._rows[0][k].clone() for k in history if k in t._rows[0]}
    out=t.step(s)
    assert out.valid.item()
    d=dict(zip(m.TEACHER_DIAGNOSTIC_FIELDS,out.diagnostic[0].tolist()))
    assert d['load_enabled']==1
    assert d['height_enabled']==0 and d['heave_enabled']==0 and d['attitude_enabled']==0
    assert (t._rows[0]['last_q']-s.last_applied_leg_target).abs().max()<=.0500001
    assert max(d['ik_residual_m_'+str(j)] for j in range(4))<=.0001
    for k in history:
        if k in before:
            assert torch.equal(t._rows[0][k],before[k])
        else:
            assert k not in t._rows[0]

def test_coherent_duplicate_preserves_action():
    t,s=coherent_teacher()
    first=t.step(s);second=t.step(s)
    assert first.valid.item() and torch.equal(first.action,second.action)

def rotation(q):
    w,x,y,z=(float(v) for v in q)
    return [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
            [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
            [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]

def test_encoded_transaction_uses_full_xyz_geometry(monkeypatch):
    t,s=coherent_teacher();real=t._feedback_transaction;seen=[]
    def record(*a,**kw):
        result=real(*a,**kw);seen.append((result[0],a[-1]));return result
    monkeypatch.setattr(t,'_feedback_transaction',record)
    assert t.step(s).valid.item()
    solved,evidence=seen[-1]
    rd=rotation(solved.command.body.quat_w[0]);rm=rotation(s.root_quat_w[0])
    expected=[]
    for leg in range(4):
        active=leg==0
        matrix=rm if active else rd
        pos=s.root_pos_w[0] if active else solved.command.body.pos_w[0]
        p=(solved.command.wheels_w[0,leg]-pos).tolist()
        off=0 if active else evidence['load_attempted_'+str(leg)]
        expected.append([sum(matrix[j][i]*p[j] for j in range(3))+rm[2][i]*off for i in range(3)])
    want=solved.execution_target.body_goal.new_tensor([expected])
    torch.testing.assert_close(solved.execution_target.body_goal,want,atol=2e-6,rtol=0)

def test_coherent_reset_discards_episode_state():
    from test_m1_reference_teacher import advance
    t,s=coherent_teacher();assert t.step(s).valid.item()
    t.step(advance(s,episode_id=s.episode_id+1,reset_mask=torch.ones_like(s.reset_mask)))
    assert not t._rows[0]['prepared']
    assert 'support_load_offset' not in t._rows[0]

def test_coherent_restore_returns_original_pose():
    from test_m1_teacher_load_feedback_transaction import load_teacher
    from ame_baseline.m1_teacher_pose import BodyPose,PoseReference
    from test_m1_teacher_pose import quat
    t,s=load_teacher('RESTORE')
    t.cfg=replace(t.cfg,bounded_crossing_attitude=True,coherent_support_pose=True)
    original=t._rows[0]['anchor_pose'].quat_w.clone()
    old=t._rows[0]['goal']
    t._rows[0]['goal']=PoseReference(BodyPose(old.body.pos_w,quat(r=.1).to(old.body.quat_w)),old.wheels_w)
    assert t.step(s).valid.item()
    assert torch.allclose(t._rows[0]['goal'].body.quat_w,original,atol=1e-9,rtol=0)
    assert 'support_execution_z' not in t._rows[0]

@pytest.mark.parametrize('receipt,offset,legacy_heave',[(True,0.,0.),(True,0.,.01),(False,0.,0.),(True,.001,0.)])
def test_coherent_restore_completion_and_cleanup(receipt,offset,legacy_heave):
    from test_m1_reference_teacher import restoring_teacher
    t,s=restoring_teacher()
    t.cfg=replace(t.cfg,slow_rolling=True,load_feedback=True,
                  bounded_crossing_attitude=True,coherent_support_pose=True)
    row=t._rows[0]
    row.update(stable=4,support_load_offset=s.root_pos_w.new_tensor([[0.,offset,-offset,0.]]),
               support_heave=s.root_pos_w.new_tensor([legacy_heave]))
    s.recovered[:,0,0]=receipt
    out=t.step(s)
    assert out.valid.item()
    if receipt and not offset:
        assert row['phase']==m.Phase.APPROACH and not row['prepared']
        assert row['target']==-1 and row['wheel']==-1
        for key in ('support_load_offset','support_heave','support_execution_z','tripod_selected_reference'):
            assert key not in row
    else:
        assert row['phase']==m.Phase.RESTORE and row['prepared']

@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('active',range(4))
def test_independent_scalar_full_xyz_load_all_legs(dtype,active):
    from ame_baseline.m1_teacher_pose import BodyPose,PoseReference,backtrack_feedback_reference
    from ame_baseline.m1_teacher_ik import IKConfig,body_feet
    from test_m1_teacher_pose import quat
    q=torch.tensor([[0.,.3,-.6,0.,.3,-.6,0.,-.3,.6,0.,-.3,.6]],dtype=dtype)
    pos=q.new_tensor([[0.,0.,.62]]);measured=BodyPose(pos,quat(r=.02,p=-.01).to(q))
    rm=q.new_tensor(rotation(measured.quat_w[0]))
    wheels=pos[:,None]+torch.einsum('ij,bkj->bki',rm,body_feet(q))
    accepted=PoseReference(measured,wheels)
    desired=PoseReference(BodyPose(pos+q.new_tensor([[.0001,0.,0.]]),quat(r=.021,p=-.011).to(q)),wheels)
    off=q.new_zeros(1,4);support=[i for i in range(4) if i!=active]
    off[0,support[0]]=.0001;off[0,support[-1]]=-.0001
    solved=backtrack_feedback_reference(accepted,desired,q.new_zeros(1,3),q.new_zeros(1,3),
        q.new_zeros(1),q,q,q,.02,IKConfig(),execution_valid=lambda ik,u:ik.valid,
        measured=measured,active_wheel=torch.tensor([active]),execution_mode=torch.tensor([1]),
        previous_support_offset=torch.zeros_like(off),proposed_support_offset=off)
    assert solved.valid.item()
    rd=rotation(solved.command.body.quat_w[0]);expected=[]
    for leg in range(4):
        matrix=rm.tolist() if leg==active else rd
        origin=pos[0] if leg==active else solved.command.body.pos_w[0]
        delta=(solved.command.wheels_w[0,leg]-origin).tolist()
        expected.append([sum(matrix[j][i]*delta[j] for j in range(3))+float(rm[2,i]*off[0,leg]) for i in range(3)])
    torch.testing.assert_close(solved.execution_target.body_goal,q.new_tensor([expected]),atol=2e-6,rtol=0)

def test_coherent_encode_rejection_keeps_committed_state(monkeypatch):
    t,s=coherent_teacher()
    before=t._rows[0]['accepted'].body.quat_w.clone()
    load=t._rows[0].get('support_load_offset')
    load=None if load is None else load.clone()
    transaction=t._feedback_transaction;encode=m.encode_targets;armed=[False]
    def record(*a,**kw):
        result=transaction(*a,**kw)
        assert result[0].valid.item()
        armed[0]=True
        return result
    def reject(*a,**kw):
        action,valid=encode(*a,**kw)
        if armed[0]:
            armed[0]=False
            return action,torch.zeros_like(valid)
        return action,valid
    monkeypatch.setattr(t,'_feedback_transaction',record)
    monkeypatch.setattr(m,'encode_targets',reject)
    out=t.step(s)
    assert not out.valid.item()
    assert torch.equal(t._rows[0]['accepted'].body.quat_w,before)
    if load is None:
        assert 'support_load_offset' not in t._rows[0]
    else:
        assert torch.equal(t._rows[0]['support_load_offset'],load)

def test_actual_v35_frame130_coherent_transaction():
    import json
    from pathlib import Path
    from test_m1_teacher_probe_contract import probe
    p=probe()
    c=json.loads((Path(__file__).parent/'fixtures/m1_v35_coherent130.json').read_text())['dynamic_support']
    t=m.ReferenceTeacher(m.TeacherConfig(slow_rolling=True,load_feedback=True,bounded_crossing_attitude=True,coherent_support_pose=True))
    t._rows=[p._dynamic_unpack(c['pre'],'cpu')]
    state=m.TeacherState(**p._dynamic_unpack(c['input'],'cpu'))
    out=t.step(state)
    assert out.valid.item()
    assert (t._rows[0]['last_q']-state.last_applied_leg_target).abs().max()<=.0500001
    d=dict(zip(m.TEACHER_DIAGNOSTIC_FIELDS,out.diagnostic[0].tolist()))
    assert max(d['ik_residual_m_'+str(j)] for j in range(4))<=.0001
    assert d['height_enabled']==0 and d['attitude_enabled']==0

def test_coherent_peer_reset_does_not_change_live_row():
    import copy
    from dataclasses import fields
    single,state=coherent_teacher();expected=single.step(state)
    t,s=coherent_teacher();t._rows=[copy.deepcopy(t._rows[0]),copy.deepcopy(t._rows[0])]
    batch=m.TeacherState(**{f.name:getattr(s,f.name).repeat((2,)+(1,)*(getattr(s,f.name).ndim-1)) for f in fields(s)})
    batch.episode_id[1]+=1;batch.reset_mask[1]=True
    out=t.step(batch)
    assert out.valid[0] and torch.equal(out.action[0],expected.action[0])
    assert not t._rows[1]['prepared']




