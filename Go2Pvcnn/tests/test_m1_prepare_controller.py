"""Shared PREPARE ownership: no timer-only lift permission or batch barrier."""
import importlib.util
import torch
import ast
from pathlib import Path
from types import SimpleNamespace
import pytest


def setup_controller():
    assert importlib.util.find_spec('ame_baseline.m1_prepare_controller') is not None, 'missing production-reusable PREPARE controller'
    from ame_baseline.m1_prepare_controller import M1PrepareController
    from ame_baseline.m1_ame_contract import M1_TRAINING_ROOT_Z_M, M1_TRAINING_JOINT_POS
    from extension.parallelism.m1_kinematics import m1_fk
    from extension.parallelism.rl_adapter import resolve_named_indices
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES
    cols = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    root = torch.tensor([[0.,0.,M1_TRAINING_ROOT_Z_M]]).repeat(4,1)
    rpy = torch.zeros_like(root)
    q = torch.tensor([M1_TRAINING_JOINT_POS]).repeat(4,1)[:,cols]
    anchors = m1_fk(root,rpy,q).foot_pos_w
    ctrl = M1PrepareController(root=root,rpy=rpy,joint=q,anchors=anchors,
        selected=torch.arange(4),episode=torch.zeros(4,dtype=torch.long),
        obstacle=torch.zeros(4,dtype=torch.long),total_weight=torch.full((4,),41.045319557*9.81))
    return ctrl, root, anchors


def observation(root, anchors):
    # Independent signed triangle margin calculation, using actual COM input.
    com = root + root.new_tensor([.026,.006,-.11])
    ids = torch.tensor([[1,2,3],[0,2,3],[0,1,3],[0,1,2]])
    tri = anchors.gather(1,ids[:,:,None].expand(-1,-1,3))[:,:,:2]
    edge = tri.roll(-1,1)-tri
    ab,ac=tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]
    area=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    delta=com[:,None,:2]-tri
    margin=((edge[:,:,0]*delta[:,:,1]-edge[:,:,1]*delta[:,:,0])*area.sign()[:,None]/edge.norm(dim=-1)).min(-1).values
    return dict(com_w=com,wheel_pos_w=anchors,force=torch.full((4,4),100.),
        tilt=torch.zeros(4,2),tilt_rate=torch.zeros(4,2),margin=margin,
        valid=torch.ones(4,dtype=torch.bool))


def test_per_environment_prepare_preserves_anchors_and_needs_measured_support():
    from extension.parallelism.m1_kinematics import m1_fk
    ctrl, root, anchors=setup_controller()
    seen_ready=torch.zeros(4,dtype=torch.bool)
    for step in range(200):
        old_q=ctrl.joint.clone()
        result=ctrl.update(observed=observation(root,anchors),live_root=root,
            collision=torch.zeros(4,dtype=torch.bool),step=torch.full((4,),step,dtype=torch.long),dt=.02)
        assert result['accepted'].all(), result['reason']
        assert ((result['joint']-old_q).abs()<=.010001).all()
        torch.testing.assert_close(m1_fk(result['root'],torch.zeros_like(root),result['joint']).foot_pos_w,anchors,atol=2e-5,rtol=0)
        root=result['root'].clone()  # ideal plant ONLY; not physical evidence
        seen_ready |= result['ready']
    assert seen_ready.all()
    assert result['ready'].all()
    assert not result['lift_authorized'].any(), 'PREPARE is not measured UNLOAD'


def test_no_measured_com_response_cannot_pass_prepare_by_waiting():
    ctrl, root, anchors=setup_controller()
    for step in range(200):
        result=ctrl.update(observed=observation(root,anchors),live_root=root,
            collision=torch.zeros(4,dtype=torch.bool),step=torch.full((4,),step,dtype=torch.long),dt=.02)
        assert not result['ready'][0], 'a commanded shift is not a measured shift'
        assert not result['lift_authorized'].any()


