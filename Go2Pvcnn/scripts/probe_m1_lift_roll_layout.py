"""Four-env candidate-only native placement checks, never policy training.

Diagnostic joint placements are not a swing/controller and produce no PPO data.
Run only after the verified training process has exited and GPU0 is released.
"""
import argparse
import json
from dataclasses import replace
from isaaclab.app import AppLauncher

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--asset',required=True)
parser.add_argument('--reference-only',action='store_true',help='Measure empty-ground controls only; never accepts a layout')
parser.add_argument('--fold-ticks',type=int,default=56,help='Physics samples for both candidate and paired control')
AppLauncher.add_app_launcher_args(parser)
args=parser.parse_args()
assert args.fold_ticks>=5
launcher=AppLauncher(args)
env=None
try:
    import torch
    import omni.usd
    from pxr import Usd,UsdGeom
    from isaaclab.envs import ManagerBasedRLEnv
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_mixed_course import configure_flat_first_terrain,progressive_row
    from ame_baseline.m1_lift_roll_layout import candidate_blocks
    from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    from ame_baseline.m1_crossing_clearance import wheel_bottom_from_vertices
    from ame_baseline.m1_lift_roll_probe_checks import assess_frame,PlacementEvidence,compare_placement,summarize_native
    from extension.parallelism.rl_adapter import resolve_named_indices
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
    cfg=M1AmeCrossLargeComplexEnvCfg()
    configure_flat_first_terrain(cfg)
    cfg.scene.terrain.semantic_course_layout_cfg=replace(
        cfg.scene.terrain.semantic_course_layout_cfg,placement_strategy='m1_lift_roll')
    cfg.scene.robot.spawn.usd_path=args.asset
    cfg.scene.num_envs=4
    cfg.sim.device=args.device
    cfg.seed=42
    env=ManagerBasedRLEnv(cfg=cfg)
    wrapper=AmeRslRlEnvWrapper(env)
    robot=env.scene['robot'];sensor=env.scene['contact_forces'];terrain=env.scene.terrain
    records=terrain.grounded_course_obstacles
    assert not any(r.row==0 for r in records)
    stage=omni.usd.get_context().get_stage()
    bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),[UsdGeom.Tokens.default_])
    geometry=[]
    for row in (1,2,3):
        cols=sorted({r.col for r in records if r.row==row})
        manifest=candidate_blocks(row,fill_gap=.20)
        for col in cols:
            objs=sorted((r for r in records if (r.row,r.col)==(row,col)),key=lambda r:r.slot_index)
            assert len(objs)==len(manifest)
            for obj,block in zip(objs,manifest):
                assert obj.required_crossing is block.required_crossing
                assert obj.semantic_class=='small'
                assert obj.shape_params['size']==(block.length,block.width,block.height)
                bounds=bbox.ComputeWorldBound(stage.GetPrimAtPath(obj.prim_path)).ComputeAlignedRange()
                for k,size in enumerate((block.length,block.width,block.height)):
                    assert abs(float(bounds.GetMax()[k]-bounds.GetMin()[k])-size)<2e-4
                    assert abs(float((bounds.GetMax()[k]+bounds.GetMin()[k])/2)-obj.world_center[k])<2e-4
        geometry.append(dict(row=row,columns=len(cols),targets=progressive_row(row)[0],fill=70))
    zeros=torch.zeros((4,16),device=args.device)
    wheel_ids=list(resolve_named_indices(tuple(robot.body_names),M1_SUPPORT_BODY_NAMES))
    contact_ids=list(resolve_named_indices(tuple(sensor.body_names),M1_SUPPORT_BODY_NAMES))
    nonwheel_ids=[i for i,n in enumerate(sensor.body_names) if n not in M1_SUPPORT_BODY_NAMES]
    joint_ids=list(resolve_named_indices(tuple(robot.joint_names),M1_ASSET_JOINT_NAMES))
    for _ in range(40):
        obs,_,done,_=wrapper.step(zeros)
        assert not done.any() and torch.isfinite(obs).all()

    def place(root_x,joints=None):
        state=robot.data.default_root_state.clone()
        state[:,:3]+=env.scene.env_origins
        state[:,0]=root_x
        robot.write_root_state_to_sim(state)
        q=robot.data.default_joint_pos.clone() if joints is None else joints
        robot.write_joint_state_to_sim(q,torch.zeros_like(q))
        robot.set_joint_position_target(q)
        robot.set_joint_velocity_target(torch.zeros_like(q))
        return state.clone(),q.clone()

    def measured_steps(requested,course,*,label,selected=None,ticks=8,reference=None):
        state,q=requested
        history=PlacementEvidence()
        expected=torch.ones((4,4),device=args.device,dtype=torch.bool)
        if selected is not None:
            expected[torch.arange(4,device=args.device),selected]=False
        nonfoot=[joint_ids[i] for i in range(16) if i%4!=3]
        for tick in range(ticks):
            env.scene.write_data_to_sim();env.sim.step(render=False);env.scene.update(env.physics_dt)
            wheels=robot.data.body_pos_w[:,wheel_ids]
            bottom=wheel_bottom_from_vertices(wheels,robot.data.body_quat_w[:,wheel_ids],wrapper._m1_wheel_vertices_b)
            offset=(wheels[:,:,None,:2]-course['landing_centers_top'][:,None,:,:2]).abs()-course['landing_half_extents'][:,None]
            margin=(torch.linalg.vector_norm(offset.clamp_min(0),dim=-1)-.119208).masked_fill(~course['landing_valid'][:,None],torch.inf).amin(-1)
            clearance=bottom.new_full((4,),.03) if selected is None else bottom.gather(1,selected[:,None]).squeeze(1)-course['centers_top'][:,label['target'],2]
            actual_quat=robot.data.root_quat_w/robot.data.root_quat_w.norm(dim=-1,keepdim=True)
            requested_quat=state[:,3:7]/state[:,3:7].norm(dim=-1,keepdim=True)
            dot=(actual_quat*requested_quat).sum(-1).abs().clamp(0,1)
            evidence=assess_frame(wheel_force=sensor.data.net_forces_w[:,contact_ids],bottom=bottom,
                ground=env.scene.env_origins[:,2],margin=margin,expected=expected,
                nonwheel_force=sensor.data.net_forces_w[:,nonwheel_ids],clearance=clearance,
                root_error=(robot.data.root_pos_w-state[:,:3]).norm(dim=-1),angle_error=2*torch.acos(dot),
                joint_error=(robot.data.joint_pos[:,nonfoot]-q[:,nonfoot]).abs().amax(-1))
            evidence.update(root_delta=(robot.data.root_pos_w-state[:,:3]).tolist(),
                joint_delta=(robot.data.joint_pos[:,nonfoot]-q[:,nonfoot]).tolist(),
                root_quat=robot.data.root_quat_w.tolist(),physics_dt=env.physics_dt,
                requested_joints=q[:,nonfoot].tolist())
            history.record(evidence)
            print('M1_PLACEMENT_FRAME '+json.dumps(dict(**label,tick=tick,**evidence,
                requested_root=state[:,:7].tolist(),actual_root=robot.data.root_state_w[:,:7].tolist(),
                actual_joints=robot.data.joint_pos[:,nonfoot].tolist())),flush=True)
        result=compare_placement(history.frames,history.frames if reference is None else reference.frames)
        history.summary=result
        print('M1_PLACEMENT_RESULT '+json.dumps(dict(**label,**result)),flush=True)
        # Support/pose fixture failures are unverified samples, not proof that
        # the approved rolling action or this layout is physically impossible.
        # Collect every case; the final aggregate fails closed. A nominal
        # placement failure must not hide later scan/geometry evidence.
        return history

    scans=[];recoveries=[];folds=[]
    for row in (1,2,3):
        env._m1_learning_gate.stage=row
        wrapper.reset()
        course=wrapper._m1_current_course()
        assert (course['valid'].sum(-1)==progressive_row(row)[0]).all()
        assert (course['landing_valid'].sum(-1)==progressive_row(row)[0]+70).all()
        for _ in range(8):
            obs,_,done,_=wrapper.step(zeros)
            assert not done.any()
        scanner=env.scene['semantic_height_scanner']
        rays=scanner.data.ray_hits_w
        raw_small=scanner.data.semantic_map==1
        hit_counts=[]
        for e in range(4):
            fill=[r for r in records if r.row==row and r.col==int(terrain.terrain_types[e]) and r.required_crossing is False]
            p=rays[e].reshape(-1,3);sem=raw_small[e].reshape(-1);hits=torch.zeros(len(p),dtype=torch.bool,device=p.device)
            for r in fill:
                c=p.new_tensor(r.world_center);size=p.new_tensor(r.shape_params['size'])
                hits|=sem & ((p[:,:2]-c[:2]).abs()<=size[:2]/2+1e-4).all(-1) & ((p[:,2]-(c[2]+size[2]/2)).abs()<1e-3)
            assert hits.any(),('fill_missing_from_live_scan',row,e)
            hit_counts.append(int(hits.sum()))
        assert (obs[:,:1536].reshape(4,6,16,16)[:,4]>0).any(-1).any(-1).all()
        scans.append(dict(row=row,actual_fill_ray_hits=hit_counts))
        wrapper.reset();course=wrapper._m1_current_course()
        recovery_reference=measured_steps(place(env.scene.env_origins[:,0]),course,
            label=dict(kind='recovery_reference',row=row,target=0),ticks=56)
        fold_references={}
        if args.reference_only:
            for target in (0,1):
                wrapper.reset();course=wrapper._m1_current_course()
                legs=[target]*2+[target+2]*2
                q=robot.data.default_joint_pos.clone()
                delta={1:.30,2:.45,3:.60}[row]
                for e,leg in enumerate(legs):
                    q[e,joint_ids[4*leg+1]]-=delta/2
                    q[e,joint_ids[4*leg+2]]+=delta
                measured_steps(place(env.scene.env_origins[:,0],q),course,
                    label=dict(kind='fold_reference',row=row,target=target),
                    selected=torch.tensor(legs,device=args.device),ticks=args.fold_ticks)
            continue
        for target in range(progressive_row(row)[0]):
            for selected_x in (.3295,-.3295):
                for travel in (0.,.045):
                    wrapper.reset();course=wrapper._m1_current_course()
                    root_x=course['centers_top'][:,target,0]+.05+.119208+.04-selected_x+travel
                    history=measured_steps(place(root_x),course,label=dict(kind='recovery',row=row,target=target,selected_x=selected_x,travel=travel),ticks=56,reference=recovery_reference)
                    minimum=min(f['min_support_margin'] for f in history.frames)
                    max_other_force=max(f['max_nonwheel_force'] for f in history.frames)
                    _,_,done,extra=wrapper.step(zeros)
                    runtime_ready=not bool(done.any()) and float(extra['log']['RequiredCrossing/recovery_ready_fraction'])==1.
                    assert not wrapper._m1_strict_crossing.recovered.any(), 'Placement must not fabricate a receipt'
                    recoveries.append(dict(row=row,target=target,selected_x=selected_x,travel=travel,min_margin=minimum,max_nonwheel_force=max_other_force,runtime_ready=runtime_ready,**history.summary))
            # Both same-side front/rear cases in parallel. Static native states
            # along body translation, not a reference trajectory or PPO rollout.
            left=target%2==0
            legs=[0 if left else 1]*2+[2 if left else 3]*2
            delta={1:.30,2:.45,3:.60}[row]
            for frac in (0.,.25,.5,.75,1.):
                wrapper.reset();course=wrapper._m1_current_course()
                offsets=course['centers_top'].new_tensor([.3295,.3295,-.3295,-.3295])
                root_x=course['centers_top'][:,target,0]-.209208+frac*.418416-offsets
                q=robot.data.default_joint_pos.clone()
                for e,leg in enumerate(legs):
                    q[e,joint_ids[4*leg+1]]-=delta/2
                    q[e,joint_ids[4*leg+2]]+=delta
                selected=torch.tensor(legs,device=args.device)
                if left not in fold_references:
                    fold_references[left]=measured_steps(place(env.scene.env_origins[:,0],q),course,
                        label=dict(kind='fold_reference',row=row,target=target),selected=selected,ticks=args.fold_ticks)
                    wrapper.reset();course=wrapper._m1_current_course()
                history=measured_steps(place(root_x,q),course,label=dict(kind='fold',row=row,target=target,fraction=frac),selected=selected,ticks=args.fold_ticks,reference=fold_references[left])
                folds.append(dict(row=row,target=target,fraction=frac,min_clearance=min(f['min_clearance'] for f in history.frames),**history.summary))
                print('M1_LIFT_ROLL_PROGRESS '+json.dumps(dict(row=row,target=target,fraction=frac)),flush=True)
    for row in (4,0):
        env._m1_learning_gate.stage=row;wrapper.reset();course=wrapper._m1_current_course()
        assert not wrapper._m1_strict_crossing.recovered.any()
        if row==0:assert not course['valid'].any() and not course['landing_valid'].any()
    conclusion=summarize_native(recoveries,folds,reference_only=args.reference_only)
    print('M1_LIFT_ROLL_NATIVE_RESULT '+json.dumps(dict(scope='placed_geometry_map_support_not_policy_skill',**conclusion,
        geometry=geometry,scans=scans,recovery_samples=len(recoveries),fold_samples=len(folds),
        recovery_min_margin=min((x['min_margin'] for x in recoveries),default=None),
        max_nonwheel_force=max((x['max_nonwheel_force'] for x in recoveries),default=None),
        fold_min_clearance=min((x['min_clearance'] for x in folds),default=None),policy_shape=list(obs.shape),
        recovery_results=recoveries,fold_results=folds)),flush=True)
    if not args.reference_only:
        assert conclusion['accepted'],'native placement acceptance incomplete; inspect per-case evidence'
except BaseException:
    import traceback
    traceback.print_exc()
    print('M1_LIFT_ROLL_NATIVE_FAILED',flush=True)
    raise
finally:
    if env is not None:env.close()
    launcher.app.close()
