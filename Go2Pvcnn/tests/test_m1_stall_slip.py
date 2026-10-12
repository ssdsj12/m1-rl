import importlib
import importlib.util
import math
from types import SimpleNamespace

import pytest
import torch


def module():
    assert importlib.util.find_spec('ame_baseline.m1_stall_slip') is not None, 'stall/slip module absent'
    return importlib.import_module('ame_baseline.m1_stall_slip')


def run_path(xs, dt=.02):
    m=module(); t=m.StallWindow(1,'cpu',dt)
    outputs=[]
    for x in xs:
        outputs.append(t.update(torch.tensor([x]),torch.tensor([[1,7]]),torch.tensor([True]),torch.tensor([False])))
    return t,outputs


def test_stall_warmup_and_bounded_rate():
    _,outs=run_path([0.]*111)
    assert all(o['rate'].item()==0 for o in outs[:100])
    assert outs[100]['rate'].item()==pytest.approx(.5)
    assert outs[-1]['progress'].item()==0


@pytest.mark.parametrize('speed,expected',[(.30,0),(.025,0),(.0125,.25),(0.,.5),(-.3,.5)])
def test_forward_window_threshold(speed,expected):
    _,outs=run_path([i*.02*speed for i in range(160)])
    assert outs[-1]['rate'].item()==pytest.approx(expected,abs=1e-5)


def test_retreat_and_retrace_do_not_reset_grace():
    _,outs=run_path([.3*i*.02 for i in range(101)]+[0.]*110+[.6]*10)
    assert outs[-1]['rate'].item()==pytest.approx(.5)


@pytest.mark.parametrize('dt',[.01,.03,.07])
def test_fractional_time_interpolation(dt):
    _,outs=run_path([.0125*i*dt for i in range(math.ceil(4/dt))],dt)
    assert outs[-1]['rate'].item()==pytest.approx(.25,abs=2e-5)


def test_rows_reset_identity_completion_and_nonfinite():
    m=module();t=m.StallWindow(3,'cpu',.02)
    x=torch.zeros(3);ids=torch.ones(3,2);active=torch.ones(3,dtype=torch.bool);complete=~active
    for _ in range(102):o=t.update(x,ids,active,complete)
    assert torch.allclose(o['rate'],torch.full((3,),.5))
    t.reset(torch.tensor([True,False,False])); ids[1,1]=2;complete[2]=True
    assert t.update(x,ids,active,complete)['rate'].sum()==0
    x[0]=float('nan')
    o=t.update(x,ids,active,complete)
    assert o['invalid'][0] and torch.isfinite(o['rate']).all()
    x[0]=0
    assert t.update(x,ids,active,complete)['rate'][0]==0


def test_disabled_stages_never_accumulate_window():
    m=module();t=m.StallWindow(1,'cpu',.02)
    for _ in range(200):o=t.update(torch.zeros(1),torch.ones(1,1),torch.tensor([False]),torch.tensor([False]))
    assert o['rate'].item()==0
    assert not t.update(torch.zeros(1),torch.ones(1,1),torch.tensor([True]),torch.tensor([False]))['warm'].item()


def test_slip_true_rolling_airborne_reverse_and_sideways():
    m=module();v=torch.zeros(4,4,3);w=v.clone();q=torch.tensor([1.,0,0,0]).expand(4,4,4)
    v[...,0]=.30;w[...,1]=.30/.0959
    w[1]=0;w[2]*=-1;v[3,:,1]=.3
    speed=m.rolling_contact_speed(v,w,q,.0959)
    f=torch.zeros_like(v);f[...,2]=20
    out=m.bounded_slip(speed,f)
    torch.testing.assert_close(out['rate'],torch.tensor([0.,.25,.25,.25]),atol=1e-6,rtol=0)
    f.zero_();assert m.bounded_slip(speed,f)['rate'].sum()==0


@pytest.mark.parametrize('force',[0.,1.,9.99,10.])
def test_only_current_upward_load_counts(force):
    m=module();f=torch.zeros(1,4,3);f[...,2]=force;f[...,0]=100
    assert m.bounded_slip(torch.ones(1,4),f)['rate'].item()==0


