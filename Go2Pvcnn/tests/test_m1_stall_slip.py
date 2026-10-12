import importlib
import importlib.util
import math
from types import SimpleNamespace

import pytest
import torch


def module():
    assert importlib.util.find_spec('ame_baseline.m1_stall_slip') is not None, 'stall/slip module absent'
    return importlib.import_module('ame_baseline.m1_stall_slip')


def run_path(xs, dt=.02):
    m=module(); t=m.StallWindow(1,'cpu',dt)
    outputs=[]
    for x in xs:
        outputs.append(t.update(torch.tensor([x]),torch.tensor([[1,7]]),torch.tensor([True]),torch.tensor([False])))
    return t,outputs


def test_stall_warmup_and_bounded_rate():
    _,outs=run_path([0.]*111)
    assert all(o['rate'].item()==0 for o in outs[:100])
    assert outs[100]['rate'].item()==pytest.approx(.5)
    assert outs[-1]['progress'].item()==0


@pytest.mark.parametrize('speed,expected',[(.30,0),(.025,0),(.0125,.25),(0.,.5),(-.3,.5)])
def test_forward_window_threshold(speed,expected):
    _,outs=run_path([i*.02*speed for i in range(160)])
    assert outs[-1]['rate'].item()==pytest.approx(expected,abs=1e-5)


def test_retreat_and_retrace_do_not_reset_grace():
    _,outs=run_path([.3*i*.02 for i in range(101)]+[0.]*110+[.6]*10)
    assert outs[-1]['rate'].item()==pytest.approx(.5)


@pytest.mark.parametrize('dt',[.01,.03,.07])
def test_fractional_time_interpolation(dt):
    _,outs=run_path([.0125*i*dt for i in range(math.ceil(4/dt))],dt)
    assert outs[-1]['rate'].item()==pytest.approx(.25,abs=2e-5)


def test_rows_reset_identity_completion_and_nonfinite():
    m=module();t=m.StallWindow(3,'cpu',.02)
    x=torch.zeros(3);ids=torch.ones(3,2);active=torch.ones(3,dtype=torch.bool);complete=~active
    for _ in range(102):o=t.update(x,ids,active,complete)
    assert torch.allclose(o['rate'],torch.full((3,),.5))
    t.reset(torch.tensor([True,False,False])); ids[1,1]=2;complete[2]=True
    assert t.update(x,ids,active,complete)['rate'].sum()==0
    x[0]=float('nan')
    o=t.update(x,ids,active,complete)
    assert o['invalid'][0] and torch.isfinite(o['rate']).all()
    x[0]=0
    assert t.update(x,ids,active,complete)['rate'][0]==0


def test_disabled_stages_never_accumulate_window():
    m=module();t=m.StallWindow(1,'cpu',.02)
    for _ in range(200):o=t.update(torch.zeros(1),torch.ones(1,1),torch.tensor([False]),torch.tensor([False]))
    assert o['rate'].item()==0
    assert not t.update(torch.zeros(1),torch.ones(1,1),torch.tensor([True]),torch.tensor([False]))['warm'].item()


def test_slip_true_rolling_airborne_reverse_and_sideways():
    m=module();v=torch.zeros(4,4,3);w=v.clone();q=torch.tensor([1.,0,0,0]).expand(4,4,4)
    v[...,0]=.30;w[...,1]=.30/.0959
    w[1]=0;w[2]*=-1;v[3,:,1]=.3
    speed=m.rolling_contact_speed(v,w,q,.0959)
    f=torch.zeros_like(v);f[...,2]=20
    out=m.bounded_slip(speed,f)
    torch.testing.assert_close(out['rate'],torch.tensor([0.,.25,.25,.25]),atol=1e-6,rtol=0)
    f.zero_();assert m.bounded_slip(speed,f)['rate'].sum()==0


@pytest.mark.parametrize('force',[0.,1.,9.99,10.])
def test_only_current_upward_load_counts(force):
    m=module();f=torch.zeros(1,4,3);f[...,2]=force;f[...,0]=100
    assert m.bounded_slip(torch.ones(1,4),f)['rate'].item()==0


def test_slip_deadband_cap_invalid_and_wheel_count():
    m=module();f=torch.zeros(2,4,3);f[...,2]=20
    s=torch.tensor([[.03,.02,0.,.01],[float('nan'),.165,0.,0.]])
    out=m.bounded_slip(s,f)
    assert out['rate'][0]==0 and out['invalid'][1]
    assert out['rate'][1].item()==pytest.approx(.0625)
    assert m.bounded_slip(torch.ones(2,4)*100,f)['rate'].max()<=.25


def test_incremental_cost_bound_and_discounted_collision_comparison():
    m=module();dt=.02;gamma=.99
    _,outs=run_path([0.]*1000)
    rates=torch.tensor([o['rate'].item()+.25 for o in outs])
    assert (rates*dt).sum()<=14.00001
    # Incremental two-cost contribution cannot beat the immediate -20 failure
    # penalty by terminating now; does NOT prove total policy return ordering.
    assert float((rates*dt*gamma**torch.arange(1000)).sum())<20.
