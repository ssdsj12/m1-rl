"""Read-only checkpoint replay: actual contact/clearance and reward inputs.

Runs four diagnostic environments, not a smaller training run. No updates,
forced actions, servo changes, or training metric threshold modifications.
"""
import argparse
import json
from pathlib import Path
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--checkpoint', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--steps', type=int, default=1000)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
launcher = AppLauncher(args)
env = None
try:
    import torch
    from isaaclab.envs import ManagerBasedRLEnv
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_mixed_course import configure_flat_first_terrain
    from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
    from ame_baseline.actor_critic_ame import ActorCriticAME
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices
    from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES
    import ame_baseline.m1_required_crossing as reward_module
    import ame_baseline.m1_dynamic_crossing as encounter_module
    import ame_baseline.ame_env_wrapper as wrapper_module

    cfg = M1AmeCrossLargeComplexEnvCfg()
    configure_flat_first_terrain(cfg)
    cfg.scene.num_envs = 4
    cfg.sim.device = args.device
    cfg.seed = 42
    env = ManagerBasedRLEnv(cfg=cfg)
    wrapped = AmeRslRlEnvWrapper(env)
    checkpoint = torch.load(args.checkpoint, map_location='cpu', weights_only=False)
    stage = int(checkpoint['m1_learning_curriculum']['stage'])
    assert stage == 1, 'This diagnosis is scoped to the stalled 3cm stage'
    model = ActorCriticAME(checkpoint['ame_num_actor_obs'], checkpoint['ame_num_critic_obs'], 16).to(args.device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()  # Playback mode, frozen BN; not exact 2048-row rollout statistics.
    robot = env.scene['robot']
    sensor = env.scene['contact_forces']
    contact_ids = list(resolve_named_indices(tuple(sensor.body_names), M1_SUPPORT_BODY_NAMES))
    leg_ids = list(resolve_named_indices(tuple(robot.joint_names), M1_PLANNER_JOINT_NAMES))
    tracker = wrapped._m1_strict_crossing
    original_update = tracker.update
    capture = {}
    def serial(value):
        if torch.is_tensor(value):
            return value.detach().cpu().tolist()
        if isinstance(value, dict):
            return {k:serial(v) for k,v in value.items()}
        return value
    def measured_update(**kw):
        capture.clear()
        capture.update({k:serial(kw[k]) for k in (
            'wheel_pos_w','wheel_quat_w','wheel_bottom_z_w','wheel_grounded','support_safe',
            'touchdown_safe','collision','direction_w')})
        result = original_update(**kw)
        capture['result'] = serial(result)
        capture['target_wheel'] = serial(tracker.target_wheel)
        for name in ('slot','last_contact_bottom','prelift_bottom_high_water',
                     'prelift_high_water','early_lift','recovered'):
            capture[name] = serial(getattr(tracker, name))
        return result
    tracker.update = measured_update
    with Path(args.output).open('w') as output, torch.inference_mode():
        output.write(json.dumps({'kind':'metadata','checkpoint':args.checkpoint,'iter':checkpoint['iter'],
            'stage':stage,'joint_names':robot.joint_names,'leg_names':M1_PLANNER_JOINT_NAMES,
            'body_names':M1_SUPPORT_BODY_NAMES,'noise_std':serial(model.std),
            'dt':env.step_dt,'mode_note':'4env replay; frozen BN; no learning',
            'source_files':[m.__file__ for m in (reward_module, encounter_module, wrapper_module)]})+'\n')
        for mode in ('mean','sampled'):
            torch.manual_seed(42)
            env._m1_learning_gate.stage = stage
            wrapped.reset()
            obs, _ = wrapped.get_observations()
            course = wrapped._m1_current_course()
            output.write(json.dumps({'kind':'course','mode':mode,'origins':serial(env.scene.env_origins),
                'course':serial(course),'default_q':serial(robot.data.default_joint_pos),
                'default_root':serial(robot.data.default_root_state)})+'\n')
            for step in range(args.steps):
                before_root = robot.data.root_pos_w.clone()
                action = model.act_inference(obs) if mode == 'mean' else model.act(obs)
                obs, reward, done, extra = wrapped.step(action)
                q = robot.data.root_quat_w
                qw,qx,qy,qz = q.unbind(-1)
                roll = torch.atan2(2*(qw*qx+qy*qz),1-2*(qx.square()+qy.square()))
                pitch = torch.asin((2*(qw*qy-qz*qx)).clamp(-1,1))
                log = extra.get('log',{})
                record = {'kind':'frame','mode':mode,'step':step,'done':serial(done),
                    'pre_root':serial(before_root-env.scene.env_origins),
                    'root':serial(robot.data.root_pos_w-env.scene.env_origins),
                    'v_body':serial(robot.data.root_lin_vel_b),'roll_pitch':serial(torch.stack((roll,pitch),-1)),
                    'angular_w':serial(robot.data.root_ang_vel_w),'q':serial(robot.data.joint_pos),
                    'q_delta':serial(robot.data.joint_pos[:,leg_ids]-robot.data.default_joint_pos[:,leg_ids]),
                    'forces':serial(sensor.data.net_forces_w[:,contact_ids]),
                    'action':serial(action),'command':serial(env.command_manager.get_command('base_velocity')),
                    'reward':serial(reward),'reward_names':list(env.reward_manager.active_terms),
                    'reward_terms':serial(env.reward_manager._step_reward*env.step_dt),
                    'crossing':dict(capture),
                    'log':{k:serial(v) for k,v in log.items() if k.startswith('RequiredCrossing/')}}
                output.write(json.dumps(record)+'\n')
                if step % 100 == 0:
                    output.flush()
                    print('M1_CONTACT_REPLAY',mode,step,flush=True)
            output.flush()
    print('M1_CONTACT_REPLAY_COMPLETE',args.output,flush=True)
finally:
    if env is not None:
        env.close()
    launcher.app.close()
