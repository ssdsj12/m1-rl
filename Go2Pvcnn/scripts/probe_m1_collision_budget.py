"""Bounded native collision-budget gate; controlled placement is not a policy."""
def check_collision_final_reward(raw, final, parts, signal):
    import torch
    rows=signal>0
    positive=sum(value.clamp_min(0.) for value in parts.values())
    torch.testing.assert_close(final[rows],(raw-positive)[rows],rtol=1e-5,atol=2e-6)


def main():
    import argparse, json
    from pathlib import Path
    from isaaclab.app import AppLauncher
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    AppLauncher.add_app_launcher_args(parser)
    args=parser.parse_args()
    if args.output.exists(): raise ValueError('Evidence path already exists')
    app=AppLauncher(args);env=None
    try:
        import torch
        from isaaclab.envs import ManagerBasedRLEnv
        from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
        from ame_baseline.m1_mixed_course import configure_flat_first_terrain
        from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
        from ame_baseline.m1_collision_budget import current_collision_snapshot
        from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
        from extension.parallelism.rl_adapter import resolve_named_indices
        cfg=M1AmeCrossLargeComplexEnvCfg();configure_flat_first_terrain(cfg)
        cfg.scene.num_envs=4;cfg.sim.device=args.device;cfg.seed=42
        cfg.commands.base_velocity.debug_vis=False
        env=ManagerBasedRLEnv(cfg=cfg);wrapper=AmeRslRlEnvWrapper(env)
        assert wrapper.num_actions==8
        assert 'obstacle_collision' not in env.termination_manager.active_terms
        assert 'collision_budget' in env.termination_manager.active_terms
        assert 'parallelism_geometry_collision' not in env.reward_manager.active_terms
        assert 'non_support_obstacle_contact' not in env.reward_manager.active_terms
        robot=env.scene['robot'];ids=torch.tensor([0],device=env.device)
        wheel=resolve_named_indices(robot.body_names,M1_SUPPORT_BODY_NAMES)[0]
        zero=torch.zeros(4,8,device=env.device)
        capture={};reward_compute=env.reward_manager.compute
        strict_update=wrapper._m1_strict_crossing.update
        strict_calls=[]
        def checked_strict(**kwargs):
            raw=current_collision_snapshot(env)['signal']>0
            assert torch.equal(kwargs['collision'],raw)
            strict_calls.append(int(raw.sum()))
            return strict_update(**kwargs)
        wrapper._m1_strict_crossing.update=checked_strict
        def measured_reward(dt):
            reward=reward_compute(dt)
            capture['raw']=reward.clone()
            capture['parts']={name:env.reward_manager._step_reward[:,i].clone()*dt
                for i,name in enumerate(env.reward_manager.active_terms)}
            capture['root']=robot.data.root_state_w.clone()
            assert torch.isfinite(reward).all()
            return reward
        env.reward_manager.compute=measured_reward
        evidence=dict(flat_resets=0,positive_charge_steps=0,budget_resets=0,
                      other_rows_reset=0,no_immediate_reset=False,post_reset_zero=False,
                      ordinary_failure_penalty=False,timeout_no_failure=False,stages=[])
        with args.output.open('x') as out,torch.inference_mode():
            def step(phase,tick):
                obs,reward,done,extra=wrapper.step(zero)
                snap=current_collision_snapshot(env)
                assert torch.isfinite(obs).all() and torch.isfinite(reward).all()
                parts=capture['parts']
                torch.testing.assert_close(parts['collision_budget_cost'],-snap['cost'],rtol=1e-5,atol=1e-7)
                torch.testing.assert_close(sum(parts.values()),capture['raw'],rtol=1e-5,atol=1e-6)
                assert ((parts['failure_termination']==0)|~snap['exhausted']).all()
                check_collision_final_reward(capture['raw'],reward,parts,snap['signal'])
                row=dict(phase=phase,tick=tick,cost=snap['cost'].tolist(),spent=snap['total'].tolist(),
                    exhausted=snap['exhausted'].tolist(),done=done.tolist(),reward=reward.tolist(),
                    failure=parts['failure_termination'].tolist(),raw=capture['raw'].tolist(),
                    terminations={name:env.termination_manager.get_term(name).tolist() for name in env.termination_manager.active_terms})
                out.write(json.dumps(row)+'\n');out.flush()
                return done,snap,parts
            wrapper.reset();start=robot.data.root_pos_w.clone()
            for i in range(100):
                done,snap,_=step('flat',i)
                evidence['flat_resets']+=int(done.sum());assert snap['cost'].sum()==0
            evidence['flat_advance']=(robot.data.root_pos_w[:,0]-start[:,0]).tolist()
            assert evidence['flat_resets']==0 and min(evidence['flat_advance'])>.3
            for stage in [0,1,2,3,4]:
                env._m1_learning_gate.stage=stage;wrapper.reset();evidence['stages'].append(stage)
                for i in range(3): step('stage_'+str(stage),i)
            env._m1_learning_gate.stage=1;wrapper.reset()
            # Place one wheel into a real block repeatedly to exercise the full
            # budget without asking a learned policy to hold the fixture still.
            step('prepare',0)
            course=wrapper._m1_current_course();box=course['centers_top'][0][course['valid'][0]][0].clone()
            root=robot.data.root_state_w[:1].clone()
            target=box.clone();target[2]+=.0959-.025
            root[0,:3]+=target-robot.data.body_pos_w[0,wheel]
            root[:,7:]=0
            pose=robot.data.joint_pos[:1].clone();vel=torch.zeros_like(pose)
            # Nonzero sentinel verifies manager row-reset locality; it is not
            # counted as physical collision evidence or collected reward.
            env._m1_collision_budget.total[1]=.7
            integral=0.
            for i in range(260):
                robot.write_root_state_to_sim(root,env_ids=ids)
                robot.write_joint_state_to_sim(pose,vel,env_ids=ids)
                # Keep unaffected rows in their safe spawn region with ordinary
                # reset only before fixture start, not during the measured step.
                env.scene.write_data_to_sim()
                done,snap,parts=step('contact',i)
                integral+=float(snap['cost'][0]);evidence['positive_charge_steps']+=int(snap['cost'][0]>0)
                evidence['other_rows_reset']+=int(done[1:].sum())
                if snap['cost'][0]>0 and snap['total'][0]<19.99:
                    assert not done[0], 'another physical failure invalidates this fixture'
                    evidence['no_immediate_reset']=True
                if done[0]:
                    assert snap['exhausted'][0], 'fixture ended before budget'
                    assert parts['failure_termination'][0]==0
                    assert abs(integral-20.)<2e-5
                    assert env._m1_collision_budget.total[0]==0
                    # Other rows may encounter obstacles while rolling. Compare
                    # their old-episode snapshot, not only the starting sentinel.
                    torch.testing.assert_close(env._m1_collision_budget.total[1:].float(),snap['total'][1:])
                    assert env._m1_collision_budget.total[1]>=.7
                    evidence['budget_resets']+=1;evidence['integral']=integral
                    break
            assert evidence['budget_resets']==1 and evidence['positive_charge_steps']>=199
            # New born row must not inherit budget; other rows remain alive.
            done,snap,_=step('after_budget_reset',0)
            evidence['post_reset_zero']=bool(snap['total'][0]==0 and not done[0])
            assert evidence['post_reset_zero'] and evidence['other_rows_reset']==0
            env._m1_learning_gate.stage=0;wrapper.reset()
            env.episode_length_buf[0]=env.max_episode_length-1
            done,_,parts=step('timeout',0)
            assert done[0] and not done[1:].any() and parts['failure_termination'][0]==0
            evidence['timeout_no_failure']=True
            wrapper.reset()
            # Existing bad_orientation uses abs(projected_gravity.z), so test
            # its actual side-tilt failure, not a180deg inversion blind spot.
            bad=robot.data.root_state_w[:1].clone();bad[:,3:7]=bad.new_tensor([.70710678,.70710678,0.,0.])
            robot.write_root_state_to_sim(bad,env_ids=ids);env.scene.write_data_to_sim()
            for i in range(30):
                done,_,parts=step('physical_failure',i)
                if done[0]: break
            assert done[0] and abs(float(parts['failure_termination'][0])+20.)<1e-5
            evidence['ordinary_failure_penalty']=True
            evidence['strict_collision_calls']=sum(strict_calls)
            assert evidence['strict_collision_calls']>0
            evidence['complete']=True
            out.write(json.dumps(dict(COMPLETE=evidence))+'\n');out.flush()
            print('COLLISION_BUDGET_NATIVE_COMPLETE '+json.dumps(evidence),flush=True)
    finally:
        if env is not None: env.close()
        app.app.close()


if __name__=='__main__': main()
