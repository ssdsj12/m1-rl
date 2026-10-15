import pytest
import torch
from test_m1_teacher_load_feedback_transaction import fixture
from ame_baseline.m1_teacher_execution_targets import execution_targets
from ame_baseline.m1_teacher_pose import BodyPose,PoseReference,_rotation
from ame_baseline.m1_teacher_ik import body_feet

@pytest.mark.parametrize('active',range(4))
@pytest.mark.parametrize('mode',[1,2])
def test_support_height_preserves_mode_specific_xy(active,mode):
    q,ref=fixture(); measured=ref.body
    command=PoseReference(BodyPose(measured.pos_w+q.new_tensor([[.02,-.03,.01]]),
                                  q.new_tensor([[1.,0.,0.,0.]])),ref.wheels_w)
    idx=torch.tensor([active]); m=torch.tensor([mode]);fraction=q.new_tensor([.25])
    old=execution_targets(command,measured,idx,q,fraction,m)
    height=ref.wheels_w[:,:,2]-.004
    offset=q.new_zeros(1,4);support=[j for j in range(4) if j!=active]
    offset[0,support[0]]=.001;offset[0,support[1]]=-.001
    out=execution_targets(command,measured,idx,q,fraction,m,
        support_reference_w_z=height,support_offset_w_z=offset)
    to_world=lambda x:measured.pos_w[:,None]+torch.einsum('bij,bkj->bki',_rotation(measured.quat_w),x)
    new_w,old_w=to_world(out.body_goal),to_world(old.body_goal)
    expected_xy=old_w[:,:,:2].clone()
    if mode==1:
        translation=command.wheels_w+measured.pos_w[:,None]-command.body.pos_w[:,None]
        expected_xy[:,support]=translation[:,support,:2]
    assert torch.allclose(new_w[:,:,:2],expected_xy,atol=1e-12,rtol=0)
    assert torch.allclose(new_w[:,support,2],(height+offset)[:,support],atol=1e-12,rtol=0)
    assert torch.allclose(out.body_goal[:,active],old.body_goal[:,active],atol=1e-12,rtol=0)
    assert torch.allclose(out.body_step,body_feet(q)+.25*(out.body_goal-body_feet(q)),atol=1e-12,rtol=0)

@pytest.mark.parametrize('bad',['shape','nan','mode0'])
def test_invalid_height_source_rejected(bad):
    q,ref=fixture();height=ref.wheels_w[:,:,2].clone();mode=torch.tensor([1])
    if bad=='shape':height=height[:,:3]
    if bad=='nan':height[0,2]=float('nan')
    if bad=='mode0':mode[:]=0
    with pytest.raises(ValueError):
        execution_targets(ref,ref.body,torch.tensor([0]),q,q.new_ones(1),mode,support_reference_w_z=height)

@pytest.mark.parametrize('mode',[1,2])
def test_height_transaction_backtracks_once(mode):
    from ame_baseline.m1_teacher_pose import backtrack_feedback_reference
    from ame_baseline.m1_teacher_ik import IKConfig
    q,ref=fixture(); old=ref.wheels_w[:,:,2].clone(); proposed=old.clone()
    if mode==2: proposed[:,3]-=.0002
    calls=[]
    def accept_second(ik,u):
        calls.append(1)
        return ik.valid & (len(calls)>1)
    result=backtrack_feedback_reference(ref,ref,q.new_zeros(1,3),q.new_zeros(1,3),
        q.new_zeros(1),q,q,q,.02,IKConfig(),execution_valid=accept_second,
        measured=ref.body,active_wheel=torch.tensor([0]),execution_mode=torch.tensor([mode]),
        previous_support_reference_w_z=old,proposed_support_reference_w_z=proposed)
    assert result.valid.item() and result.backtrack_index.item()==1
    world=ref.body.pos_w[:,None]+torch.einsum('bij,bkj->bki',_rotation(ref.body.quat_w),result.execution_target.body_step)
    fraction=result.execution_target.fraction[:,None]
    assert torch.allclose(world[:,1:,2],(old+fraction*(proposed-old))[:,1:],atol=1e-10,rtol=0)

