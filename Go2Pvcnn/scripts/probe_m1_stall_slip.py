"""Reward-only native assertions layered on the reference physics probe."""
from pathlib import Path
import runpy


def additional_checks(env,wrapped):
    import json
    import torch
    from ame_baseline.m1_stall_slip import StallWindow, bounded_slip, rolling_contact_speed, validate_native_evidence
    from ame_baseline.m1_ame_rewards import m1_wheel_rolling_residual_l2
    dev=env.device;n=env.num_envs
    zero=torch.zeros(n,12,device=dev)
    names=env.reward_manager.active_terms
    stall_idx=names.index('stall');slip_idx=names.index('feet_slide')
    max_error=0.;terminal=0
    evidence={}
    for level in (0,1,2,3,4):
        env._m1_learning_gate.stage=level;wrapped.reset()
        for _ in range(12):
            _,reward,done,_=wrapped.step(zero)
            terminal+=int(done.sum())
            ss=env._m1_stall_snapshot;sl=env._m1_slip_snapshot
            assert torch.isfinite(reward).all()
            assert bool((ss['rate']==0).all()),'reset needs fresh 2-second window'
            error=(env.reward_manager._step_reward[:,stall_idx]+ss['rate']).abs().max()
            max_error=max(max_error,float(error))
            if level in (1,2,3):
                error=(env.reward_manager._step_reward[:,slip_idx]+sl['rate']).abs().max()
                max_error=max(max_error,float(error))
            else:
                assert not bool(env._m1_stall_slip_stage.any())
            if done.any():assert not bool(wrapped._m1_stall_window.ready[done].any())
        if level in (0,4):
            current=m1_wheel_rolling_residual_l2(env)
            env.cfg.m1_flat_first=False
            legacy=m1_wheel_rolling_residual_l2(env)
            env.cfg.m1_flat_first=True
            torch.testing.assert_close(current,legacy,rtol=0,atol=0)
    # Hold root XY in the empty spawn area only in this diagnostic fixture.
    # Real physics, reward manager and wrapper run for a full matured window.
    env._m1_learning_gate.stage=1;wrapped.reset()
    for _ in range(10):wrapped.step(zero)
    robot=env.scene['robot'];xy=robot.data.root_pos_w[:,:2].clone()
    nonzero=0
    for _ in range(125):
        state=robot.data.root_state_w.clone();state[:,:2]=xy;state[:,7:9]=0
        robot.write_root_state_to_sim(state);env.scene.write_data_to_sim()
        _,_,done,_=wrapped.step(zero)
        assert not done.any(),'fixture left safe spawn area'
        rate=env._m1_stall_snapshot['rate']
        nonzero+=int((rate>0).sum())
        max_error=max(max_error,float((env.reward_manager._step_reward[:,stall_idx]+rate).abs().max()))
        # RewardManager stores rates; returned manager contribution integrates once.
        assert env.reward_manager.get_term_cfg('stall').weight==1.
        assert float((rate*env.step_dt).max())<=.5*env.step_dt+1e-7
    evidence['nonzero_stall_steps']=nonzero
    # A current-airborne wheel with historical force must not keep slip charged.
    sensor=env.scene['contact_forces']
    force=sensor.data.net_forces_w;history=sensor.data.net_forces_w_history
    old_force=force.clone();old_history=history.clone()
    force.zero_();history[...,2]=20.
    evidence['history_only_zero']=bool((m1_wheel_rolling_residual_l2(env)==0).all())
    force.copy_(old_force);history.copy_(old_history)
    # Force one timeout while the curriculum changes only that reset row to mixed.
    # Capture contact input at RewardManager time, before Isaac auto-reset.
    cfg=env.reward_manager.get_term_cfg('feet_slide');original=cfg.func;capture={}
    def measured_slip(e,**kwargs):
        from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
        from extension.parallelism.rl_adapter import resolve_named_indices
        bi=list(resolve_named_indices(robot.body_names,M1_SUPPORT_BODY_NAMES))
        si=list(resolve_named_indices(sensor.body_names,M1_SUPPORT_BODY_NAMES))
        speed=rolling_contact_speed(robot.data.body_link_lin_vel_w[:,bi],robot.data.body_ang_vel_w[:,bi],robot.data.body_quat_w[:,bi],.0959)
        capture['rate']=bounded_slip(speed,sensor.data.net_forces_w[:,si])['rate'].clone()
        capture['stage']=e._m1_stall_slip_stage.clone()
        return original(e,**kwargs)
    cfg.func=measured_slip;env.reward_manager.set_term_cfg('feet_slide',cfg)
    env._m1_learning_gate.stage=4
    env.episode_length_buf[0]=env.max_episode_length-1
    _,_,done,_=wrapped.step(zero)
    assert bool(done[0]) and not bool(done[1:].any())
    terminal+=int(done.sum())
    evidence['terminal_old_stage']=bool(capture['stage'].all()) and int(env.scene.terrain.terrain_levels[0])>=4
    evidence['terminal_old_force']=bool(torch.allclose(env._m1_slip_snapshot['rate'],capture['rate'],rtol=0,atol=1e-7))
    assert not bool(wrapped._m1_stall_window.ready[0])
    _,_,_,_=wrapped.step(zero)
    evidence['next_step_new_stage']=not bool(env._m1_stall_slip_stage[0]) and float(env._m1_stall_snapshot['rate'][0])==0
    cfg.func=original;env.reward_manager.set_term_cfg('feet_slide',cfg)
    # Synthetic diagnostic trajectories compare CPU/GPU kernels. No policy teacher.
    cpu=StallWindow(n,'cpu',env.step_dt);gpu=StallWindow(n,dev,env.step_dt)
    for i in range(180):
        x=torch.arange(n)*(.3*i*env.step_dt)
        identity=torch.ones(n,2);active=torch.ones(n,dtype=torch.bool)
        a=cpu.update(x,identity,active,~active)
        b=gpu.update(x.to(dev),identity.to(dev),active.to(dev),(~active).to(dev))
        torch.testing.assert_close(a['rate'],b['rate'].cpu(),rtol=0,atol=1e-6)
    assert float(b['rate'][0])==.5 and float(b['rate'][1])==0
    v=torch.zeros(n,4,3,device=dev);w=v.clone();f=v.clone()
    v[...,0]=.3;w[...,1]=.3/.0959;f[...,2]=20
    q=torch.tensor([1.,0,0,0],device=dev).expand(n,4,4)
    assert bounded_slip(rolling_contact_speed(v,w,q,.0959),f)['rate'].max()==0
    v.zero_()
    assert torch.allclose(bounded_slip(rolling_contact_speed(v,w,q,.0959),f)['rate'],torch.full((n,),.25,device=dev))
    f.zero_();assert bounded_slip(rolling_contact_speed(v,w,q,.0959),f)['rate'].sum()==0
    evidence['rate_error']=max_error
    validate_native_evidence(evidence)
    print('STALL_SLIP_NATIVE_COMPLETE '+json.dumps(dict(evidence=evidence,stages=[0,1,2,3,4],terminal=terminal)),flush=True)


runpy.run_path(str(Path(__file__).with_name('probe_m1_reference_learning.py')),
              init_globals={'additional_checks':additional_checks},run_name='__main__')
