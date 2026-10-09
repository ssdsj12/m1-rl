import importlib
import math
import pytest
import torch


def predict(*args, **kwargs):
    mod=importlib.import_module('ame_baseline.m1_mass_predictor')
    return mod.predict(*args, **kwargs)


def model():
    return dict(root='base', bodies=[dict(name='base',mass=2.,com=[0.,0.,0.]),
        dict(name='tip',mass=1.,com=[1.,0.,0.])], joints=[dict(name='hinge',
        parent='base',child='tip',pos0=[1.,0.,0.],pos1=[0.,0.,0.],
        rot0=[1.,0.,0.,0.],rot1=[1.,0.,0.,0.],axis='Z')])


def inputs():
    return torch.tensor([[0.],[math.pi/2]],dtype=torch.float64),torch.zeros(2,3,dtype=torch.float64),torch.tensor([[1.,0.,0.,0.]]*2,dtype=torch.float64)


def test_actual_joint_angle_changes_mass_weighted_com_per_row():
    q,p,r=inputs(); out=predict(model(),('hinge',),q,p,r)
    torch.testing.assert_close(out['com'],torch.tensor([[2/3,0.,0.],[1/3,1/3,0.]],dtype=q.dtype))
    assert out['valid'].tolist()==[True,True]


def test_both_joint_frames_and_child_anchor_are_consumed():
    m=model(); j=m['joints'][0];j['pos1']=[.5,0.,0.]
    j['rot0']=[math.sqrt(.5),0.,0.,math.sqrt(.5)]
    q,p,r=inputs(); q.zero_()
    out=predict(m,('hinge',),q,p,r)
    torch.testing.assert_close(out['com'][0],torch.tensor([1/3,1/6,0.],dtype=q.dtype))
    j['rot1']=j['rot0']
    out=predict(m,('hinge',),q,p,r)
    torch.testing.assert_close(out['com'][0],torch.tensor([.5,0.,0.],dtype=q.dtype))


def test_root_pose_rotates_then_translates_com():
    q,p,r=inputs();q.zero_();p[:,0]=3.;r[:]=torch.tensor([math.sqrt(.5),0.,0.,math.sqrt(.5)])
    out=predict(model(),('hinge',),q,p,r)
    torch.testing.assert_close(out['com'],torch.tensor([[3.,2/3,0.]]*2,dtype=q.dtype),atol=1e-7,rtol=1e-7)


def test_invalid_row_is_masked_without_corrupting_other_row():
    q,p,r=inputs();q[1]=float('nan')
    out=predict(model(),('hinge',),q,p,r)
    assert out['valid'].tolist()==[True,False]
    assert torch.isfinite(out['com']).all()


def test_nonunit_root_is_not_silently_treated_as_valid():
    q,p,r=inputs();r[1]*=2
    assert predict(model(),('hinge',),q,p,r)['valid'].tolist()==[True,False]


@pytest.mark.parametrize('names',[('wrong',),('hinge','hinge')])
def test_names_fail_closed(names):
    q,p,r=inputs()
    with pytest.raises(ValueError):predict(model(),names,q,p,r)


def test_disconnected_tree_fails_closed():
    q,p,r=inputs();m=model();m['joints'][0]['parent']='missing'
    with pytest.raises(ValueError):predict(m,('hinge',),q,p,r)
