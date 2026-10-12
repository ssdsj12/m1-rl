"""Isolated fixed-ABAD wiring/clock evidence, not a policy teacher or learning proof."""
import math


def require_finite(*tensors):
    import torch
    if any(not bool(torch.isfinite(value).all()) for value in tensors):
        raise ValueError('Nonfinite raw native measurement')


def validate_evidence(e):
    expected=dict(complete=True,stages=[0,1,2,3,4],policy_dim=8,history_dim=16,
                  policy_state_dim=85,critic_state_dim=88,rewards_finite=True,raw_rewards_finite=True,
                  terminal_row_reset=True,flat_resets=0)
    if any(e.get(k)!=v for k,v in expected.items()):
        raise ValueError('Incomplete native fixed-ABAD evidence')
    for name in ('abad_target_error','wheel_target_error','elapsed_100','flat_advance_min','flat_max_tilt'):
        if not math.isfinite(e[name]):raise ValueError('Nonfinite native measurement')
    if (e['abad_target_error']>1e-7 or e['wheel_target_error']>1e-6 or
        abs(e['elapsed_100']-2.)>1e-5 or e['apply_calls']<600 or
        e['flat_advance_min']<.3 or e['flat_max_tilt']>.15):
        raise ValueError('Native targets/clock/flat-reference check failed')


