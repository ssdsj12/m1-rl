import torch
import pytest
from test_m1_single_lift import inputs,lift_function
from extension.parallelism.m1_kinematics import m1_fk


def test_attitude_feedback_corrects_stance_with_separate_selected_world_height():
    x=inputs();live=x['rpy'].clone();live[:,0]=.01
    world=dict(live_root=x['root'],live_rpy=live,
        previous_frame=dict(root=x['root'],rpy=x['rpy']),vertical_only=False,height_only=True)
    out=lift_function()(**x,world_feedback=world,
        attitude_feedback=dict(live_rpy=live,previous_rpy=x['rpy']))
    assert out['valid'].all(),out['reason']
    assert (out['rpy'][:,0]<0).all()
    torch.testing.assert_close(out['root'],x['root'])
    torch.testing.assert_close(out['rpy'][:,2],x['rpy'][:,2])
    assert (out['joint']-x['previous_joint']).abs().max()<=.010001
    predicted=m1_fk(out['root'],out['rpy'],out['joint']).foot_pos_w
    for row in range(4):
        others=[j for j in range(4) if j!=row]
        torch.testing.assert_close(predicted[row,others],x['anchor_w'][row,others],atol=1e-5,rtol=0)


def test_attitude_feedback_rejects_excessive_error_without_affecting_other_rows():
    x=inputs();live=x['rpy'].clone();live[0,0]=.081
    out=lift_function()(**x,attitude_feedback=dict(live_rpy=live,previous_rpy=x['rpy']))
    assert out['valid'].tolist()==[False,True,True,True]
    torch.testing.assert_close(out['joint'][0],x['previous_joint'][0])


def test_attitude_feedback_cannot_share_whole_body_feedback_owner():
    x=inputs()
    with pytest.raises(ValueError,match='ownership'):
        lift_function()(**x,pose_feedback={},attitude_feedback=dict(live_rpy=x['rpy'],previous_rpy=x['rpy']))


def test_probe_attitude_path_is_explicitly_opt_in():
    import ast
    from pathlib import Path
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
    assert any(any(isinstance(a,ast.Constant) and a.value=='--lift_attitude_feedback' for a in n.args) for n in calls)
    lift=next(n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='lift_target')
    kw=next((k for k in lift.keywords if k.arg=='attitude_feedback'),None)
    assert kw is not None and isinstance(kw.value,ast.IfExp)
    assert isinstance(kw.value.orelse,ast.Constant) and kw.value.orelse.value is None
