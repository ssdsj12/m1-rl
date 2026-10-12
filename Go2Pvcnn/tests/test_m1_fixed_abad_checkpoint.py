from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
import torch
from ame_baseline.actor_critic_ame import ActorCriticAME
from ame_baseline.ame_runner import AmeOnPolicyRunner, AME_ARCHITECTURE_SIGNATURE
from ame_baseline.m1_ame_contract import m1_training_contract
from ame_baseline.m1_fixed_abad import fixed_abad_contract
from ame_baseline.m1_learning_curriculum import LearningCurriculumGate


def runner():
    r=object.__new__(AmeOnPolicyRunner)
    a=ActorCriticAME(1621,1624,8,actor_hidden_dims=(8,),critic_hidden_dims=(8,))
    r.device='cpu';r.alg=NS(actor_critic=a,optimizer=torch.optim.Adam(a.parameters()))
    r.empirical_normalization=False;r.current_learning_iteration=0;r.logger_type='tensorboard'
    r.env=NS(unwrapped=NS(cfg=NS(m1_fixed_wheel_speed_m_s=.3,m1_fixed_abad=True,
        m1_training_contract=m1_training_contract(fixed_abad=True)),
        _m1_learning_gate=LearningCurriculumGate(4,'cpu')),reset=lambda:None)
    return r


def checkpoint(r):
    sum(p.square().sum() for p in r.alg.actor_critic.parameters()).backward();r.alg.optimizer.step()
    return dict(model_state_dict=deepcopy(r.alg.actor_critic.state_dict()),
        optimizer_state_dict=deepcopy(r.alg.optimizer.state_dict()),iter=0,next_iter=1,
        ame_architecture_signature=AME_ARCHITECTURE_SIGNATURE,ame_num_actor_obs=1621,
        ame_num_critic_obs=1624,ame_num_actions=8,m1_action_contract=fixed_abad_contract(.3),
        m1_training_contract=m1_training_contract(fixed_abad=True),
        m1_learning_curriculum=r.env.unwrapped._m1_learning_gate.state_dict())


def test_fresh_eight_save_reload(tmp_path):
    r=runner();checkpoint(r)
    p=tmp_path/'model_0.pt';r.save(p)
    s=torch.load(p,weights_only=False)
    assert s['m1_action_contract']==fixed_abad_contract(.3)
    assert s['m1_training_contract']==m1_training_contract(fixed_abad=True)
    assert s['m1_learning_curriculum']['stage']==0 and s['next_iter']==1
    assert 'm1_action_conversion' not in s and 'm1_reward_conversion' not in s
    other=runner();other.load(p)
    assert other.current_learning_iteration==1
    for k,v in s['model_state_dict'].items():torch.testing.assert_close(other.alg.actor_critic.state_dict()[k],v)
    assert len(other.alg.optimizer.state)==len(r.alg.optimizer.state)


@pytest.mark.parametrize('bad',['missing','angle','speed','order','dimension','training','nan','std','adam'])
def test_reject_before_live_mutation(tmp_path,bad):
    r=runner();s=checkpoint(r)
    if bad=='missing':s.pop('m1_action_contract')
    if bad=='angle':s['m1_action_contract']['fixed_joint_targets'][0]=.1
    if bad=='speed':s['m1_action_contract']['wheel_speed_m_s']=.4
    if bad=='order':s['m1_action_contract']['policy_joint_names'].reverse()
    if bad=='dimension':s['ame_num_actions']=12
    if bad=='training':s['m1_training_contract']=m1_training_contract()
    if bad=='nan':s['model_state_dict']['std'][0]=float('nan')
    if bad=='std':s['model_state_dict']['std'][0]=0
    if bad=='adam':s['optimizer_state_dict']['state'][0]['exp_avg']=torch.zeros(2)
    target=runner();before=deepcopy(target.alg.actor_critic.state_dict());p=tmp_path/'bad.pt';torch.save(s,p)
    with pytest.raises(ValueError):target.load(p)
    assert not target.alg.optimizer.state
    for k,v in before.items():torch.testing.assert_close(v,target.alg.actor_critic.state_dict()[k])


def test_eight_contract_rejected_in_twelve_runtime():
    from ame_baseline.m1_fixed_wheel_checkpoint import validate_action_contract
    with pytest.raises(ValueError):validate_action_contract({'m1_action_contract':fixed_abad_contract(.3)},12,.3)
