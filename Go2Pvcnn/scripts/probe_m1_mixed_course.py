#!/usr/bin/env python3
"""Bounded four-env scene/measurement check; no lift or training claim."""
import argparse
import json
import sys
import traceback
from collections import Counter
from pathlib import Path

PACKAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACKAGE));sys.path.insert(0,str(PACKAGE/'rsl_rl'))
from isaaclab.app import AppLauncher
parser=argparse.ArgumentParser(description=__doc__)
AppLauncher.add_app_launcher_args(parser)
args=parser.parse_args()
launcher=AppLauncher(args)
env=None
failure=None
try:
    import torch
    import omni.usd
    from pxr import Usd,UsdGeom
    from isaaclab.envs import ManagerBasedRLEnv
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_mixed_course import configure_mixed_terrain,flat_counts,REFERENCE_NONPLANE_SMALL,REFERENCE_NONPLANE_LARGE
    from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
    from extension.semantic_course import terrain_column_names_from_generator
    cfg=M1AmeCrossLargeComplexEnvCfg()
    configure_mixed_terrain(cfg)
    # This probe pins representative cells. Production retains the reference
    # curriculum, whose reset hook legitimately changes terrain levels.
    assert cfg.curriculum.terrain_levels is not None
    cfg.curriculum.terrain_levels=None
    cfg.scene.num_envs=4;cfg.sim.device=args.device
    cfg.sim.dt=.001;cfg.decimation=1;cfg.seed=7
    cfg.events.reset_base.params['pose_range']={'x':(0.,0.),'y':(0.,0.),'yaw':(0.,0.)}
    cfg.events.reset_robot_joints.params['velocity_range']=(0.,0.)
    print('M1_MIXED_STAGE config_ready',flush=True)
    assert cfg.robot_name=='m1' and cfg.action_dim==16
    env=ManagerBasedRLEnv(cfg=cfg)
    terrain=env.scene.terrain
    names=terrain_column_names_from_generator(cfg.scene.terrain.terrain_generator)
    assert set(names)=={'flat','random_rough','hf_pyramid_slope','hf_pyramid_slope_inv','boxes','pyramid_stairs','pyramid_stairs_inv'}
    records=terrain.grounded_course_obstacles
    counts=Counter((x.row,x.col,x.semantic_class) for x in records)
    for row in range(10):
        for col,name in enumerate(names):
            expected=flat_counts(row) if name=='flat' else (REFERENCE_NONPLANE_SMALL[row],REFERENCE_NONPLANE_LARGE[row])
            assert tuple(counts[(row,col,kind)] for kind in ('small','large'))==expected,(row,col,name,expected)
    flat=names.index('flat');rough=names.index('random_rough')
    terrain.terrain_levels.copy_(torch.tensor([0,9,0,9],device=args.device))
    terrain.terrain_types.copy_(torch.tensor([flat,flat,rough,rough],device=args.device))
    terrain.env_origins.copy_(terrain.terrain_origins[terrain.terrain_levels,terrain.terrain_types])
    env.reset()
    wrapper=AmeRslRlEnvWrapper(env)
    actual=wrapper._m1_current_course()
    assert actual['valid'].sum(-1).tolist()==[15,165,0,4],(terrain.terrain_levels.tolist(),actual['valid'].sum(-1).tolist())
    assert not env.scene['robot'].is_fixed_base and wrapper.num_actions==16
    print('M1_MIXED_STAGE registry_ready '+json.dumps({'records':len(records),'env_counts':[15,165,0,4]}),flush=True)
    stage=omni.usd.get_context().get_stage()
    bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),[UsdGeom.Tokens.default_])
    # Validate every small collider's live world bounds, not only metadata.
    max_top_error=0.;minimum_height=float('inf');maximum_height=0.;measured=0
    for obj in records:
        if obj.semantic_class!='small':continue
        prim=stage.GetPrimAtPath(obj.prim_path)
        if not prim.IsValid():raise RuntimeError('missing obstacle '+obj.prim_path)
        bounds=bbox.ComputeWorldBound(prim).ComputeAlignedRange()
        low,high=bounds.GetMin(),bounds.GetMax()
        height=float(high[2]-low[2])
        assert abs(height-.10)<1e-4,(obj.prim_path,height)
        assert abs((high[0]+low[0])/2-obj.world_center[0])<1e-4
        assert abs((high[1]+low[1])/2-obj.world_center[1])<1e-4
        top_error=abs(high[2]-(obj.world_center[2]+.05))
        assert top_error<1e-4
        max_top_error=max(max_top_error,top_error)
        minimum_height=min(minimum_height,height);maximum_height=max(maximum_height,height);measured+=1
    print('M1_MIXED_STAGE geometry_ready '+json.dumps({'measured_small':measured,'max_top_error':max_top_error}),flush=True)
    for step in range(2):
        wrapper.step(torch.zeros((4,16),device=args.device))
        print('M1_MIXED_STAGE neutral_step='+str(step),flush=True)
    assert not wrapper._m1_strict_crossing.crossing_count.any()
    obs,extra=wrapper.get_observations()
    assert torch.isfinite(obs).all()
    scanner=env.scene['semantic_height_scanner']
    assert torch.isfinite(scanner.data.ray_hits_w[...,2]).any()
    # Move only the probe's second robot near one known flat obstacle without
    # advancing physics; verify real rays and labels, not just finite terrain.
    robot=env.scene['robot'];probe_ids=torch.tensor([1],device=args.device)
    pose=robot.data.root_pos_w[1:2].clone()
    pose[0,:2]=actual['centers_top'][1,0,:2]+pose.new_tensor([-.35,0.])
    root_pose=torch.cat((pose,robot.data.root_quat_w[1:2]),dim=-1)
    robot.write_root_pose_to_sim(root_pose,env_ids=probe_ids)
    scanner.update_env_ids(probe_ids)
    small_mask=scanner.data.semantic_map[1].flatten()==1
    assert small_mask.any(),'scanner cannot see actual small obstacles'
    hits=scanner.data.ray_hits_w[1][small_mask]
    real_centers=actual['centers_top'][1][actual['valid'][1]]
    nearest=torch.cdist(hits[:,:2],real_centers[:,:2]).argmin(-1)
    semantic_scan_top_error=(hits[:,2]-real_centers[nearest,2]).abs().max().item()
    assert semantic_scan_top_error<1e-3,semantic_scan_top_error
    print('M1_MIXED_COURSE_RESULT '+json.dumps({
        'scope':'scene_and_two_neutral_steps_not_crossing','terrain_families':list(dict.fromkeys(names)),
        'spawned_records':len(records),'measured_small':measured,'small_height_range':[minimum_height,maximum_height],
        'max_top_error':max_top_error,'env_small_counts':actual['valid'].sum(-1).tolist(),
        'policy_shape':list(obs.shape),'critic_shape':list(extra['observations']['critic'].shape),
        'actions':wrapper.num_actions,'strict_crossings':wrapper._m1_strict_crossing.crossing_count.tolist(),
        'semantic_small_rays':int(small_mask.sum()),'semantic_scan_top_error':semantic_scan_top_error,
    }),flush=True)
except BaseException as exc:
    failure=exc
    print('M1_MIXED_COURSE_ERROR '+repr(exc),file=sys.stderr,flush=True)
    traceback.print_exc()
finally:
    if env is not None:env.close()
    launcher.app.close()
if failure is not None:
    raise SystemExit(1)
