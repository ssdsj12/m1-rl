import pytest
import torch
from ame_baseline.m1_teacher_ik import body_feet,IKConfig
from ame_baseline.m1_teacher_pose import BodyPose,PoseReference,_rotation,backtrack_feedback_reference
from ame_baseline.m1_teacher_execution_targets import execution_targets
from dataclasses import replace

def load_teacher(phase='LIFT'):
    from test_m1_teacher_lift_decoupling import crossing
    teacher,s=crossing(phase)
    teacher.cfg=replace(teacher.cfg,load_feedback=True)
    s.wheel_force_w[0,:,2]=s.root_pos_w.new_tensor([12.,179.,159.,35.])
    return teacher,s

def test_teacher_commits_bounded_load_offset():
    teacher,s=load_teacher()
    out=teacher.step(s)
    assert out.valid.item()
    offset=teacher._rows[0]['support_load_offset']
    assert offset[0,0]==0 and offset[0,3]<0
    assert offset.sum().abs()<1e-8 and offset.abs().max()<=.00020001

def test_rejected_teacher_does_not_commit_load_offset(monkeypatch):
    import ame_baseline.m1_teacher_pose as p
    teacher,s=load_teacher();real=p.solve_constrained_ik
    monkeypatch.setattr(p,'solve_constrained_ik',
        lambda *a,**kw:replace(real(*a,**kw),valid=torch.zeros(a[0].shape[0],dtype=torch.bool)))
    out=teacher.step(s)
    assert not out.valid.item()
    assert 'support_load_offset' not in teacher._rows[0]

def test_reset_discards_own_load_offset():
    from test_m1_reference_teacher import advance
    teacher,s=load_teacher();assert teacher.step(s).valid.item()
    teacher.step(advance(s,episode_id=s.episode_id+1,reset_mask=torch.ones_like(s.reset_mask)))
    assert 'support_load_offset' not in teacher._rows[0]

def test_restore_reduces_offset_without_jump():
    teacher,s=load_teacher('RESTORE')
    old=s.root_pos_w.new_tensor([[0.,.004,-.001,-.003]])
    teacher._rows[0]['support_load_offset']=old.clone()
    out=teacher.step(s)
    assert out.valid.item()
    new=teacher._rows[0]['support_load_offset']
    assert new.abs().max()<old.abs().max()
    assert (new-old).abs().max()<=.00020001
    assert new.sum().abs()<1e-8
    assert teacher._rows[0]['prepared']

def fixture():
    q=torch.tensor([[0.,.3,-.6,0.,.3,-.6,0.,-.3,.6,0.,-.3,.6]],dtype=torch.float64)
    root=q.new_tensor([[0.,0.,.62]]);quat=q.new_tensor([[.9950041652780258,.09983341664682815,0.,0.]])
    body=BodyPose(root,quat)
    wheels=root[:,None]+torch.einsum('bij,bkj->bki',_rotation(quat),body_feet(q))
    return q,PoseReference(body,wheels)

@pytest.mark.parametrize('active',range(4))
def test_world_vertical_support_offset_uses_measured_rotation(active):
    q,ref=fixture();idx=torch.tensor([active]);mode=torch.tensor([1]);beta=q.new_tensor([.25])
    support=[j for j in range(4) if j!=active]
    off=q.new_zeros(1,4);off[0,support[0]]=.0002;off[0,support[-1]]=-.0002
    baseline=execution_targets(ref,ref.body,idx,q,beta,mode)
    target=execution_targets(ref,ref.body,idx,q,beta,mode,support_offset_w_z=off)
    world=torch.einsum('bij,bkj->bki',_rotation(ref.body.quat_w),target.body_goal-baseline.body_goal)
    assert world[:,:,:2].abs().max()<1e-12
    assert torch.allclose(world[:,:,2],off,atol=1e-12)
    assert torch.allclose(target.body_step-baseline.body_step,.25*(target.body_goal-baseline.body_goal))

def test_transaction_solves_submillimetre_support_correction():
    q,ref=fixture();zero=q.new_zeros(1,4);off=zero.clone();off[0,1]=.0002;off[0,3]=-.0002
    result=backtrack_feedback_reference(ref,ref,q.new_zeros(1,3),q.new_zeros(1,3),
        q.new_zeros(1),q,q,q,.02,IKConfig(),execution_valid=lambda ik,u:ik.valid,
        measured=ref.body,active_wheel=torch.tensor([0]),execution_mode=torch.tensor([1]),
        previous_support_offset=zero,proposed_support_offset=off)
    assert result.valid.item()
    assert result.command_ik.iterations[0,1]>0 and result.command_ik.iterations[0,3]>0
    assert result.command_ik.residual_m.max()<=.0001
    assert (result.command_ik.q-q).abs().max()<=.05

def test_invalid_active_offset_is_rejected():
    q,ref=fixture();off=q.new_tensor([[.001,-.001,0.,0.]])
    with pytest.raises(ValueError):
        execution_targets(ref,ref.body,torch.tensor([0]),q,q.new_ones(1),
            torch.tensor([1]),support_offset_w_z=off)

@pytest.mark.parametrize('mode,old_value,new_value',[(1,0.,.0002),(1,.001,.0012),(2,.001,.0008)])
def test_backtrack_scales_support_increment_only_once(mode,old_value,new_value):
    from ame_baseline.m1_teacher_ik import solve_constrained_ik
    q,ref=fixture();zero=q.new_zeros(1,4);off=zero.clone();off[0,1]=new_value;off[0,3]=-new_value
    old=zero.clone();old[0,1]=old_value;old[0,3]=-old_value
    old_goal=execution_targets(ref,ref.body,torch.tensor([0]),q,q.new_ones(1),torch.tensor([mode]),support_offset_w_z=old)
    last=solve_constrained_ik(q,old_goal.body_goal,q,IKConfig(),tolerance_m=q.new_full((1,4),1e-8))
    assert last.valid.item()
    calls=[]
    def accept_second(ik,u):
        calls.append(1)
        return ik.valid & (len(calls)>1)
    result=backtrack_feedback_reference(ref,ref,q.new_zeros(1,3),q.new_zeros(1,3),
        q.new_zeros(1),q,q,last.q,.02,IKConfig(),execution_valid=accept_second,
        measured=ref.body,active_wheel=torch.tensor([0]),execution_mode=torch.tensor([mode]),
        previous_support_offset=old,proposed_support_offset=off)
    assert result.valid.item() and result.backtrack_index.item()==1
    delta=result.execution_target.body_step-body_feet(q)
    world=torch.einsum('bij,bkj->bki',_rotation(ref.body.quat_w),delta)
    fraction=result.execution_target.fraction[:,None]
    assert torch.allclose(world[:,:,2],old+fraction*(off-old),atol=1e-8,rtol=0)
