import importlib
import torch
import pytest
from extension.parallelism.m1_kinematics import m1_fk,M1_DEFAULT_JOINT_POS,M1_ROOT_Z_M


def fixture():
    bodies=[dict(name='base',mass=20.,com=[0.,0.,0.])];joints=[]
    for leg,front,side in zip(('FBL','FAR','RBL','RAR'),(1,1,-1,-1),(1,-1,1,-1)):
        parent='base'
        for kind,offset,mass,axis in zip(('ABAD','HIP','KNEE','FOOT'),
            ([.272*front,.065*side,0.],[.0575*front,.039*side,0.],[0.,.0442*side,-.26],[0.,.0592*side,-.28]),(.3,2.6,1.6,.7),('X','Y','Y','Y')):
            name=f'{leg}_{kind}'
            bodies.append(dict(name=name,mass=mass,com=[0.,0.,0.]))
            joints.append(dict(name=name+'_JOINT',parent=parent,child=name,pos0=offset,pos1=[0.,0.,0.],rot0=[1.,0.,0.,0.],rot1=[1.,0.,0.,0.],axis=axis));parent=name
    root=torch.tensor([[0.,0.,M1_ROOT_Z_M]]*2,dtype=torch.float64);rpy=torch.zeros_like(root)
    anchor=m1_fk(root,rpy,root.new_tensor(M1_DEFAULT_JOINT_POS).expand(2,12)).foot_pos_w
    return dict(model=dict(root='base',bodies=bodies,joints=joints),roots=root[:,None],rpys=rpy[:,None],
        anchors=anchor,selected=torch.tensor([0,3]),wheel_q=torch.zeros(2,4,dtype=root.dtype),heights=root.new_tensor([0.,.08,.16]))


def test_only_selected_wheel_moves_through_all_heights():
    x=fixture(); f=getattr(importlib.import_module('ame_baseline.m1_anticipatory_support'),'forecast_lift')
    out=f(**x)
    assert out['min_load'].shape==(2,1,3)
    assert out['reachable'].all()
    assert torch.isfinite(out['min_margin']).all()
    for row,leg in enumerate((0,3)):
        delta=out['wheel_targets'][row,0]-x['anchors'][row]
        expected=torch.zeros_like(delta);expected[:,leg,2]=x['heights']
        torch.testing.assert_close(delta,expected)


@pytest.mark.parametrize('heights',[[.08,.16],[0.,-.01],[0.,.16,.08]])
def test_bad_height_path_fails_closed(heights):
    x=fixture();x['heights']=x['roots'].new_tensor(heights)
    f=getattr(importlib.import_module('ame_baseline.m1_anticipatory_support'),'forecast_lift')
    with pytest.raises(ValueError):f(**x)