def test_collision_and_stale_frames_are_local_and_latched():
    ctrl, root, anchors=setup_controller()
    for step in range(200):
        clocks=torch.full((4,),step,dtype=torch.long)
        if step==3: clocks[1]=2
        collision=torch.tensor([step==0,False,False,False])
        result=ctrl.update(observed=observation(root,anchors),live_root=root,
            collision=collision,step=clocks,dt=.02)
        root=result['root'].clone()
    assert result['failed'].tolist()==[True,True,False,False]
    assert result['ready'].tolist()==[False,False,True,True]
    # A new episode may reset only the affected row, never other environments.
    previous=ctrl.joint[1:].clone()
    ctrl.reset_rows(torch.tensor([0]),root=root[:1],rpy=torch.zeros(1,3),
        joint=ctrl.joint[:1],anchors=anchors[:1],selected=torch.tensor([0]),
        episode=torch.tensor([1]),obstacle=torch.tensor([0]))
    assert ctrl.failed.tolist()==[False,True,False,False]
    torch.testing.assert_close(ctrl.joint[1:],previous)


def test_physical_probe_uses_controller_and_rejects_non_equivalent_effort():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    guards=[n for n in tree.body if isinstance(n,ast.If) and 'args.batched_prepare' in ast.unparse(n.test)
            and 'args.phase_effort' in ast.unparse(n.test)]
    assert guards, 'new controller probe must reject incompatible actuator experiments before startup'
    args=SimpleNamespace(batched_prepare=True,phase_effort=True)
    with pytest.raises(ValueError):
        exec(compile(ast.Module(body=[guards[0]],type_ignores=[]),'probe_guard','exec'),{'args':args})
    assert any(isinstance(n,ast.Call) and ast.unparse(n.func)=='prepare_controller.update' for n in ast.walk(tree))


def test_probe_finishes_with_fresh_evidence_and_explicit_matching_deadline():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    ctor=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and ast.unparse(n.func)=='M1PrepareController')
    assert any(k.arg=='timeout_steps' and ast.unparse(k.value)=='args.num_steps + 1' for k in ctor.keywords)
    assert any(isinstance(n,ast.Call) and ast.unparse(n.func)=='prepare_controller.finish' for n in ast.walk(tree))


def test_prepare_action_reaches_the_existing_m1_decoder_without_wheel_drive():
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS, m1_action_targets
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices
    ctrl,root,anchors=setup_controller()
    for step in range(20):
        result=ctrl.update(observed=observation(root,anchors),live_root=root,
            collision=torch.zeros(4,dtype=torch.bool),step=torch.full((4,),step,dtype=torch.long),dt=.02)
        root=result['root'].clone()
    assert callable(getattr(ctrl,'position_action',None)), 'shared controller needs exact production action encoding'
    default=torch.tensor([M1_TRAINING_JOINT_POS]).repeat(4,1)
    action,eligible=ctrl.position_action(default)
    assert eligible.all()
    assert (action[:,3::4]==0).all()
    target=m1_action_targets(action,default)
    cols=list(resolve_named_indices(M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES))
    torch.testing.assert_close(target[:,cols],ctrl.joint)
    ctrl.failed[0]=True
    _,eligible=ctrl.position_action(default)
    assert eligible.tolist()==[False,True,True,True]


def test_prepare_root_reference_accelerates_and_brakes_with_existing_limit():
    ctrl,root,anchors=setup_controller()
    previous_velocity=torch.zeros(4,2)
    for step in range(200):
        previous_root=ctrl.root.clone()
        result=ctrl.update(observed=observation(root,anchors),live_root=root,
            collision=torch.zeros(4,dtype=torch.bool),step=torch.full((4,),step,dtype=torch.long),dt=.02)
        velocity=(result['root'][:,:2]-previous_root[:,:2])/.02
        assert (velocity.norm(dim=-1)<=.04001).all()
        assert ((velocity-previous_velocity).norm(dim=-1)/.02<=.0501).all(), 'PREPARE must not command a1m/s² velocity jump'
        if result['ready'].any():
            assert (velocity[result['ready']].norm(dim=-1)<=.00101).all(), 'cannot hand off a moving reference'
        previous_velocity=velocity
        root=result['root'].clone()


