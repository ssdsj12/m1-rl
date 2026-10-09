import importlib
import torch
from extension.parallelism.m1_kinematics import m1_ik
from test_m1_lift_forecast import fixture


def test_fixed_reference_is_bounded_and_not_immediately_ready():
    x=fixture();root=x['roots'][:,0];rpy=x['rpys'][:,0]
    q,_=m1_ik(root,rpy,x['anchors']);goal=root.clone();goal[:,0]+=.04
    step=getattr(importlib.import_module('ame_baseline.m1_anticipatory_support'),'fixed_reference_step')
    out=step(entry=root,rpy=rpy,anchors=x['anchors'],previous=root,velocity=torch.zeros_like(root[:,:2]),previous_joint=q.reshape(2,12),goal=goal,dt=.02)
    assert out['valid'].all() and not out['post_lift_load_ready'].any()
    assert (out['root']-root).norm(dim=-1).max()<=.0000201
    assert (out['joint']-q.reshape(2,12)).abs().max()<=.01


def test_converged_reference_stays_fixed_and_rejects_outside_bound():
    x=fixture();root=x['roots'][:,0];rpy=x['rpys'][:,0]
    q,_=m1_ik(root,rpy,x['anchors'])
    step=getattr(importlib.import_module('ame_baseline.m1_anticipatory_support'),'fixed_reference_step')
    kw=dict(entry=root,rpy=rpy,anchors=x['anchors'],previous=root,velocity=torch.zeros_like(root[:,:2]),previous_joint=q.reshape(2,12),dt=.02)
    out=step(**kw,goal=root)
    assert out['valid'].all() and out['post_lift_load_ready'].all()
    goal=root.clone();goal[0,0]+=.081
    out=step(**kw,goal=goal)
    assert out['valid'].tolist()==[False,True]


def test_entry_plan_uses_only_entry_inputs_and_preserves_input_tensors():
    x=fixture();root=x['roots'][:,0];rpy=x['rpys'][:,0];before=x['anchors'].clone()
    plan=getattr(importlib.import_module('ame_baseline.m1_anticipatory_support'),'entry_plan')
    out=plan(model=x['model'],root=root,rpy=rpy,anchors=x['anchors'],selected=x['selected'],wheel_q=x['wheel_q'],height=.16)
    assert out['root'].shape==root.shape and out['valid'].shape==(2,)
    assert torch.equal(before,x['anchors'])
    assert (out['root']-root).norm(dim=-1).max()<=.08
    # This synthetic model is not the authored M1 mass distribution. Feasibility
    # is an output, not an assumption; invalid rows must fail closed.
    assert out['valid'].any()
    torch.testing.assert_close(out['root'][~out['valid']],root[~out['valid']])
    torch.testing.assert_close(out['rpy'][~out['valid']],rpy[~out['valid']])
    from ame_baseline.m1_anticipatory_support import forecast_lift
    ok=out['valid']
    evidence=forecast_lift(model=x['model'],roots=out['root'][ok,None],rpys=out['rpy'][ok,None],
        anchors=x['anchors'][ok],selected=x['selected'][ok],wheel_q=x['wheel_q'][ok],
        heights=torch.linspace(0.,.16,17,dtype=root.dtype))
    assert evidence['reachable'].all()
    assert (evidence['min_load']>=35.).all() and (evidence['min_margin']>=.02).all()
