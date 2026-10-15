import importlib.util
import pytest
import torch
from ame_baseline.m1_teacher_pose import BodyPose,PoseReference,_rotation


def api():
    assert importlib.util.find_spec('ame_baseline.m1_teacher_attitude') is not None, 'attitude geometry module missing'
    from ame_baseline.m1_teacher_attitude import centered_support_attitude_error
    return centered_support_attitude_error


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('active',range(4))
def test_centered_error_has_no_active_or_common_heave(dtype,active):
    root=torch.tensor([[0.,0.,.6]],dtype=dtype);quat=root.new_tensor([[1.,0.,0.,0.]])
    wheels=root.new_tensor([[[.3,.2,.1],[.3,-.2,.1],[-.3,.2,.1],[-.3,-.2,.1]]])
    cmd=PoseReference(BodyPose(root,quat),wheels)
    q=quat.clone();q[0,0]=torch.cos(root.new_tensor(.025));q[0,1]=torch.sin(root.new_tensor(.025))
    out=api()(cmd,BodyPose(root,q),torch.tensor([active]))
    assert out.valid.item() and out.error_m.abs().max()>0
    assert out.error_m[0,active]==0 and out.error_m.sum().abs()<1e-8
    same=api()(cmd,cmd.body,torch.tensor([active]))
    assert same.valid.item() and same.error_m.abs().max()<1e-8
    sign=api()(cmd,BodyPose(root,-q),torch.tensor([active]))
    assert torch.allclose(out.error_m,sign.error_m,atol=1e-8,rtol=0)


def test_translation_and_global_yaw_invariance():
    root=torch.tensor([[0.,0.,.6]],dtype=torch.float64);q=root.new_tensor([[1.,0.,0.,0.]])
    cmd=PoseReference(BodyPose(root,q),root.new_tensor([[[.3,.2,.1],[.3,-.2,.1],[-.3,.2,.1],[-.3,-.2,.1]]]))
    measured=BodyPose(root,root.new_tensor([[.9987502603949663,.04997916927067833,0.,0.]]))
    out=api()(cmd,measured,torch.tensor([0]))
    yaw=root.new_tensor([[.7071067811865476,0.,0.,.7071067811865476]])
    rot=_rotation(yaw);shift=root.new_tensor([[20.,-50.,3.]])
    move=lambda p:torch.einsum('bij,bj->bi',rot,p)+shift
    # q_yaw * q_roll, wxyz.
    qm=measured.quat_w;product=torch.stack((yaw[:,0]*qm[:,0],yaw[:,0]*qm[:,1],yaw[:,3]*qm[:,1],yaw[:,3]*qm[:,0]),-1)
    changed=PoseReference(BodyPose(move(root),yaw),torch.einsum('bij,bkj->bki',rot,cmd.wheels_w)+shift[:,None])
    actual=api()(changed,BodyPose(move(root),product),torch.tensor([0]))
    assert torch.allclose(out.error_m,actual.error_m,atol=1e-12,rtol=0)


def test_invalid_row_is_finite_and_not_valid():
    root=torch.tensor([[0.,0.,.6]]).repeat(3,1);q=root.new_tensor([[1.,0.,0.,0.]]).repeat(3,1)
    wheels=root.new_tensor([[[.3,.2,.1],[.3,-.2,.1],[-.3,.2,.1],[-.3,-.2,.1]]]).repeat(3,1,1)
    measured=q.clone();measured[1,0]=float('nan');measured[2,0]=2
    out=api()(PoseReference(BodyPose(root,q),wheels),BodyPose(root,measured),torch.zeros(3,dtype=torch.long))
    assert out.valid.tolist()==[True,False,False]
    assert torch.isfinite(out.error_m).all() and out.error_m[1:].abs().max()==0
