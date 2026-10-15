from dataclasses import replace
import pytest
import torch
from ame_baseline.m1_teacher_pose import BodyPose, PoseReference, world_to_goal_body, backtrack_feedback_reference
from ame_baseline.m1_teacher_ik import body_feet, IKConfig


def fixture(dtype=torch.float64):
    q=torch.tensor([[0.,.3,-.6,0.,.3,-.6,0.,-.3,.6,0.,-.3,.6]],dtype=dtype)
    root=torch.tensor([[0.,0.,.62]],dtype=dtype)
    quat=torch.tensor([[1.,0.,0.,0.]],dtype=dtype)
    command=PoseReference(BodyPose(root,quat),body_feet(q)+root[:,None])
    measured=BodyPose(root+root.new_tensor([.01,0.,-.02]),root.new_tensor([[.9987502604,0.,.0499791693,0.]]))
    return q,command,measured


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('active',range(4))
@pytest.mark.parametrize('mode',[0,1,2])
def test_target_frames_and_bounded_start(dtype,active,mode):
    from ame_baseline.m1_teacher_execution_targets import execution_targets
    q,cmd,measured=fixture(dtype)
    r=execution_targets(cmd,measured,torch.tensor([active]),q,q.new_tensor([.125]),torch.tensor([mode]))
    expected=world_to_goal_body(cmd)
    if mode==1: expected[:,active]=world_to_goal_body(PoseReference(measured,cmd.wheels_w))[:,active]
    torch.testing.assert_close(r.body_goal,expected)
    expected_step=expected if mode==0 else body_feet(q)+.125*(expected-body_feet(q))
    torch.testing.assert_close(r.body_step,expected_step)


@pytest.mark.parametrize('bad',['quat','nan'])
def test_invalid_measurement_cannot_be_executable(bad):
    from ame_baseline.m1_teacher_execution_targets import execution_targets
    q,c,m=fixture()
    m=BodyPose(m.pos_w,m.quat_w*2) if bad=='quat' else BodyPose(m.pos_w*float('nan'),m.quat_w)
    r=execution_targets(c,m,torch.tensor([0]),q,q.new_ones(1),torch.tensor([1]))
    assert not torch.isfinite(r.body_step).all()


@pytest.mark.parametrize('bad',['active','mode','fraction','dtype','batch'])
def test_structural_contract(bad):
    from ame_baseline.m1_teacher_execution_targets import execution_targets
    q,c,m=fixture(); a=torch.tensor([0]); mode=torch.tensor([1]); f=q.new_ones(1)
    if bad=='active': a[0]=4
    if bad=='mode': mode[0]=3
    if bad=='fraction': f[0]=0
    if bad=='dtype': f=f.float()
    if bad=='batch': a=a.repeat(2)
    with pytest.raises(ValueError): execution_targets(c,m,a,q,f,mode)


@pytest.mark.parametrize('mode',[1,2])
def test_large_frame_switch_is_bounded_and_rejection_is_explicit(mode):
    q,c,m=fixture()
    if mode==2: c=PoseReference(BodyPose(c.body.pos_w+q.new_tensor([0.,0.,-.03]),c.body.quat_w),c.wheels_w)
    args=(c,c,q.new_zeros(1,3),q.new_zeros(1,3),q.new_zeros(1),q,q,q,.02,IKConfig())
    kw=dict(measured=m,active_wheel=torch.tensor([0]),execution_mode=torch.tensor([mode]))
    r=backtrack_feedback_reference(*args,execution_valid=lambda ik,u: ik.valid,**kw)
    assert r.valid.item()
    assert ((r.command_ik.q-q).abs()<=.05).all()
    assert r.backtrack_index.item()>0
    assert r.execution_target.fraction.item()<1
    rejected=backtrack_feedback_reference(*args,execution_valid=lambda ik,u: torch.zeros(1,dtype=torch.bool),**kw)
    assert not rejected.valid.item() and rejected.backtrack_index.item()==-1