def main():
    import argparse
    import json
    from pathlib import Path
    from isaaclab.app import AppLauncher
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    AppLauncher.add_app_launcher_args(parser)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Evidence output must be new')
    launcher=AppLauncher(args);env=None
    try:
        import torch
        from isaaclab.envs import ManagerBasedRLEnv
        from isaaclab.utils.math import euler_xyz_from_quat
        from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
        from ame_baseline.m1_mixed_course import configure_flat_first_terrain
        from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
        from ame_baseline.m1_ame_contract import m1_last_action,m1_last_leg_action
        from ame_baseline.m1_fixed_abad import M1_ABAD_JOINT_NAMES,fixed_abad_contract
        from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
        from extension.parallelism.m1_kinematics import M1_WHEEL_JOINT_NAMES,M1_ASSET_JOINT_NAMES
        from extension.parallelism.rl_adapter import resolve_named_indices
        cfg=M1AmeCrossLargeComplexEnvCfg();configure_flat_first_terrain(cfg)
        assert cfg.m1_fixed_abad and cfg.action_dim==8
        cfg.scene.num_envs=4;cfg.sim.device=args.device;cfg.seed=7
        cfg.commands.base_velocity.debug_vis=False
        cfg.events.reset_base.params['velocity_range']={k:(0.,0.) for k in ('x','y','z','roll','pitch','yaw')}
        env=ManagerBasedRLEnv(cfg=cfg);wrapped=AmeRslRlEnvWrapper(env)
        robot=env.scene['robot'];term=env.action_manager.get_term('JointPositionAction')
        abad=list(resolve_named_indices(robot.joint_names,M1_ABAD_JOINT_NAMES))
        wheels=list(resolve_named_indices(robot.joint_names,M1_WHEEL_JOINT_NAMES))
        order=list(resolve_named_indices(robot.joint_names,M1_ASSET_JOINT_NAMES))
        sensor=env.scene['contact_forces'];feet=list(resolve_named_indices(sensor.body_names,M1_SUPPORT_BODY_NAMES))
        e=dict(complete=False,stages=[],policy_dim=wrapped.num_actions,history_dim=16,
            policy_state_dim=85,critic_state_dim=88,rewards_finite=True,raw_rewards_finite=True,abad_target_error=0.,
            wheel_target_error=0.,apply_calls=0,terminal_row_reset=False,flat_resets=0,
            flat_max_tilt=0.,contract=fixed_abad_contract(.3))
        apply=term.apply_actions
        def measured_apply():
            apply();e['apply_calls']+=1
            require_finite(robot.data.joint_pos_target[:,abad],robot.data.joint_vel_target[:,wheels])
            e['abad_target_error']=max(e['abad_target_error'],float(robot.data.joint_pos_target[:,abad].abs().max()))
            e['wheel_target_error']=max(e['wheel_target_error'],float((robot.data.joint_vel_target[:,wheels]-.3/.0959).abs().max()))
        term.apply_actions=measured_apply
        sanitize=wrapped._sanitize_rewards
        def measured_sanitize(raw):
            require_finite(raw)
            return sanitize(raw)
        wrapped._sanitize_rewards=measured_sanitize
        def frame(stream,phase,tick,action):
            obs,reward,done,extras=wrapped.step(action)
            assert obs.shape==(4,1621) and extras['observations']['critic'].shape==(4,1624)
            assert m1_last_leg_action(env).shape==(4,12) and m1_last_action(env).shape==(4,16)
            require_finite(obs,extras['observations']['critic'],reward,env.reward_manager._step_reward,
                robot.data.joint_pos_target[:,order],robot.data.joint_pos[:,order],
                robot.data.root_state_w,sensor.data.net_forces_w[:,feet])
            assert not bool(env.termination_manager.get_term('nonfinite_robot_state').any())
            e['rewards_finite'] &= bool(torch.isfinite(reward).all() and torch.isfinite(obs).all())
            r,p,y=euler_xyz_from_quat(robot.data.root_quat_w)
            tilt=torch.atan2(torch.sin(torch.stack((r,p))),torch.cos(torch.stack((r,p)))).abs()
            stream.write(json.dumps(dict(phase=phase,tick=tick,sim_time=env.sim.current_time,
                action=action.tolist(),targets=robot.data.joint_pos_target[:,order].tolist(),
                actual_joint=robot.data.joint_pos[:,order].tolist(),wheel_velocity=robot.data.joint_vel[:,wheels].tolist(),
                root=robot.data.root_pos_w.tolist(),yaw=y.tolist(),Fz=sensor.data.net_forces_w[:,feet,2].tolist(),
                done=done.tolist(),reward=reward.tolist()))+'\n')
            return done,tilt
        zero=torch.zeros(4,8,device=env.device)
        with args.output.open('x') as out,torch.inference_mode():
            wrapped.reset();start=robot.data.root_pos_w.clone();t0=env.sim.current_time
            for i in range(100):
                done,tilt=frame(out,'flat',i,zero)
                e['flat_resets']+=int(done.sum());e['flat_max_tilt']=max(e['flat_max_tilt'],float(tilt.max()))
            e['elapsed_100']=env.sim.current_time-t0
            e['flat_advance']=(robot.data.root_pos_w[:,0]-start[:,0]).tolist()
            e['flat_advance_min']=min(e['flat_advance'])
            e['flat_abad_actual_max']=float(robot.data.joint_pos[:,abad].abs().max())
            for level in (0,1,2,3,4):
                env._m1_learning_gate.stage=level;wrapped.reset();e['stages'].append(level)
                for i in range(30):
                    action=torch.rand(4,8,device=env.device)*.1-.05
                    if level==0 and i==5:env.episode_length_buf[0]=env.max_episode_length-1
                    done,_=frame(out,level,i,action)
                    if level==0 and i==5:
                        assert bool(done[0]) and not bool(done[1:].any())
                        assert bool((env.action_manager.action[0]==0).all())
                        torch.testing.assert_close(env.action_manager.action[1:],action[1:])
                        assert bool((term.raw_actions[0]==0).all())
                        e['terminal_row_reset']=True
            e['complete']=True;validate_evidence(e)
            out.write(json.dumps(dict(COMPLETE=e))+'\n');out.flush()
            print('FIXED_ABAD_NATIVE_COMPLETE '+json.dumps(e),flush=True)
    finally:
        if env is not None:env.close()
        launcher.app.close()


if __name__=='__main__':main()
