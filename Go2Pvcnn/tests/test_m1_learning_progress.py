import importlib.util
import pytest
import torch


def new():
    assert importlib.util.find_spec('ame_baseline.m1_learning_progress') is not None
    from ame_baseline.m1_learning_progress import LearningProgress
    return LearningProgress(1,'cpu')


def tick(t,load=25.,progress=0.,safe=True,air=False,active=True,key=1,other=25.,before=True):
    forces=torch.zeros(1,4,3);forces[:,:,2]=other;forces[:,0,2]=load
    return t.update(key=torch.tensor([key]),selected=torch.tensor([0]),forces=forces,
        weight=torch.tensor([100.]),active=torch.tensor([active]),safe=torch.tensor([safe]),
        before=torch.tensor([before]),airborne=torch.tensor([air]),progress=torch.tensor([progress]))


def test_frozen_baseline_bounded_unloading_and_passage_no_repeat():
    t=new();tick(t)
    a=tick(t,load=12.5);b=tick(t,load=0.,air=True,progress=.5)
    c=tick(t,load=0.,air=True,progress=1.,before=False)
    assert a['unload_delta'].item()==pytest.approx(.5)
    assert b['unload_delta'].item()==pytest.approx(.5)
    assert b['passage_delta'].item()==pytest.approx(.5)
    assert c['passage_delta'].item()==pytest.approx(.5)
    tick(t,load=25.,progress=.2)
    again=tick(t,load=0.,air=True,progress=1.)
    assert again['unload_delta'].item()==0 and again['passage_delta'].item()==0


@pytest.mark.parametrize('reason',['unsafe','weak_support','inactive'])
def test_unsafe_improvement_never_backpaid(reason):
    t=new();tick(t)
    out=tick(t,load=0.,progress=.8,air=True,safe=reason!='unsafe',
        other=1. if reason=='weak_support' else 25.,active=reason!='inactive')
    assert out['unload_delta'].item()==0 and out['passage_delta'].item()==0
    out=tick(t,load=0.,progress=.8,air=True)
    assert out['unload_delta'].item()==0 and out['passage_delta'].item()==0


def test_missing_baseline_no_unload_credit_loaded_forward_no_passage_credit():
    t=new(); assert tick(t,load=0.,air=True)['unload_delta'].item()==0
    tick(t,load=25.)
    assert tick(t,progress=.5)['passage_delta'].item()==0
    assert tick(t,load=0.,air=True,progress=.5)['passage_delta'].item()==0


def test_reset_and_new_identity_start_clean():
    t=new();tick(t);tick(t,load=0.,air=True,progress=1.)
    tick(t,key=2);assert tick(t,load=0.,key=2)['unload_delta'].item()==1
    t.reset(torch.tensor([True]));tick(t,key=2)
    assert tick(t,load=0.,key=2)['unload_delta'].item()==1


def test_final_reward_caps_and_terminal_blocking():
    from ame_baseline.m1_required_crossing import required_crossing_reward
    out,_,bonus=required_crossing_reward(torch.zeros(3),torch.zeros(3,1),.02,
        blocked=torch.ones(3,dtype=torch.bool),collision=torch.tensor([False,True,False]),
        done=torch.tensor([False,False,True]),prelift=torch.zeros(3,dtype=torch.bool),
        recovery=torch.zeros(3,dtype=torch.bool),unload_delta=torch.ones(3),passage_delta=torch.ones(3))
    torch.testing.assert_close(bonus,torch.tensor([.4,0.,0.]))
