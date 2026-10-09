import importlib.util
from pathlib import Path
import torch
from extension.parallelism.m1_kinematics import m1_fk


def function():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_selected_world.py'
    assert path.exists(), 'selected world-frame correction missing'
    spec = importlib.util.spec_from_file_location('selected_world', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.selected_world_target


def data():
    root = torch.tensor([[0., 0., .554]]).repeat(4, 1)
    q = torch.tensor([[0., -.57, 1.1]*4]).repeat(4, 1)
    rpy = torch.zeros_like(root)
    live = root.clone(); live[:, 2] -= .003
    return dict(root=root, rpy=rpy, live_root=live, live_rpy=rpy,
                target=m1_fk(root,rpy,q).foot_pos_w, nominal=q, previous=q,
                selected=torch.arange(4), dt=.1)


def test_all_four_selected_feet_use_live_pose_without_changing_stance():
    x=data(); result=function()(**x)
    assert result['valid'].all()
    actual=m1_fk(x['live_root'],x['live_rpy'],result['joint']).foot_pos_w
    for row in range(4):
        torch.testing.assert_close(actual[row,row],x['target'][row,row],atol=1e-5,rtol=0)
        mask=torch.ones(12,dtype=torch.bool); mask[row*3:row*3+3]=False
        torch.testing.assert_close(result['joint'][row,mask],x['nominal'][row,mask])


def test_invalid_or_excessive_pose_rejects_without_writing_new_joint():
    x=data(); x['live_root'][0,2]-=.1; x['live_root'][1,0]=float('nan')
    result=function()(**x)
    assert not result['valid'][:2].any()
    torch.testing.assert_close(result['joint'][:2],x['previous'][:2])


def test_frame_guard_reports_live_and_previous_residual_separately():
    x=data(); x['live_root'][0,2]-=.03
    result=function()(**x)
    torch.testing.assert_close(result['full']['root_error'],x['live_root']-x['root'])
    assert result['full']['previous_root_error'].abs().max()==0
    assert result['full']['angle_error'].abs().max()==0


def test_correction_obeys_joint_slew():
    x=data(); x['dt']=.002
    result=function()(**x)
    assert ((result['joint']-x['previous']).abs()<=.001001).all()


def test_full_candidate_rejection_is_attributed_before_backtracking():
    x=data(); x['dt']=.002
    result=function()(**x)
    assert result['full']['reachable'].all()
    assert result['full']['limits'].all()
    assert not result['full']['slew'].any()
    assert (result['full']['max_delta'] > .001).all()


def test_frame_backtracking_advances_from_last_accepted_frame():
    x=data(); x['live_root'][:,2]-=.007; x['dt']=.02
    frame=None
    for _ in range(20):
        result=function()(**x,previous_frame=frame)
        assert result['valid'].all()
        assert ((result['joint']-x['previous']).abs()<=.010001).all()
        x['previous']=result['joint']
        frame=result['frame']
    actual=m1_fk(x['live_root'],x['live_rpy'],result['joint']).foot_pos_w
    torch.testing.assert_close(actual[torch.arange(4),torch.arange(4)],
                               x['target'][torch.arange(4),torch.arange(4)],atol=1e-5,rtol=0)


def test_vertical_mode_does_not_correct_xy_or_attitude():
    x=data(); x['live_root'][:,0]+=.01; x['live_rpy']=x['rpy'].clone(); x['live_rpy'][:,2]=.03
    result=function()(**x,vertical_only=True)
    assert result['valid'].all()
    torch.testing.assert_close(result['frame']['root'][:,:2],x['root'][:,:2])
    torch.testing.assert_close(result['frame']['root'][:,2],x['live_root'][:,2])
    torch.testing.assert_close(result['frame']['rpy'],x['rpy'])


def test_vertical_mode_keeps_full_measured_pose_safety_gate():
    x=data(); x['live_root'][0,0]+=.03; x['live_rpy']=x['rpy'].clone();x['live_rpy'][1,2]=.09
    result=function()(**x,vertical_only=True)
    assert not result['valid'][:2].any()


def test_height_only_compensates_tilt_preserving_body_xy_and_stance():
    x=data(); x['live_root'][:,0]+=.008
    x['live_rpy']=torch.tensor([[.01,.006,.02]]).repeat(4,1)
    result=function()(**x,height_only=True)
    assert result['valid'].all() and (result['scale']==1).all()
    rows=torch.arange(4)
    world=m1_fk(x['live_root'],x['live_rpy'],result['joint']).foot_pos_w
    torch.testing.assert_close(world[rows,rows,2],x['target'][rows,rows,2],atol=1e-5,rtol=0)
    zero=torch.zeros_like(x['root'])
    body=m1_fk(zero,zero,result['joint']).foot_pos_w
    nominal_body=m1_fk(zero,zero,x['nominal']).foot_pos_w
    torch.testing.assert_close(body[rows,rows,:2],nominal_body[rows,rows,:2],atol=1e-5,rtol=0)
    for row in range(4):
        mask=torch.ones(12,dtype=torch.bool);mask[row*3:row*3+3]=False
        torch.testing.assert_close(result['joint'][row,mask],x['nominal'][row,mask])


def test_height_only_preserves_frame_and_slew_guards():
    x=data();x['live_root'][0,0]+=.03
    x['live_rpy']=torch.tensor([[.01,.006,.02]]).repeat(4,1);x['dt']=.002
    result=function()(**x,height_only=True)
    assert not result['valid'][0]
    assert ((result['joint']-x['previous']).abs()<=.001001).all()


def test_height_activation_mask_retains_vertical_mode_until_settled():
    x=data(); x['live_rpy']=torch.tensor([[.01,.006,.02]]).repeat(4,1)
    active=torch.tensor([False,True,False,True])
    result=function()(**x,height_only=True,height_mask=active)
    old=function()(**x,vertical_only=True)
    exact=function()(**x,height_only=True)
    torch.testing.assert_close(result['joint'][~active],old['joint'][~active])
    torch.testing.assert_close(result['joint'][active],exact['joint'][active])
    torch.testing.assert_close(result['frame']['rpy'][~active],x['rpy'][~active])


def test_height_activation_uses_backtracking_when_mode_changes():
    x=data();x['live_rpy']=torch.tensor([[.01,.006,.02]]).repeat(4,1);x['dt']=.02
    old=function()(**x,vertical_only=True)
    x['previous']=old['joint']
    result=function()(**x,height_only=True,height_mask=torch.ones(4,dtype=torch.bool),previous_frame=old['frame'])
    assert result['valid'].all()
    assert ((result['joint']-x['previous']).abs()<=.010001).all()
