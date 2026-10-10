"""Bounded scene/reset integration checks; forced stages are NOT learned skill."""
import argparse
import json
import traceback
from isaaclab.app import AppLauncher

parser=argparse.ArgumentParser(description=__doc__)
AppLauncher.add_app_launcher_args(parser)
args=parser.parse_args()
launcher=AppLauncher(args)
env=None
try:
    import torch
    import omni.usd
    from pxr import Usd,UsdGeom
    from isaaclab.envs import ManagerBasedRLEnv
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_mixed_course import configure_flat_first_terrain,progressive_row
    from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
    from extension.semantic_course import terrain_column_names_from_generator
    cfg=M1AmeCrossLargeComplexEnvCfg()
    configure_flat_first_terrain(cfg)
    cfg.scene.num_envs=4
    cfg.sim.device=args.device
    cfg.seed=42
    env=ManagerBasedRLEnv(cfg=cfg)
    wrapper=AmeRslRlEnvWrapper(env)
    terrain=env.scene.terrain
    names=terrain_column_names_from_generator(cfg.scene.terrain.terrain_generator)
    records=terrain.grounded_course_obstacles
    assert not any(r.row==0 for r in records)
    assert torch.all(terrain.terrain_levels==0)
    assert all(names[int(t)]=='flat' for t in terrain.terrain_types)
    assert not wrapper._m1_current_course()['valid'].any()
    assert cfg.commands.base_velocity.rel_standing_envs==0
    assert not env.scene['robot'].is_fixed_base
    assert getattr(env,'_trajectory_manager',None) is None
    stage=omni.usd.get_context().get_stage()
    bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),[UsdGeom.Tokens.default_])
    measured={}
    for row in (1,2,3):
        objects=[r for r in records if r.row==row and r.col==0 and r.semantic_class=='small']
        assert len(objects)==progressive_row(row)[0]
        heights=[]
        for obj in objects:
            bounds=bbox.ComputeWorldBound(stage.GetPrimAtPath(obj.prim_path)).ComputeAlignedRange()
            height=float(bounds.GetMax()[2]-bounds.GetMin()[2])
            assert abs(height-progressive_row(row)[1])<1e-4
            heights.append(height)
        measured[row]=heights
    zeros=torch.zeros((4,16),device=args.device)
    # Real settled no-debug steps must produce measured recovery readiness.
    recovery_checks=[]
    for _ in range(100):
        obs,_,_,extra=wrapper.step(zeros)
        assert torch.isfinite(obs).all()
        recovery_checks.append(float(extra['log']['RequiredCrossing/recovery_ready_fraction']))
    assert max(recovery_checks[-20:])>0, 'Healthy settled recovery never became ready'
    assert (env._m1_learning_gate.steps==100).all()
    assert env._m1_learning_gate.stage==0
    reset_checks=[]
    reward_checks=[]
    scan_checks=[]
    for curriculum_stage in (1,2,3,4,0):
        # Diagnostic-only state assignment to test every reset path; no checkpoint.
        env._m1_learning_gate.stage=curriculum_stage
        wrapper.reset()
        course=wrapper._m1_current_course()
        count=course['valid'].sum(-1)
        if curriculum_stage<4:
            assert (terrain.terrain_levels==curriculum_stage).all()
            assert (count==progressive_row(curriculum_stage)[0]).all()
        else:
            assert (terrain.terrain_levels>=4).all()
        assert (env._m1_learning_gate.steps==0).all()
        reset_checks.append({'stage':curriculum_stage,'counts':count.tolist()})
        if curriculum_stage in (1,2,3):
            # Diagnostic placement near the first block, never used by train.
            robot=env.scene['robot']
            pose=robot.data.root_state_w[:,:7].clone()
            pose[:,0]=course['centers_top'][:,0,0]-.6
            robot.write_root_pose_to_sim(pose)
            robot.write_root_velocity_to_sim(torch.zeros((4,6),device=args.device))
            for _ in range(8):
                obs,reward,done,extra=wrapper.step(zeros)
                assert torch.isfinite(obs).all() and torch.isfinite(reward).all()
                raw=env.reward_manager._step_reward.sum(-1)*env.step_dt
                log=extra['log']
                removed=log['RequiredCrossing/removed_positive_reward']
                bonus=log['RequiredCrossing/event_bonus']
                assert torch.allclose(reward.mean(),raw.mean()-removed+bonus,atol=1e-5)
                reward_checks.append({'stage':curriculum_stage,'zone':float(log['RequiredCrossing/zone_fraction']),
                    'removed':float(removed),'bonus':float(bonus),'done':int(done.sum())})
            assert any(r['zone']>0 and r['removed']>0 for r in reward_checks if r['stage']==curriculum_stage)
            # Inspect the real observation returned to PPO, not a synthetic map.
            from ame_baseline.ame_observations import _quat_apply_inverse, _yaw_quat
            scanner=env.scene['semantic_height_scanner']
            encoded=obs[:,:1536].reshape(4,6,16,16)
            local=encoded[:,:3].flatten(2).transpose(1,2)
            quat=scanner.data.quat_w.clone()
            if getattr(scanner.cfg,'ray_alignment',None)=='yaw':quat=_yaw_quat(quat)
            quat[:,1:]*=-1
            world=_quat_apply_inverse(quat[:,None].expand(-1,256,-1),local)+scanner.data.pos_w[:,None]
            small=encoded[:,4].flatten(1)>0
            raw_small=(scanner.data.semantic_map.flatten(1)==1)&torch.isfinite(scanner.data.ray_hits_w).all(-1)
            assert small.any(-1).all() and raw_small.any(-1).all(), 'Live map missed near block'
            encoded_top=world[:,:,2].masked_fill(~small,-torch.inf).amax(-1)
            raw_top=scanner.data.ray_hits_w[:,:,2].masked_fill(~raw_small,-torch.inf).amax(-1)
            assert torch.allclose(encoded_top,raw_top,atol=1e-4), 'Pooling diluted real block height'
            scan_checks.append({'stage':curriculum_stage,'raw_top':raw_top.tolist(),'encoded_top':encoded_top.tolist()})
    print('M1_FLAT_FIRST_RESULT '+json.dumps({'scope':'geometry_and_reset_integration_not_learning',
        'initial_obstacles':0,'stage_heights':measured,'reset_checks':reset_checks,
        'policy_shape':list(obs.shape),'metrics':env._m1_learning_gate.metrics(),
        'reward_checks':reward_checks,'recovery_ready_last20':recovery_checks[-20:],
        'live_scan_checks':scan_checks}),flush=True)
except BaseException:
    traceback.print_exc()
    raise
finally:
    if env is not None:env.close()
    launcher.app.close()
