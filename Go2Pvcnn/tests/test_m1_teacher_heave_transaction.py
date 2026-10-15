import pytest
import torch
from dataclasses import replace
from test_m1_teacher_load_feedback_transaction import fixture,load_teacher
from test_m1_reference_teacher import advance,api

def test_paired_heave_backtracks_once():
    from ame_baseline.m1_teacher_pose import backtrack_feedback_reference,_rotation
    from ame_baseline.m1_teacher_ik import IKConfig
    q,ref=fixture();calls=[]
    def accept_second(ik,u):
        calls.append(1);return ik.valid & (len(calls)>1)
    out=backtrack_feedback_reference(ref,ref,q.new_zeros(1,3),q.new_zeros(1,3),q.new_zeros(1),
        q,q,q,.02,IKConfig(),execution_valid=accept_second,measured=ref.body,
        active_wheel=torch.tensor([0]),execution_mode=torch.tensor([1]),
        previous_support_reference_w_z=ref.wheels_w[:,:,2],proposed_support_reference_w_z=ref.wheels_w[:,:,2],
        previous_support_heave=q.new_zeros(1),proposed_support_heave=q.new_tensor([-.0004]))
    assert out.valid.item() and out.backtrack_index.item()==1
    world=ref.body.pos_w[:,None]+torch.einsum('bij,bkj->bki',_rotation(ref.body.quat_w),out.execution_target.body_step)
    assert torch.allclose(world[:,1:,2]-ref.wheels_w[:,1:,2],
        q.new_full((1,3),-.0004)*out.execution_target.fraction[:,None],atol=1e-10,rtol=0)

def test_teacher_capture_and_next_height_correction():
    teacher,s=load_teacher();out=teacher.step(s);assert out.valid.item()
    row=teacher._rows[0];baseline=row['support_heave_error0'].clone()
    assert row['support_heave'].abs().max()<1e-8
    s=advance(s);s.root_pos_w[:,2]-=.001
    assert teacher.step(s).valid.item()
    assert torch.equal(row['support_heave_error0'],baseline)
    assert -.00040001<=row['support_heave'].item()<0
    teacher.step(advance(s,episode_id=s.episode_id+1,reset_mask=torch.ones_like(s.reset_mask)))
    assert 'support_heave' not in teacher._rows[0] and 'support_heave_error0' not in teacher._rows[0]
    assert 'support_capture_root_z' not in teacher._rows[0]

def test_teacher_rejected_heave_not_committed(monkeypatch):
    import ame_baseline.m1_teacher_pose as p
    teacher,s=load_teacher();real=p.solve_constrained_ik
    monkeypatch.setattr(p,'solve_constrained_ik',lambda *a,**kw:replace(real(*a,**kw),valid=torch.zeros(a[0].shape[0],dtype=torch.bool)))
    assert not teacher.step(s).valid.item()
    assert 'support_heave_error0' not in teacher._rows[0]

def test_teacher_restore_decays_heave():
    teacher,s=load_teacher('RESTORE');row=teacher._rows[0]
    row.update(support_heave=s.root_pos_w.new_tensor([.001]),support_heave_error0=s.root_pos_w.new_zeros(1))
    assert teacher.step(s).valid.item()
    assert .00059999<=row['support_heave'].item()<.001

@pytest.mark.parametrize('bad',['unpaired','shape','nan','cap','rate','context'])
def test_paired_heave_rejects_invalid_contract(bad):
    from ame_baseline.m1_teacher_pose import backtrack_feedback_reference
    from ame_baseline.m1_teacher_ik import IKConfig
    q,ref=fixture();old=q.new_zeros(1);new=q.new_tensor([-.0004])
    height=ref.wheels_w[:,:,2]
    if bad=='unpaired':new=None
    if bad=='shape':new=new.reshape(1,1)
    if bad=='nan':new[:]=float('nan')
    if bad=='cap':old[:]=.021;new[:]=.021
    if bad=='rate':new[:]=-.0005
    if bad=='context':height=None
    with pytest.raises(ValueError):
        backtrack_feedback_reference(ref,ref,q.new_zeros(1,3),q.new_zeros(1,3),q.new_zeros(1),
            q,q,q,.02,IKConfig(),execution_valid=lambda ik,u:ik.valid,measured=ref.body,
            active_wheel=torch.tensor([0]),execution_mode=torch.tensor([1]),
            previous_support_reference_w_z=height,proposed_support_reference_w_z=height,
            previous_support_heave=old,proposed_support_heave=new)