def test_prepare_deadline_requires_fresh_final_readiness_not_budget_expiry():
    ctrl,root,anchors=setup_controller()
    assert callable(getattr(ctrl,'finish',None)), 'bounded PREPARE needs explicit final evidence'
    # Acceptable but not settled attitude can never satisfy the readiness gate.
    for step in range(8):
        obs=observation(root,anchors)
        obs['tilt'][:]=.20
        result=ctrl.update(observed=obs,live_root=root,collision=torch.zeros(4,dtype=torch.bool),
            step=torch.full((4,),step,dtype=torch.long),dt=.02)
        root=result['root'].clone()
    outcome=ctrl.finish(step=torch.full((4,),7,dtype=torch.long))
    assert not outcome['ready'].any()
    assert outcome['failed'].all()
    assert outcome['reason'].tolist()==[9]*4


def test_prepare_final_certificate_cannot_reuse_an_old_frame():
    ctrl,root,anchors=setup_controller()
    assert callable(getattr(ctrl,'finish',None))
    for step in range(200):
        result=ctrl.update(observed=observation(root,anchors),live_root=root,
            collision=torch.zeros(4,dtype=torch.bool),step=torch.full((4,),step,dtype=torch.long),dt=.02)
        root=result['root'].clone()
    assert result['ready'].all()
    outcome=ctrl.finish(step=torch.full((4,),198,dtype=torch.long))
    assert not outcome['ready'].any()
    assert outcome['failed'].all()


def test_shared_root_ramp_allows_a_stricter_speed_without_changing_acceleration():
    from ame_baseline.m1_com_trajectory import root_step
    import inspect
    assert 'max_speed' in inspect.signature(root_step).parameters
    entry=torch.zeros(1,3)
    root=entry.clone(); velocity=torch.zeros(1,2)
    target=torch.tensor([[.06,0.,0.]])
    for _ in range(100):
        result=root_step(entry,root,velocity,target,dt=.02,max_speed=.02)
        assert result['valid'].all()
        assert result['velocity'].norm(dim=-1).max()<=.0200001
        assert ((result['velocity']-velocity).norm(dim=-1)/.02).max()<=.050001
        root,velocity=result['root'],result['velocity']


def test_final_observation_does_not_commit_an_unexecuted_command():
    ctrl,root,anchors=setup_controller()
    for step in range(200):
        result=ctrl.update(observed=observation(root,anchors),live_root=root,
            collision=torch.zeros(4,dtype=torch.bool),step=torch.full((4,),step,dtype=torch.long),dt=.02)
        root=result['root'].clone()
        if result['ready'].all():
            break
    before=[x.clone() for x in (ctrl.root,ctrl.joint,ctrl.velocity)]
    ctrl.update(observed=observation(root,anchors),live_root=root,
        collision=torch.zeros(4,dtype=torch.bool),step=torch.full((4,),step+1,dtype=torch.long),dt=.02,
        advance_reference=False)
    for actual,expected in zip((ctrl.root,ctrl.joint,ctrl.velocity),before):
        assert torch.equal(actual,expected), 'final read must retain last executed command'
    result=ctrl.finish(step=torch.full((4,),step+1,dtype=torch.long))
    assert result['ready'].all()


def test_probe_batched_budget_is_bounded_and_does_not_expand_legacy_mode():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    guard=next(n for n in tree.body if isinstance(n,ast.If)
        and 'args.num_steps' in ast.unparse(n.test))
    check=compile(ast.Module(body=[guard],type_ignores=[]),'budget_guard','exec')
    exec(check,{'args':SimpleNamespace(num_steps=200,batched_prepare=True)})
    for steps,batched in ((201,True),(201,False),(0,True)):
        with pytest.raises(ValueError):
            exec(check,{'args':SimpleNamespace(num_steps=steps,batched_prepare=batched)})


def test_prepare_default_deadline_preserves_approved_four_seconds():
    ctrl,_,_=setup_controller()
    assert ctrl.timeout_steps==200


def test_probe_final_measurement_does_not_advance_reference():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    final_calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)
        and ast.unparse(n.func)=='prepare_controller.update'
        and any(k.arg=='step' and ast.unparse(k.value)=='final_clock' for k in n.keywords)]
    assert len(final_calls)==1
    assert any(k.arg=='advance_reference' and ast.unparse(k.value)=='False'
               for k in final_calls[0].keywords)
