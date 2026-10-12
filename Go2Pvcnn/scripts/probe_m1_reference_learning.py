"""Isolated native contract tests, never concurrent with training or a lift teacher."""
import argparse
import json
import faulthandler
from isaaclab.app import AppLauncher

parser=argparse.ArgumentParser(description=__doc__)
AppLauncher.add_app_launcher_args(parser)
args=parser.parse_args();launcher=AppLauncher(args);env=None
faulthandler.dump_traceback_later(60,repeat=True)
try:
    import torch
    from pxr import UsdGeom
    import omni.usd
    from isaaclab.actuators import DCMotor,ImplicitActuator
    from isaaclab.envs import ManagerBasedRLEnv
    from isaaclab.utils.math import euler_xyz_from_quat
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_mixed_course import configure_flat_first_terrain
    from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
    from ame_baseline.m1_learning_observations import m1_wheel_learning_observation,wheel_loads
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices
    from ame_baseline.m1_reference_geometry import cylinder_bottom
    cfg=M1AmeCrossLargeComplexEnvCfg();configure_flat_first_terrain(cfg)
    cfg.scene.num_envs=4;cfg.sim.device=args.device;cfg.seed=7
    # Headless measurement needs no remote arrow_x.usd visualization asset.
    cfg.commands.base_velocity.debug_vis=False
    cfg.events.reset_base.params['velocity_range']={k:(0.,0.) for k in ('x','y','z','roll','pitch','yaw')}
    # Kit may replace stderr/fault handlers during imports. Keep a dedicated
    # diagnostic descriptor and arm immediately before manager construction.
    trace_file=open('/tmp/m1-reference-native-stacks.log','a')
    faulthandler.enable(file=trace_file,all_threads=True)
    faulthandler.dump_traceback_later(30,repeat=True,file=trace_file)
    env=ManagerBasedRLEnv(cfg=cfg);wrapped=AmeRslRlEnvWrapper(env)
    robot=env.scene['robot'];ids=list(resolve_named_indices(tuple(robot.body_names),M1_SUPPORT_BODY_NAMES))
    assert isinstance(robot.actuators['legs'],DCMotor)
    assert isinstance(robot.actuators['wheels'],ImplicitActuator)
    assert torch.all(robot.actuators['legs'].stiffness==120) and torch.all(robot.actuators['legs'].damping==5.5)
    assert torch.all(robot.actuators['wheels'].damping==30)
    assert env.cfg.events.add_base_mass is None and wrapped.num_actions==12
    assert not getattr(env,'_trajectory_manager',None)
    assert cfg.scene.robot.spawn.articulation_props.solver_velocity_iteration_count==2
    stage=omni.usd.get_context().get_stage()
    for i in range(4):
        for name in M1_SUPPORT_BODY_NAMES:
            path=f'/World/envs/env_{i}/Robot/{name}'
            assert not stage.GetPrimAtPath(path+'/collisions').IsActive()
            wheel=UsdGeom.Cylinder(stage.GetPrimAtPath(path+'/wheel_collision'))
            assert wheel.GetAxisAttr().Get()=='Y' and abs(wheel.GetRadiusAttr().Get()-.0959)<1e-8
    _,weight=wheel_loads(env)
    materials=robot.root_physx_view.get_material_properties()
    assert torch.allclose(materials[...,:2],torch.ones_like(materials[...,:2]))
    assert torch.all(materials[...,2]==0)
    zero=torch.zeros(4,12,device=args.device);initial=robot.data.root_pos_w.clone()
    resets=0;max_tilt=0.;calls=[]
    update=wrapped._m1_strict_crossing.update
    def measured_update(**kwargs):
        assert kwargs['cylinder_geometry'] and kwargs['required_clearance']==0
        assert kwargs['wheel_forces'].shape==(4,4,3)
        out=update(**kwargs);calls.append(1)
        assert torch.isfinite(out['unload_delta']).all() and torch.isfinite(out['passage_delta']).all()
        return out
    wrapped._m1_strict_crossing.update=measured_update
    for i in range(150):
        obs,reward,done,extras=wrapped.step(zero);resets+=int(done.sum())
        assert obs.shape==(4,1621),obs.shape
        assert torch.isfinite(obs).all() and torch.isfinite(reward).all()
        feature=m1_wheel_learning_observation(env).reshape(4,4,8)
        assert torch.all(feature[:,:,4]==0),'flat terrain exposes obstacle features'
        r,p,_=euler_xyz_from_quat(robot.data.root_quat_w)
        tilt=torch.atan2(torch.sin(torch.stack((r,p))),torch.cos(torch.stack((r,p)))).abs()
        max_tilt=max(max_tilt,float(tilt.max()))
    advance=(robot.data.root_pos_w[:,0]-initial[:,0]).tolist()
    print('REFERENCE_FLAT '+json.dumps(dict(resets=resets,max_tilt=max_tilt,advance=advance,weight=weight.tolist())),flush=True)
    assert resets==0 and max_tilt<.15 and min(advance)>.3
    env._m1_learning_gate.stage=1;wrapped.reset()
    for _ in range(10):wrapped.step(zero)
    course=wrapped._m1_current_course();box=course['centers_top'][0][course['valid'][0]][0]
    # Measurements place a stationary test body; these are not policy actions.
    relative=robot.data.body_pos_w[0,ids[0]]-robot.data.root_pos_w[0]
    bottom=cylinder_bottom(robot.data.body_pos_w[:,ids],robot.data.body_quat_w[:,ids])[0,0]
    baseline=robot.data.root_state_w[:1].clone();baseline[:,7:]=0
    baseline[0,0]=box[0]-relative[0]-.18;baseline[0,1]=box[1]-relative[1]
    baseline[0,2]=robot.data.root_pos_w[0,2]-(bottom-env.scene.terrain.env_origins[0,2])
    clear=baseline.clone();clear[0,0]+=.18
    clear[0,2]+=box[2]-env.scene.terrain.env_origins[0,2]+.015
    env_ids=torch.tensor([0],device=args.device)
    robot.write_root_state_to_sim(clear,env_ids=env_ids);env.scene.write_data_to_sim()
    _,_,done,_=wrapped.step(zero)
    print('REFERENCE_NEAR_MISS '+json.dumps(dict(done=done.tolist())),flush=True)
    assert not bool(done[0])
    wrapped.reset();robot.write_root_state_to_sim(baseline,env_ids=env_ids);env.scene.write_data_to_sim()
    collision=False
    for i in range(100):
        _,reward,done,extras=wrapped.step(zero)
        assert not bool(done[1:].any()),'unrelated rows reset'
        if bool(done[0]):
            hit=env.termination_manager.get_term('obstacle_collision')
            print('REFERENCE_COLLISION '+json.dumps(dict(frame=i,done=done.tolist(),hit=hit.tolist(),reward=reward.tolist())),flush=True)
            assert bool(hit[0]) and float(reward[0])<-10
            collision=True;break
    assert collision and calls
    if 'additional_checks' in globals():
        additional_checks(env,wrapped)
    print('REFERENCE_LEARNING_NATIVE_COMPLETE',flush=True)
except BaseException:
    import traceback
    traceback.print_exc()
    raise
finally:
    faulthandler.cancel_dump_traceback_later()
    if env is not None:env.close()
    launcher.app.close()
