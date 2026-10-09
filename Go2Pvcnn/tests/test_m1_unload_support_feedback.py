"""Checks actual probe ownership and both UNLOAD exits without Isaac startup."""
import ast
from pathlib import Path


def test_opt_in_unload_support_does_not_replace_prepare_forecast():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
    assert any(any(isinstance(a,ast.Constant) and a.value=='--unload_support_feedback' for a in n.args) for n in calls)
    fixed=[n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='fixed_reference_step']
    assert len(fixed)==2
    switches=[n for n in ast.walk(tree) if isinstance(n,ast.If) and
        'args.anticipatory_prepare and (not args.unload_support_feedback)'==ast.unparse(n.test)]
    assert len(switches)==1


def test_normal_and_final_unload_exit_require_fresh_support_and_stopped_reference():
    source=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert 'ready_now &= load_ready_before & (transfer_velocity.norm(dim=-1)<=.001)' in source
    assert "ready_now &= final_transfer['valid'] & final_transfer['post_lift_load_ready']" in source


def test_acceleration_ramp_consumes_goal_not_already_speed_limited_step():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    ramps=[n for n in ast.walk(tree) if isinstance(n,ast.Call)
        and isinstance(n.func,ast.Name) and n.func.id=='root_step']
    assert len(ramps)==1
    target=ramps[0].args[3]
    assert isinstance(target,ast.IfExp)
    assert ast.unparse(target.body)=="transfer['desired_root']"
    assert ast.unparse(target.test)=='args.unload_support_feedback'


def test_goal_ramp_avoids_double_limiter_lag_without_relaxing_bounds():
    import torch
    from ame_baseline.m1_com_trajectory import root_step
    entry=torch.zeros(1,3,dtype=torch.float64);goal=entry.clone();goal[:,0]=.005
    good=entry.clone();bad=entry.clone();vg=torch.zeros(1,2,dtype=entry.dtype);vb=vg.clone()
    for _ in range(100):
        before=vg.clone()
        a=root_step(entry,good,vg,goal,dt=.02)
        # Old wiring sent one speed-limited step instead of the feasible goal.
        short=bad+(goal-bad).clamp(-.0008,.0008)
        b=root_step(entry,bad,vb,short,dt=.02)
        assert a['valid'].all() and b['valid'].all()
        good,vg=a['root'],a['velocity'];bad,vb=b['root'],b['velocity']
        assert ((vg-before).norm(dim=-1)/.02<=.050001).all()
        assert (vg.norm(dim=-1)<=.040001).all()
    assert (good-goal).norm()<.0001
    assert (good-goal).norm()<(bad-goal).norm()/10
