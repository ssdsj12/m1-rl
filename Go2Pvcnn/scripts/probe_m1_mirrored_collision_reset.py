"""Bounded native verification; no learning and no scripted lift policy."""
import argparse
import json
import runpy
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
    from isaaclab.utils.math import euler_xyz_from_quat
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_mixed_course import configure_flat_first_terrain
    from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS, M1_TRAINING_ROOT_Z_M
    from ame_baseline.m1_ame_terminations import obstacle_collision

    audit = runpy.run_path(str(Path(__file__).with_name('audit_m1_standing_height.py')))
    mesh = audit['current']
    assert abs(mesh['height'] - .585) < .001 and abs(mesh['min_z']) < .001, mesh
    cfg = M1AmeCrossLargeComplexEnvCfg()
    configure_flat_first_terrain(cfg)
    cfg.scene.num_envs = 4
    cfg.sim.device = args.device
    cfg.seed = 7
    cfg.events.reset_robot_joints.params.update(position_range=(1.,1.), velocity_range=(0.,0.))
    cfg.events.reset_base.params['velocity_range'] = {k:(0.,0.) for k in ('x','y','z','roll','pitch','yaw')}
    env = ManagerBasedRLEnv(cfg=cfg)
    wrapped = AmeRslRlEnvWrapper(env)
    assert env.cfg.m1_training_contract['required_top_margin_m'] == 0.
    # Observe the real wrapper's argument on GPU, not just its source text.
    original_update = wrapped._m1_strict_crossing.update
    margin_calls = []
    def checked_update(**kwargs):
        margin_calls.append(kwargs['required_clearance'])
        assert kwargs['required_clearance'] == 0.
        return original_update(**kwargs)
    wrapped._m1_strict_crossing.update = checked_update
    assert wrapped.num_actions == 12 and not env.scene['robot'].is_fixed_base
    assert not getattr(env, '_trajectory_manager', None)
    robot = env.scene['robot']
    zero = torch.zeros(4,12,device=args.device)
    initial = robot.data.root_pos_w.clone()
    resets = 0
    max_tilt = 0.
    for i in range(150):
        _, reward, done, extras = wrapped.step(zero)
        resets += int(done.sum())
        assert torch.isfinite(reward).all() and torch.isfinite(robot.data.root_state_w).all()
        r,p,_ = euler_xyz_from_quat(robot.data.root_quat_w)
        tilt = torch.atan2(torch.sin(torch.stack((r,p))),torch.cos(torch.stack((r,p)))).abs()
        max_tilt = max(max_tilt,float(tilt.max()))
    advance = (robot.data.root_pos_w[:,0]-initial[:,0]).tolist()
    print('M1_MIRROR_FLAT '+json.dumps(dict(resets=resets,max_tilt=max_tilt,advance=advance)),flush=True)
    assert resets == 0 and max_tilt < .15 and min(advance) > .3

    env._m1_learning_gate.stage = 1
    wrapped.reset()
    course = wrapped._m1_current_course()
    valid = course['valid'][0]
    box = course['centers_top'][0][valid][0]
    # Same zero leg actions throughout: drive FL toward the first actual box.
    root = robot.data.default_root_state[:1].clone()
    root[0,:3] = box
    root[0,0] -= .3295 + .18
    root[0,1] -= .2074
    root[0,2] = env.scene.terrain.env_origins[0,2] + M1_TRAINING_ROOT_Z_M
    ids = torch.tensor([0],device=args.device)
    # Separated by 1.5cm: no collision, no extra 3cm rule (not a full crossing).
    clear_root = root.clone()
    clear_root[0,0] += .18
    clear_root[0,2] += (box[2]-env.scene.terrain.env_origins[0,2]) + .015
    robot.write_root_state_to_sim(clear_root,env_ids=ids)
    env.scene.write_data_to_sim()
    _, _, clear_done, _ = wrapped.step(zero)
    clear_hit = env.termination_manager.get_term('obstacle_collision').clone()
    print('M1_MIRROR_CLEAR '+json.dumps(dict(done=clear_done.tolist(),hit=clear_hit.tolist())),flush=True)
    assert not bool(clear_hit[0]) and not bool(clear_done[0])
    wrapped.reset()
    robot.write_root_state_to_sim(root,env_ids=ids)
    env.scene.write_data_to_sim()
    collision = False
    other_resets = 0
    for i in range(100):
        _, reward, done, extras = wrapped.step(zero)
        other_resets += int(done[1:].sum())
        hit = env.termination_manager.get_term('obstacle_collision').clone()
        if bool(done[0]):
            result=dict(frame=i,done=done.tolist(),hit=hit.tolist(),reward=reward.tolist(),
                        reset_local_root=(robot.data.root_pos_w-env.scene.terrain.env_origins).tolist())
            print('M1_MIRROR_CONTACT '+json.dumps(result),flush=True)
            assert bool(hit[0]) and float(reward[0]) < -10., result
            collision = True
            break
    assert collision and other_resets == 0, (collision,other_resets)
    assert not bool(obstacle_collision(env)[0]), 'reset pose retains collision'
    assert margin_calls and set(margin_calls) == {0.}
    print('M1_MIRROR_NATIVE_COMPLETE',flush=True)
finally:
    if env is not None:
        env.close()
    launcher.app.close()
