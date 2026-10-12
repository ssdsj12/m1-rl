"""Reward-only native assertions layered on the reference physics probe."""
from pathlib import Path
import runpy


def additional_checks(env,wrapped):
    import json
    import torch
    from ame_baseline.m1_stall_slip import StallWindow, bounded_slip, rolling_contact_speed
    from ame_baseline.m1_ame_rewards import m1_wheel_rolling_residual_l2
    dev=env.device;n=env.num_envs
    zero=torch.zeros(n,12,device=dev)
    names=env.reward_manager.active_terms
    stall_idx=names.index('stall');slip_idx=names.index('feet_slide')
    max_error=0.;terminal=0
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
    assert max_error<1e-6,max_error
    print('STALL_SLIP_NATIVE_COMPLETE '+json.dumps(dict(reward_rate_error=max_error,stages=[0,1,2,3,4],terminal=terminal)),flush=True)


runpy.run_path(str(Path(__file__).with_name('probe_m1_reference_learning.py')),
              init_globals={'additional_checks':additional_checks},run_name='__main__')