def test_slip_deadband_cap_invalid_and_wheel_count():
    m=module();f=torch.zeros(2,4,3);f[...,2]=20
    s=torch.tensor([[.03,.02,0.,.01],[float('nan'),.165,0.,0.]])
    out=m.bounded_slip(s,f)
    assert out['rate'][0]==0 and out['invalid'][1]
    assert out['rate'][1].item()==pytest.approx(.0625)
    assert m.bounded_slip(torch.ones(2,4)*100,f)['rate'].max()<=.25


def test_incremental_cost_bound_and_discounted_collision_comparison():
    m=module();dt=.02;gamma=.99
    _,outs=run_path([0.]*1000)
    rates=torch.tensor([o['rate'].item()+.25 for o in outs])
    assert (rates*dt).sum()<=14.00001
    # Incremental two-cost contribution cannot beat the immediate -20 failure
    # penalty by terminating now; does NOT prove total policy return ordering.
    assert float((rates*dt*gamma**torch.arange(1000)).sum())<20.


def fake_env():
    from extension.parallelism.m1_kinematics import M1_WHEEL_RADIUS_M
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    names=tuple(reversed(M1_SUPPORT_BODY_NAMES));b=3
    v=torch.zeros(b,4,3);w=v.clone();w[...,1]=.3/M1_WHEEL_RADIUS_M
    f=v.clone();f[...,2]=20
    data=SimpleNamespace(body_link_lin_vel_w=v,body_ang_vel_w=w,
                         body_quat_w=torch.tensor([1.,0,0,0]).expand(b,4,4))
    robot=SimpleNamespace(body_names=names,data=data)
    sensor=SimpleNamespace(body_names=names,data=SimpleNamespace(net_forces_w=f))
    return SimpleNamespace(cfg=SimpleNamespace(m1_flat_first=True),
        scene={'robot':robot,'contact_forces':sensor},
        _m1_stall_slip_stage=torch.tensor([False,True,False]))


def test_replace_not_add_and_preserve_other_stages():
    m=module();assert hasattr(m,'replace_slip')
    env=fake_env();legacy=torch.tensor([4.,4.,4.])
    actual=m.replace_slip(env,legacy)
    torch.testing.assert_close(actual,torch.tensor([4.,2.5,4.]))
    env.scene['contact_forces'].data.net_forces_w.zero_()
    torch.testing.assert_close(m.replace_slip(env,legacy),torch.tensor([4.,0.,4.]))
    env.cfg.m1_flat_first=False
    torch.testing.assert_close(m.replace_slip(env,legacy),legacy)


def test_native_completion_requires_exercised_integration_cases():
    m=module();assert hasattr(m,'validate_native_evidence')
    evidence=dict(nonzero_stall_steps=20,terminal_old_stage=True,terminal_old_force=True,
                  next_step_new_stage=True,history_only_zero=True,rate_error=0.)
    m.validate_native_evidence(evidence)
    for k in evidence:
        bad=evidence.copy();bad[k]=.2 if k=='rate_error' else 0
        with pytest.raises(AssertionError):m.validate_native_evidence(bad)


def test_prepare_snapshot_full_receipts_and_stage_identity():
    m=module();assert hasattr(m,'prepare_stall_snapshot')
    env=fake_env();env.scene=SimpleNamespace(env_origins=torch.zeros(3,3))
    root=torch.zeros(3,3)
    class Scene:
        env_origins=torch.zeros(3,3)
        def __getitem__(self,k):return SimpleNamespace(data=SimpleNamespace(root_pos_w=root))
    env.scene=Scene()
    t=m.StallWindow(3,'cpu',.02)
    course={'ids':torch.ones(3,1,dtype=torch.long),'valid':torch.ones(3,1,dtype=torch.bool)}
    required=torch.ones(3,1,4,dtype=torch.bool);recovered=~required
    levels=torch.tensor([0,1,4])
    for _ in range(105):m.prepare_stall_snapshot(env,t,levels,course,required,recovered)
    torch.testing.assert_close(m.stall_penalty(env),torch.tensor([0.,-.5,0.]))
    root[:,1]=99 # side travel never clears stall
    m.prepare_stall_snapshot(env,t,levels,course,required,recovered)
    assert m.stall_penalty(env)[1]==-.5
    recovered[:]=True
    m.prepare_stall_snapshot(env,t,levels,course,required,recovered)
    assert m.stall_penalty(env).sum()==0


