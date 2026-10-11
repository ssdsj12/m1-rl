from copy import deepcopy
import importlib
from types import SimpleNamespace as NS
import pytest
import torch
from ame_baseline.actor_critic_ame import ActorCriticAME
from ame_baseline.ame_runner import AmeOnPolicyRunner, AME_ARCHITECTURE_SIGNATURE

LEGS = [0,1,2,4,5,6,8,9,10,12,13,14]

def migration_module():
    try:
        return importlib.import_module('ame_baseline.m1_fixed_wheel_checkpoint')
    except ModuleNotFoundError:
        pytest.fail('explicit fixed-wheel checkpoint conversion is missing')

def actors():
    return [ActorCriticAME(1589,1592,n,actor_hidden_dims=(8,),critic_hidden_dims=(8,)) for n in (16,12)]

def source_checkpoint(old):
    optimizer = torch.optim.Adam(old.parameters())
    sum(p.square().sum() for p in old.parameters()).backward()
    optimizer.step()
    return dict(model_state_dict=deepcopy(old.state_dict()), optimizer_state_dict=optimizer.state_dict(),
                ame_architecture_signature=AME_ARCHITECTURE_SIGNATURE,
                ame_num_actor_obs=1589,ame_num_critic_obs=1592,ame_num_actions=16,
                iter=300,next_iter=301,m1_learning_curriculum={'stage':1})

def test_conversion_preserves_leg_function_and_named_adam_states():
    mod = migration_module()
    old,new = actors()
    source = source_checkpoint(old)
    converted = mod.convert_fixed_wheel_checkpoint(source,old,new,.3,'a'*64)
    new.load_state_dict(converted['model_state_dict'])
    old.eval(); new.eval()
    obs = torch.randn(2,1589)
    torch.testing.assert_close(new.act_inference(obs),old.act_inference(obs)[:,LEGS])
    changed = {'std','actor.2.weight','actor.2.bias'}
    for name,tensor in source['model_state_dict'].items():
        torch.testing.assert_close(converted['model_state_dict'][name], tensor[LEGS] if name in changed else tensor)
    for (name,param),pid in zip(old.named_parameters(),source['optimizer_state_dict']['param_groups'][0]['params']):
        for key,value in source['optimizer_state_dict']['state'][pid].items():
            expected = value[LEGS] if name in changed and value.ndim else value
            torch.testing.assert_close(converted['optimizer_state_dict']['state'][pid][key],expected)
    assert source['ame_num_actions'] == 16 and source['model_state_dict']['std'].shape == (16,)
    assert converted['ame_num_actions'] == 12 and converted['next_iter'] == 301
    assert converted['m1_action_conversion']['source_sha256'] == 'a'*64
    assert converted['m1_action_contract'] == mod.fixed_wheel_contract(.3)
    opt = torch.optim.Adam(new.parameters())
    opt.load_state_dict(converted['optimizer_state_dict'])
    opt.zero_grad(); sum(p.square().sum() for p in new.parameters()).backward(); opt.step()
    assert all(torch.isfinite(p).all() for p in new.parameters())

@pytest.mark.parametrize('corruption', ['signature','std','adam_shape','adam_missing','iteration','dimensions'])
def test_conversion_fails_closed(corruption):
    mod = migration_module()
    old,new = actors(); source = source_checkpoint(old)
    if corruption == 'signature': source['ame_architecture_signature'] = 'other'
    if corruption == 'std': source['model_state_dict']['std'][0] = float('nan')
    if corruption == 'adam_shape': source['optimizer_state_dict']['state'][0]['exp_avg'] = torch.zeros(3)
    if corruption == 'adam_missing': source['optimizer_state_dict']['state'].pop(0)
    if corruption == 'iteration': source['next_iter'] = 999
    if corruption == 'dimensions': source['ame_num_actor_obs'] = 2
    with pytest.raises(ValueError): mod.convert_fixed_wheel_checkpoint(source,old,new,.3,'a'*64)

@pytest.mark.parametrize('mutation', ['missing','speed','order'])
def test_runner_rejects_wrong_contract_before_model_mutation(tmp_path,mutation):
    mod = migration_module()
    old,new = actors(); source = source_checkpoint(old)
    checkpoint = mod.convert_fixed_wheel_checkpoint(source,old,new,.3,'a'*64)
    if mutation == 'missing': checkpoint.pop('m1_action_contract')
    if mutation == 'speed': checkpoint['m1_action_contract']['wheel_speed_m_s'] = .4
    if mutation == 'order': checkpoint['m1_action_contract']['leg_joint_names'].reverse()
    runner = object.__new__(AmeOnPolicyRunner)
    runner.device='cpu'; runner.alg=NS(actor_critic=new,optimizer=torch.optim.Adam(new.parameters()))
    runner.env=NS(unwrapped=NS(cfg=NS(m1_fixed_wheel_speed_m_s=.3)))
    before=deepcopy(new.state_dict()); path=tmp_path/'wrong.pt'; torch.save(checkpoint,path)
    with pytest.raises(ValueError,match='contract'): runner.load(path)
    for k,v in before.items(): torch.testing.assert_close(v,new.state_dict()[k])
