"""Captured support frame must not shorten legs when measured body sinks."""
import pytest
import torch
from ame_baseline.m1_teacher_pose import BodyPose,PoseReference
from ame_baseline.m1_teacher_ik import body_feet
from ame_baseline.m1_teacher_execution_targets import execution_targets


def setup(dtype=torch.float64,batch=1):
    q=torch.tensor([[0.,.3,-.6,0.,.3,-.6,0.,-.3,.6,0.,-.3,.6]],dtype=dtype).repeat(batch,1)
    pos=q.new_tensor([[0.,0.,.54]]).repeat(batch,1)
    quat=q.new_tensor([[1.,0.,0.,0.]]).repeat(batch,1)
    body=BodyPose(pos,quat);command=PoseReference(body,body_feet(q)+pos[:,None])
    return q,body,command,command.wheels_w[:,:,2].clone()


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('active',range(4))
@pytest.mark.parametrize('mode',[1,2])
def test_measured_sink_does_not_shorten_support_targets(dtype,active,mode):
    q,body,command,height=setup(dtype)
    args=(command,body,torch.tensor([active]),q,q.new_ones(1),torch.tensor([mode]))
    base=execution_targets(*args,support_reference_w_z=height,support_capture_root_z=body.pos_w[:,2])
    pos=body.pos_w.clone();pos[:,2]-=.001
    moved=execution_targets(command,BodyPose(pos,body.quat_w),args[2],q,args[4],args[5],
        support_reference_w_z=height,support_capture_root_z=body.pos_w[:,2])
    support=[j for j in range(4) if j!=active]
    assert torch.allclose(moved.body_goal[:,support],base.body_goal[:,support],atol=1e-7,rtol=0)
    # Activity uses the original measured-goal path only in LIFT/PASS.
    expected=.001 if mode==1 else 0.
    assert float(moved.body_goal[0,active,2]-base.body_goal[0,active,2])==pytest.approx(expected,abs=1e-7)


def test_first_capture_is_exact_legacy_and_rows_are_independent():
    q,body,command,height=setup(batch=2);active=torch.tensor([0,3]);mode=torch.tensor([1,2]);one=q.new_ones(2)
    legacy=execution_targets(command,body,active,q,one,mode,support_reference_w_z=height)
    captured=execution_targets(command,body,active,q,one,mode,support_reference_w_z=height,support_capture_root_z=body.pos_w[:,2])
    assert torch.equal(legacy.body_goal,captured.body_goal)
    pos=body.pos_w.clone();pos[0,2]-=.002;pos[1,2]+=.003
    moved=execution_targets(command,BodyPose(pos,body.quat_w),active,q,one,mode,support_reference_w_z=height,support_capture_root_z=body.pos_w[:,2])
    assert torch.allclose(moved.body_goal[0,1:],legacy.body_goal[0,1:],atol=1e-12,rtol=0)
    assert torch.allclose(moved.body_goal[1,:3],legacy.body_goal[1,:3],atol=1e-12,rtol=0)


@pytest.mark.parametrize('bad',['shape','dtype','nan','inf','missing_height','mode0'])
def test_invalid_origin_rejected(bad):
    q,body,command,height=setup();origin=body.pos_w[:,2].clone();mode=torch.tensor([1])
    if bad=='shape':origin=origin[:,None]
    elif bad=='dtype':origin=origin.float()
    elif bad=='nan':origin[:]=float('nan')
    elif bad=='inf':origin[:]=float('inf')
    elif bad=='missing_height':height=None
    else:mode[:]=0
    with pytest.raises(ValueError):
        execution_targets(command,body,torch.tensor([0]),q,q.new_ones(1),mode,
            support_reference_w_z=height,support_capture_root_z=origin)
