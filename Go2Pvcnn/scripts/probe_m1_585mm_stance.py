"""Bounded native stance hold. No teacher, lift controller or training claims."""
import argparse
import json
import runpy
import traceback
from pathlib import Path
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
launcher = AppLauncher(args)
env = None
try:
    import torch
    from isaaclab.envs import ManagerBasedRLEnv
    from isaaclab.utils.math import quat_apply, euler_xyz_from_quat
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_mixed_course import configure_mixed_terrain
    from extension.semantic_course import terrain_column_names_from_generator
    cfg = M1AmeCrossLargeComplexEnvCfg()
    configure_mixed_terrain(cfg)
    cfg.scene.num_envs = 4
    cfg.sim.device = args.device
    cfg.seed = 7
    cfg.curriculum.terrain_levels = None
    cfg.events.reset_robot_joints.params['velocity_range'] = (0., 0.)
    cfg.events.reset_base.params['pose_range'] = {'x': (0., 0.), 'y': (0., 0.), 'yaw': (0., 0.)}
    cfg.events.reset_base.params['velocity_range'] = {k: (0., 0.) for k in ('x','y','z','roll','pitch','yaw')}
    env = ManagerBasedRLEnv(cfg=cfg)
    terrain = env.scene.terrain
    names = terrain_column_names_from_generator(cfg.scene.terrain.terrain_generator)
    terrain.terrain_levels.zero_()
    terrain.terrain_types.fill_(names.index('flat'))
    terrain.env_origins.copy_(terrain.terrain_origins[terrain.terrain_levels, terrain.terrain_types])
    env.reset()
    robot = env.scene['robot']
    assert not robot.is_fixed_base
    assert not getattr(env, '_mpc_trajectory_manager', None)
    zeros = torch.zeros((4,16), device=args.device)
    resets = 0
    max_tilt = 0.
    max_speed = 0.
    steps = round(5. / env.step_dt)
    for i in range(steps):
        _, _, terminated, truncated, _ = env.step(zeros)
        resets += int((terminated | truncated).sum())
        assert torch.isfinite(robot.data.root_state_w).all()
        roll, pitch, _ = euler_xyz_from_quat(robot.data.root_quat_w)
        tilt = torch.atan2(torch.sin(torch.stack((roll,pitch))), torch.cos(torch.stack((roll,pitch)))).abs()
        max_tilt = max(max_tilt, float(tilt.max()))
        max_speed = max(max_speed, float(robot.data.root_lin_vel_w.norm(dim=-1).max()))
        if i % 50 == 0:
            print('STANCE_PROGRESS '+str(i), flush=True)
    # Source mesh local vertices transformed by actual PhysX body-link poses;
    # do not read stale USD transforms when Fabric drives physics.
    audit = runpy.run_path(str(Path(__file__).with_name('audit_m1_standing_height.py')))
    low = torch.full((4,), float('inf'), device=args.device)
    high = -low.clone()
    wheel_low = {}
    for body, path, points in audit['meshes']:
        idx = robot.body_names.index(body)
        pts = torch.as_tensor(points, dtype=torch.float32, device=args.device)
        q = robot.data.body_link_quat_w[:,idx,None,:].expand(-1,len(pts),-1)
        world = quat_apply(q.reshape(-1,4), pts[None].expand(4,-1,-1).reshape(-1,3)).reshape(4,-1,3)
        world += robot.data.body_link_pos_w[:,idx,None,:]
        z = world[:,:,2] - terrain.env_origins[:,2,None]
        low = torch.minimum(low,z.min(-1).values)
        high = torch.maximum(high,z.max(-1).values)
        if body.endswith('FOOT_LINK') and '/collisions/' in path:
            wheel_low[body] = z.min(-1).values.tolist()
    result = dict(scope='five_second_neutral_hold_not_lift_or_crossing', seconds=steps*env.step_dt,
        resets=resets, max_tilt_rad=max_tilt, max_root_speed=max_speed,
        final_root_z=(robot.data.root_pos_w[:,2]-terrain.env_origins[:,2]).tolist(),
        final_mesh_top=high.tolist(), final_mesh_bottom=low.tolist(), wheel_bottoms=wheel_low)
    print('M1_STANCE_RESULT '+json.dumps(result), flush=True)
    assert resets == 0, result
    assert max_tilt < .15, result
    assert min(high.tolist()) > .50, result
except BaseException:
    traceback.print_exc()
    raise
finally:
    if env is not None:
        env.close()
    launcher.app.close()