def test_wrapper_and_manager_lifecycle_wiring():
    from pathlib import Path
    base=Path(__file__).parents[1]/'ame_baseline'
    w=(base/'ame_env_wrapper.py').read_text()
    assert 'self._m1_stall_window' in w
    assert w.index('prepare_stall_snapshot(self.unwrapped') < w.index('self.env.step(actions)')
    assert 'self._m1_stall_window.reset(done)' in w
    assert 'func=stall_penalty' in (base/'m1_ame_env_cfg.py').read_text()
    assert 'replace_slip(env, legacy)' in (base/'m1_ame_rewards.py').read_text()


def source_checkpoint():
    from copy import deepcopy
    from ame_baseline.actor_critic_ame import ActorCriticAME
    from ame_baseline.ame_runner import AME_ARCHITECTURE_SIGNATURE
    from ame_baseline.m1_fixed_wheel_checkpoint import fixed_wheel_contract
    from ame_baseline.m1_ame_contract import m1_training_contract
    from ame_baseline.m1_learning_curriculum import LearningCurriculumGate
    actor=ActorCriticAME(1621,1624,12,actor_hidden_dims=(8,),critic_hidden_dims=(8,))
    opt=torch.optim.Adam(actor.parameters());sum(x.square().sum() for x in actor.parameters()).backward();opt.step()
    c=m1_training_contract();c.pop('reward_contract',None)
    return dict(model_state_dict=deepcopy(actor.state_dict()),optimizer_state_dict=opt.state_dict(),
        ame_architecture_signature=AME_ARCHITECTURE_SIGNATURE,ame_num_actor_obs=1621,ame_num_critic_obs=1624,
        ame_num_actions=12,iter=200,next_iter=201,m1_training_contract=c,
        m1_action_contract=fixed_wheel_contract(.3),m1_learning_curriculum=LearningCurriculumGate(1,'cpu').state_dict())


def test_explicit_reward_conversion_preserves_source_and_states():
    m=module();assert hasattr(m,'convert_reward_checkpoint')
    from ame_baseline.m1_ame_contract import m1_training_contract,validate_training_contract
    src=source_checkpoint();new=m.convert_reward_checkpoint(src,'a'*64)
    assert 'reward_contract' not in src['m1_training_contract']
    with pytest.raises(ValueError):validate_training_contract(src,m1_training_contract())
    validate_training_contract(new,m1_training_contract())
    for k,v in src['model_state_dict'].items():torch.testing.assert_close(new['model_state_dict'][k],v,rtol=0,atol=0)
    for p,ss in src['optimizer_state_dict']['state'].items():
        for k,v in ss.items():torch.testing.assert_close(new['optimizer_state_dict']['state'][p][k],v,rtol=0,atol=0)
    assert new['m1_learning_curriculum']==src['m1_learning_curriculum']
    assert new['m1_reward_conversion']['source_sha256']=='a'*64
    assert new['next_iter']==201


@pytest.mark.parametrize('corrupt',['contract','std','optimizer','stage','iteration','dims','course_nan','adam_lr'])
def test_conversion_rejects_invalid_source(corrupt):
    m=module();assert hasattr(m,'convert_reward_checkpoint')
    src=source_checkpoint()
    if corrupt=='contract':src['m1_training_contract']['root_z']=.456
    if corrupt=='std':src['model_state_dict']['std'][0]=float('nan')
    if corrupt=='optimizer':src['optimizer_state_dict']['state'].pop(0)
    if corrupt=='stage':src.pop('m1_learning_curriculum')
    if corrupt=='iteration':src['next_iter']=3
    if corrupt=='dims':src['ame_num_actor_obs']=1589
    if corrupt=='course_nan':src['m1_learning_curriculum']['window_error']=float('nan')
    if corrupt=='adam_lr':src['optimizer_state_dict']['param_groups'][0]['lr']=float('nan')
    with pytest.raises(ValueError):m.convert_reward_checkpoint(src,'a'*64)
