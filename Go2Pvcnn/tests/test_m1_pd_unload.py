"""Measured PD-only unload; no fabricated WBC allocation/effort certificate."""
import torch
import pytest
import ast
from pathlib import Path
from types import SimpleNamespace
from test_m1_prepare_controller import setup_controller, observation


def prepared_state():
    ctrl,root,anchors=setup_controller()
    for step in range(190):
        result=ctrl.update(observed=observation(root,anchors),live_root=root,
            collision=torch.zeros(4,dtype=torch.bool),step=torch.full((4,),step,dtype=torch.long),dt=.02)
        root=result['root'].clone()
    assert result['ready'].all()
    return ctrl,root,anchors


def evidence(root,anchors,selected_force=60.):
    obs=observation(root,anchors)
    obs['force'][torch.arange(4),torch.arange(4)]=selected_force
    return obs


def tick(ctrl,obs,step,**kwargs):
    return ctrl.update(observed=obs,step=torch.full((4,),step,dtype=torch.long),
        collision=torch.zeros(4,dtype=torch.bool),actuator_ok=torch.ones(4,dtype=torch.bool),dt=.02,**kwargs)


def test_unload_only_shortens_selected_leg_and_requires_five_measured_frames():
    from ame_baseline.m1_pd_unload import M1PdUnloadController
    from extension.parallelism.m1_kinematics import m1_fk
    prepared,root,anchors=prepared_state()
    ctrl=M1PdUnloadController(prepared)
    old=ctrl.joint.clone()
    for step in range(15):
        result=tick(ctrl,evidence(root,anchors),step)
        assert result['accepted'].all()
        assert not result['ready'].any(), 'a rising reference is not measured unload'
        delta=m1_fk(ctrl.root,ctrl.rpy,ctrl.joint).foot_pos_w-anchors
        assert (delta[:,:,:2].abs()<2e-5).all()
        mask=~torch.eye(4,dtype=torch.bool)
        assert (delta[:,:,2][mask].abs()<2e-5).all()
        assert ((ctrl.joint-old).abs()<=.010001).all()
        old=ctrl.joint.clone()
    held=ctrl.joint.clone()
    for step in range(15,20):
        result=tick(ctrl,evidence(root,anchors,0.),step)
        assert result['ready'].all()==(step==19)
        assert torch.equal(ctrl.joint,held), 'stop shortening once measured unloaded'


def test_unload_rejects_stale_collision_and_wrong_actuator_locally():
    from ame_baseline.m1_pd_unload import M1PdUnloadController
    prepared,root,anchors=prepared_state()
    ctrl=M1PdUnloadController(prepared)
    tick(ctrl,evidence(root,anchors),0)
    result=ctrl.update(observed=evidence(root,anchors),step=torch.tensor([0,1,1,1]),
        collision=torch.tensor([False,True,False,False]),
        actuator_ok=torch.tensor([True,True,False,True]),dt=.02)
    assert result['failed'].tolist()==[True,True,True,False]
    result=tick(ctrl,evidence(root,anchors,0.),2)
    assert result['failed'].tolist()==[True,True,True,False]


def test_unload_no_motion_or_false_force_forecast_cannot_pass_deadline():
    from ame_baseline.m1_pd_unload import M1PdUnloadController
    prepared,root,anchors=prepared_state()
    ctrl=M1PdUnloadController(prepared)
    for step in range(100):
        result=tick(ctrl,evidence(root,anchors),step)
        assert not result['ready'].any()
        assert (ctrl.height<=.0200001).all()
    before=ctrl.joint.clone()
    tick(ctrl,evidence(root,anchors),100,advance_reference=False)
    assert torch.equal(before,ctrl.joint)
    final=ctrl.finish(step=torch.full((4,),100,dtype=torch.long))
    assert final['failed'].all() and not final['ready'].any()


def test_unload_support_deficit_does_not_advance_lift():
    from ame_baseline.m1_pd_unload import M1PdUnloadController
    prepared,root,anchors=prepared_state()
    ctrl=M1PdUnloadController(prepared)
    obs=evidence(root,anchors)
    obs['force'][0,1]=20.
    result=tick(ctrl,obs,0)
    assert result['accepted'][0] and not result['ready'][0]
    assert ctrl.height[0]==0
    obs['force'][0,1]=9.
    assert tick(ctrl,obs,1)['failed'][0]


def test_pd_contract_checks_actual_canonical_drives_and_no_extra_effort():
    from ame_baseline.m1_pd_unload import production_pd_valid
    k=torch.full((4,16),800.);d=torch.full((4,16),40.);f=torch.zeros(4,16)
    k[:,3::4]=0.;d[:,3::4]=5.
    assert production_pd_valid(k,d,f).all()
    f[0,1]=1.;k[1,2]=0.;d[2,3]=20.
    assert production_pd_valid(k,d,f).tolist()==[False,False,False,True]


def test_unload_action_roundtrip_and_unprepared_handoff_rejected():
    from ame_baseline.m1_pd_unload import M1PdUnloadController
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS,m1_action_targets
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES
    prepared,root,anchors=prepared_state()
    ctrl=M1PdUnloadController(prepared)
    tick(ctrl,evidence(root,anchors),0)
    default=torch.tensor([M1_TRAINING_JOINT_POS]).repeat(4,1)
    action,eligible=ctrl.position_action(default)
    assert eligible.all() and (action[:,3::4]==0).all()
    cols=[M1_ASSET_JOINT_NAMES.index(n) for n in M1_PLANNER_JOINT_NAMES]
    torch.testing.assert_close(m1_action_targets(action,default)[:,cols],ctrl.joint)
    prepared.ready[0]=False
    with pytest.raises(ValueError,match='prepared'):
        M1PdUnloadController(prepared)