@pytest.mark.parametrize('bad',['unpaired','shape','nan','mode0','lift_drift','restore_rate'])
def test_height_transaction_rejects_invalid_history(bad):
    from ame_baseline.m1_teacher_pose import backtrack_feedback_reference
    from ame_baseline.m1_teacher_ik import IKConfig
    q,ref=fixture();old=ref.wheels_w[:,:,2].clone();new=old.clone();mode=torch.tensor([1])
    if bad=='unpaired':new=None
    if bad=='shape':new=new[:,:3]
    if bad=='nan':new[0,1]=float('nan')
    if bad=='mode0':mode[:]=0
    if bad=='lift_drift':new[0,1]+=.0001
    if bad=='restore_rate':mode[:]=2;new[0,1]+=.0003
    with pytest.raises(ValueError):
        backtrack_feedback_reference(ref,ref,q.new_zeros(1,3),q.new_zeros(1,3),
            q.new_zeros(1),q,q,q,.02,IKConfig(),execution_valid=lambda ik,u:ik.valid,
            measured=ref.body,active_wheel=torch.tensor([0]),execution_mode=mode,
            previous_support_reference_w_z=old,proposed_support_reference_w_z=new)

def test_teacher_captures_applied_command_height_not_contact_height():
    from test_m1_teacher_load_feedback_transaction import load_teacher
    from test_m1_reference_teacher import advance
    teacher,s=load_teacher()
    expected=s.root_pos_w[:,None]+torch.einsum('bij,bkj->bki',_rotation(s.root_quat_w),body_feet(s.last_applied_leg_target))
    assert teacher.step(s).valid.item()
    saved=teacher._rows[0]['support_execution_z'].clone()
    assert torch.allclose(saved,expected[:,:,2])
    s=advance(s);s.root_pos_w[:,2]-=.001
    assert teacher.step(s).valid.item()
    assert torch.equal(saved,teacher._rows[0]['support_execution_z'])
    teacher.step(advance(s,episode_id=s.episode_id+1,reset_mask=torch.ones_like(s.reset_mask)))
    assert 'support_execution_z' not in teacher._rows[0]

def test_teacher_rejected_transaction_preserves_height(monkeypatch):
    from dataclasses import replace
    from test_m1_teacher_load_feedback_transaction import load_teacher
    import ame_baseline.m1_teacher_pose as p
    teacher,s=load_teacher();real=p.solve_constrained_ik
    monkeypatch.setattr(p,'solve_constrained_ik',lambda *a,**kw:replace(real(*a,**kw),valid=torch.zeros(a[0].shape[0],dtype=torch.bool)))
    assert not teacher.step(s).valid.item()
    assert 'support_execution_z' not in teacher._rows[0]

def test_teacher_restore_height_moves_bounded_toward_geometry():
    from test_m1_teacher_load_feedback_transaction import load_teacher
    teacher,s=load_teacher('RESTORE')
    old=(s.root_pos_w[:,None]+torch.einsum('bij,bkj->bki',_rotation(s.root_quat_w),body_feet(s.last_applied_leg_target)))[:,:,2]
    old=old-.002
    teacher._rows[0]['support_execution_z']=old.clone()
    teacher._rows[0]['support_capture_root_z']=s.root_pos_w[:,2].clone()
    out=teacher.step(s)
    assert out.valid.item()
    new=teacher._rows[0]['support_execution_z']
    assert not torch.equal(old[:,1:],new[:,1:])
    assert (new-old).abs().max()<=.00020001
    assert teacher._rows[0]['prepared']

def test_teacher_emits_height_transaction_and_rejection_history(monkeypatch):
    from dataclasses import replace
    from test_m1_teacher_load_feedback_transaction import load_teacher
    from test_m1_reference_teacher import advance,api
    import ame_baseline.m1_teacher_pose as p
    teacher,s=load_teacher();out=teacher.step(s)
    fields=api().TEACHER_DIAGNOSTIC_FIELDS
    assert out.diagnostic[0,fields.index('height_enabled')]==1
    assert out.diagnostic[0,fields.index('height_captured')]==1
    old=teacher._rows[0]['support_execution_z'].clone()
    for j in range(4):
        assert out.diagnostic[0,fields.index(f'height_committed_{j}')]==old[0,j]
    real=p.solve_constrained_ik
    monkeypatch.setattr(p,'solve_constrained_ik',lambda *a,**kw:replace(real(*a,**kw),valid=torch.zeros(a[0].shape[0],dtype=torch.bool)))
    rejected=teacher.step(advance(s))
    assert not rejected.valid.item()
    assert torch.equal(old,teacher._rows[0]['support_execution_z'])
    for j in range(4):
        assert rejected.diagnostic[0,fields.index(f'height_committed_{j}')]==old[0,j]
