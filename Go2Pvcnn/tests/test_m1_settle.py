import importlib.util
from pathlib import Path
import torch
import pytest


def admission():
    path=Path(__file__).parents[1]/'ame_baseline/m1_settle.py'
    assert path.exists(),'settle contact/deadline admission missing'
    spec=importlib.util.spec_from_file_location('settle',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.settle_allowed


def test_settle_never_extends_airborne_leg_budget():
    force=torch.full((3,4),30.);force[1,2]=0.;force[2,1]=float('nan')
    assert admission()(force,0,100).tolist()==[True,False,False]


def test_settle_timeout_rejects_even_loaded_wheels():
    force=torch.full((1,4),30.)
    assert admission()(force,99,100).item()
    assert not admission()(force,100,100).item()
    with pytest.raises(ValueError): admission()(force,0,101)


def test_confirmed_touchdown_may_settle_with_weak_contact_but_not_airborne():
    force=torch.full((4,4),40.);force[:,0]=torch.tensor([8.,0.,1.,8.])
    seen=torch.tensor([True,True,True,False])
    result=admission()(force,0,100,selected=torch.zeros(4,dtype=torch.long),touchdown_seen=seen)
    assert result.tolist()==[True,False,False,False]


def test_jitter_does_not_waive_three_support_force_or_deadline():
    force=torch.tensor([[8.,29.,40.,40.],[8.,40.,40.,40.]])
    kwargs=dict(selected=torch.zeros(2,dtype=torch.long),touchdown_seen=torch.ones(2,dtype=torch.bool))
    assert admission()(force,0,100,**kwargs).tolist()==[False,True]
    assert not admission()(force,100,100,**kwargs).any()


def test_weak_contact_admission_is_not_stable_landing_success():
    from ame_baseline.m1_prepare_gate import PrepareGate
    force=torch.tensor([[8.,40.,40.,40.]])
    zero=torch.zeros(1,dtype=torch.long)
    ready=PrepareGate(1,'cpu')
    for step in range(5):
        result=ready.update(episode=zero,obstacle=zero,leg=zero,step=zero+step,
            force=force,tilt=torch.zeros(1,2),tilt_rate=torch.zeros(1,2),
            margin=torch.tensor([.03]),ik_valid=torch.tensor([True]),collision=torch.tensor([False]))
        assert not result.any()
    assert ready.count.item()==0