def test_rejected_transaction_keeps_nonzero_heave_and_capture(monkeypatch):
    import ame_baseline.m1_teacher_pose as p
    teacher,s=load_teacher();assert teacher.step(s).valid.item()
    s=advance(s);s.root_pos_w[:,2]-=.001
    assert teacher.step(s).valid.item()
    row=teacher._rows[0];old=row['support_heave'].clone();error0=row['support_heave_error0'].clone()
    assert old.item()<0
    real=p.solve_constrained_ik
    monkeypatch.setattr(p,'solve_constrained_ik',lambda *a,**kw:replace(real(*a,**kw),valid=torch.zeros(a[0].shape[0],dtype=torch.bool)))
    assert not teacher.step(advance(s)).valid.item()
    assert torch.equal(row['support_heave'],old) and torch.equal(row['support_heave_error0'],error0)

@pytest.mark.parametrize('heave',[0.,.001,-.001])
def test_restore_handover_requires_zero_heave(heave):
    from test_m1_reference_teacher import restoring_teacher
    teacher,s=restoring_teacher()
    teacher.cfg=replace(teacher.cfg,slow_rolling=True,load_feedback=True)
    row=teacher._rows[0];row.update(stable=4,support_heave=s.root_pos_w.new_tensor([heave]),
        support_heave_error0=s.root_pos_w.new_zeros(1))
    s.recovered[:,0,0]=True
    out=teacher.step(s)
    assert out.valid.item()
    if heave:
        assert row['stable']>=5
        assert row['phase']==api().Phase.RESTORE and row['support_heave'].abs().item()>0
    else:
        assert row['phase']==api().Phase.APPROACH
        assert 'support_heave' not in row and 'support_heave_error0' not in row

def test_reset_only_clears_ended_row_heave():
    import copy
    from dataclasses import fields
    teacher,s=load_teacher();assert teacher.step(s).valid.item()
    s=advance(s);s.root_pos_w[:,2]-=.001;assert teacher.step(s).valid.item()
    teacher._rows.append(copy.deepcopy(teacher._rows[0]))
    values={f.name:getattr(s,f.name).repeat((2,)+(1,)*(getattr(s,f.name).ndim-1))
        for f in fields(s) if isinstance(getattr(s,f.name),torch.Tensor)}
    s=advance(replace(s,**values));s.reset_mask[0]=True;s.episode_id[0]+=1
    out=teacher.step(s)
    assert out.valid[1]
    assert 'support_heave' not in teacher._rows[0] and 'support_heave_error0' not in teacher._rows[0]
    assert 'support_capture_root_z' not in teacher._rows[0]
    assert torch.equal(teacher._rows[1]['support_capture_root_z'],s.root_pos_w[1:2,2]+.001)
    assert teacher._rows[1]['support_heave'].item()<0

@pytest.mark.parametrize('retained',[False,True])
def test_final_encode_failure_does_not_commit_heave(monkeypatch,retained):
    t=api();teacher,s=load_teacher()
    if retained:
        assert teacher.step(s).valid.item()
        s=advance(s);s.root_pos_w[:,2]-=.001
        assert teacher.step(s).valid.item()
        s=advance(s);s.root_pos_w[:,2]-=.001
    row=teacher._rows[0]
    before={key:row[key].clone() for key in ('support_heave','support_heave_error0','support_capture_root_z','support_execution_z') if key in row}
    real_transaction=teacher._feedback_transaction;real_encode=t.encode_targets
    armed=[False];rejected=[]
    def transaction(*args,**kwargs):
        result=real_transaction(*args,**kwargs)
        assert result[0].valid.item(), 'must reach successful IK transaction before final encoding'
        armed[0]=True
        return result
    def encode(*args,**kwargs):
        action,valid=real_encode(*args,**kwargs)
        if armed[0]:
            assert valid.item()
            armed[0]=False;rejected.append(True)
            return action,torch.zeros_like(valid)
        return action,valid
    monkeypatch.setattr(teacher,'_feedback_transaction',transaction)
    monkeypatch.setattr(t,'encode_targets',encode)
    out=teacher.step(s)
    assert rejected==[True] and not out.valid.item() and out.reason.item()==int(t.Reason.ACTION_INVALID)
    for key in ('support_heave','support_heave_error0','support_capture_root_z','support_execution_z'):
        if retained:assert torch.equal(row[key],before[key])
        else:assert key not in row