def test_pd_unload_probe_requires_prepared_mode_and_two_second_limit():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    guards=[n for n in tree.body if isinstance(n,ast.If) and 'args.pd_unload_steps' in ast.unparse(n.test)]
    assert guards, 'PD-only diagnostic needs explicit bounded opt-in'
    guard=compile(ast.Module(body=[guards[0]],type_ignores=[]),'guard','exec')
    exec(guard,{'args':SimpleNamespace(pd_unload_steps=100,batched_prepare=True)})
    for n,enabled in ((101,True),(10,False),(-1,True)):
        with pytest.raises(ValueError):
            exec(guard,{'args':SimpleNamespace(pd_unload_steps=n,batched_prepare=enabled)})
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
    assert any(ast.unparse(n.func)=='production_pd_valid' for n in calls)
    call=next(n for n in calls if ast.unparse(n.func)=='pd_unload.update')
    expr=next(k.value for k in call.keywords if k.arg=='advance_reference')
    # Loop includes the final observation, but must not issue its next action.
    assert eval(compile(ast.Expression(expr),'advance','eval'),
                {'ustep':100,'args':SimpleNamespace(pd_unload_steps=100)}) is False
    assert eval(compile(ast.Expression(expr),'advance','eval'),
                {'ustep':99,'args':SimpleNamespace(pd_unload_steps=100)}) is True


def test_tracking_diagnostic_separates_body_pose_joint_lag_and_fk_mismatch():
    from ame_baseline.m1_pd_unload import tracking_diagnostics
    from extension.parallelism.m1_kinematics import m1_fk
    prepared,root,anchors=prepared_state()
    live=root.clone();live[:,2]-=.006
    actual=prepared.joint.clone();actual[:,1]+=.01
    wheel=m1_fk(live,prepared.rpy,actual).foot_pos_w
    report=tracking_diagnostics(reference_root=root,reference_rpy=prepared.rpy,
        live_root=live,live_rpy=prepared.rpy,command=prepared.joint,actual_joint=actual,
        wheel=wheel)
    assert (report['pose_delta'][:,:,:2].abs()<1e-6).all()
    torch.testing.assert_close(report['pose_delta'][:,:,2],torch.full((4,4),-.006),atol=1e-6,rtol=0)
    assert report['joint_tracking_delta'].abs().max()>.001
    assert report['fk_error'].abs().max()<1e-6


def test_world_height_compensates_measured_base_tilt_without_moving_stance_targets():
    from ame_baseline.m1_pd_unload import M1PdUnloadController
    from extension.parallelism.m1_kinematics import m1_fk
    prepared,root,anchors=prepared_state()
    ctrl=M1PdUnloadController(prepared,world_height=True)
    live=root.clone();live[:,2]-=.005
    attitude=prepared.rpy.clone();attitude[:,0]=.02;attitude[:,1]=-.01
    mask=(torch.arange(12)[None]//3)!=torch.arange(4)[:,None]
    for step in range(30):
        old=ctrl.joint.clone()
        result=tick(ctrl,evidence(root,anchors),step,live_root=live,live_rpy=attitude)
        assert result['accepted'].all(),result['reason']
        assert ((ctrl.joint-old).abs()<=.010001).all()
        assert torch.equal(ctrl.joint[mask],prepared.joint[mask])
    wheel=m1_fk(live,attitude,ctrl.joint).foot_pos_w
    z=wheel[torch.arange(4),torch.arange(4),2]
    goal=anchors[torch.arange(4),torch.arange(4),2]+ctrl.height
    torch.testing.assert_close(z,goal,atol=2e-5,rtol=0)
    assert (ctrl.height<=.02).all()
    # Readiness must retain the last executed command, not a new pose-correction
    # proposal that will not be applied because the caller hands off.
    for step in range(30,34):
        tick(ctrl,evidence(root,anchors,0.),step,live_root=live,live_rpy=attitude)
    old=ctrl.joint.clone()
    attitude[:,0]+=.001
    result=tick(ctrl,evidence(root,anchors,0.),34,live_root=live,live_rpy=attitude)
    assert result['ready'].all()
    assert torch.equal(ctrl.joint,old)


def test_world_compensation_cannot_hide_more_than_two_cm_total_shortening():
    from ame_baseline.m1_pd_unload import M1PdUnloadController
    from extension.parallelism.m1_kinematics import m1_fk
    prepared,root,anchors=prepared_state()
    ctrl=M1PdUnloadController(prepared,world_height=True)
    initial=m1_fk(ctrl.root,ctrl.rpy,ctrl.joint).foot_pos_w
    live=root.clone();live[:,2]-=.009
    attitude=prepared.rpy.clone();attitude[:,0]=.02;attitude[:,1]=-.01
    rejected=False
    for step in range(100):
        old=ctrl.joint.clone()
        result=tick(ctrl,evidence(root,anchors),step,live_root=live,live_rpy=attitude)
        actual_command=m1_fk(ctrl.root,ctrl.rpy,ctrl.joint).foot_pos_w
        shortening=(actual_command-initial)[torch.arange(4),torch.arange(4),2]
        assert (shortening<=.0200001).all(), 'frame compensation must count toward total shortening'
        if result['failed'].any():
            rejected=True
            assert torch.equal(ctrl.joint[result['failed']],old[result['failed']])
            assert not result['ready'].any()
            break
    assert rejected, 'do not silently increase the diagnostic envelope'
