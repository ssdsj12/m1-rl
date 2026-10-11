"""Explicit, fail-closed migration of the AME 16-action Adam checkpoint."""
from copy import deepcopy
import re
import torch
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES
from extension.parallelism.rl_adapter import resolve_named_indices
from .m1_ame_contract import validate_fixed_wheel_speed


def fixed_wheel_contract(speed_m_s):
    return dict(version=1, mode='fixed_wheel_leg_only',
                wheel_speed_m_s=validate_fixed_wheel_speed(speed_m_s),
                leg_joint_names=list(M1_PLANNER_JOINT_NAMES), wheel_joint_names=list(M1_WHEEL_JOINT_NAMES),
                executed_history_joint_names=list(M1_ASSET_JOINT_NAMES))


def validate_action_contract(checkpoint, num_actions, speed_m_s):
    saved = checkpoint.get('m1_action_contract')
    if speed_m_s is not None:
        if num_actions != 12 or saved != fixed_wheel_contract(speed_m_s):
            raise ValueError('M1 action contract does not match fixed-wheel runtime')
    elif saved is not None or num_actions == 12:
        raise ValueError('M1 action contract requires an explicit fixed-wheel runtime')


def _finite(tensor, label):
    if not torch.is_tensor(tensor) or not bool(torch.isfinite(tensor).all()):
        raise ValueError(f'Non-finite or invalid tensor: {label}')


def validate_checkpoint_state(checkpoint, actor=None, *, load_optimizer=False):
    """Check state before mutating any live model/optimizer."""
    state=checkpoint['model_state_dict']
    for name,value in state.items():
        _finite(value,name)
    if 'std' not in state or not bool((state['std']>0).all()):
        raise ValueError('Invalid checkpoint std')
    if actor is not None:
        expected=actor.state_dict()
        if state.keys()!=expected.keys() or any(state[k].shape!=v.shape for k,v in expected.items()):
            raise ValueError('Checkpoint model state shape/key mismatch')
    if load_optimizer:
        params=list(actor.parameters());opt=checkpoint['optimizer_state_dict']
        if len(opt['param_groups'])!=1 or opt['param_groups'][0]['params']!=list(range(len(params))):
            raise ValueError('Checkpoint optimizer parameter identities mismatch')
        for pid,values in opt['state'].items():
            if pid not in range(len(params)):
                raise ValueError('Unknown optimizer parameter')
            for name,value in values.items():
                _finite(value,f'optimizer.{pid}.{name}')
                if (name=='step' and (value.numel()!=1 or float(value)<0)) or (name!='step' and value.shape!=params[pid].shape):
                    raise ValueError('Checkpoint optimizer state shape mismatch')
        if checkpoint.get('m1_action_contract') is not None:
            if set(opt['state'])!=set(range(len(params))):
                raise ValueError('Missing fixed-wheel optimizer states')
            allowed={'step','exp_avg','exp_avg_sq'} | ({'max_exp_avg_sq'} if opt['param_groups'][0].get('amsgrad',False) else set())
            if any(set(v)!=allowed for v in opt['state'].values()):
                raise ValueError('Unsupported fixed-wheel optimizer state')


def convert_fixed_wheel_checkpoint(source, old_actor, new_actor, speed_m_s, source_sha):
    from .ame_runner import AME_ARCHITECTURE_SIGNATURE
    contract = fixed_wheel_contract(speed_m_s)
    if not re.fullmatch('[0-9a-f]{64}', source_sha):
        raise ValueError('Source SHA256 is required')
    if source.get('ame_architecture_signature') != AME_ARCHITECTURE_SIGNATURE or source.get('m1_action_contract') is not None:
        raise ValueError('Expected an unconverted AME architecture signature')
    dims = (source.get('ame_num_actor_obs'), source.get('ame_num_critic_obs'), source.get('ame_num_actions'))
    if dims != (1589,1592,16) or old_actor.std.numel() != 16 or new_actor.std.numel() != 12:
        raise ValueError('Unsupported source/runtime dimensions')
    for actor in (old_actor,new_actor):
        if (actor.map_dim+actor.actor_state_dim,actor.map_dim+actor.critic_state_dim) != (1589,1592):
            raise ValueError('Observation architecture mismatch')
    if source.get('next_iter',source['iter']+1) != source['iter']+1 or not isinstance(source.get('m1_learning_curriculum'),dict):
        raise ValueError('Invalid next_iter or missing curriculum state')
    original = source['model_state_dict']
    expected = old_actor.state_dict()
    if original.keys() != expected.keys():
        raise ValueError('Model state keys mismatch')
    for name,tensor in original.items():
        _finite(tensor,name)
        if tensor.shape != expected[name].shape:
            raise ValueError(f'Model shape mismatch: {name}')
    if not bool((original['std'] > 0).all()):
        raise ValueError('Invalid std')
    last = f'actor.{len(old_actor.actor)-1}'
    changed = {'std',last+'.weight',last+'.bias'}
    rows = list(resolve_named_indices(M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES))
    result = deepcopy(source)
    for name in changed:
        result['model_state_dict'][name] = original[name][rows].clone()
    for name,tensor in new_actor.state_dict().items():
        if result['model_state_dict'][name].shape != tensor.shape:
            raise ValueError(f'Converted model shape mismatch: {name}')

    # RSL PPO creates one Adam group from actor_critic.parameters(), in the
    # exact registration order below. Reject other group/ID layouts rather
    # than guessing identities from state dictionary insertion order.
    params = list(old_actor.named_parameters())
    if [n for n,_ in params] != [n for n,_ in new_actor.named_parameters()]:
        raise ValueError('Named parameter order mismatch')
    optimizer = result['optimizer_state_dict']
    groups = optimizer['param_groups']
    ids = list(range(len(params)))
    if len(groups) != 1 or groups[0]['params'] != ids or set(optimizer['state']) != set(ids):
        raise ValueError('Unsupported Adam parameter identities or missing states')
    if 'param_names' in groups[0] and groups[0]['param_names'] != [n for n,_ in params]:
        raise ValueError('Adam parameter name mismatch')
    for pid,(name,param) in zip(ids,params):
        state = optimizer['state'][pid]
        allowed = {'step','exp_avg','exp_avg_sq'} | ({'max_exp_avg_sq'} if groups[0].get('amsgrad',False) else set())
        if set(state) != allowed:
            raise ValueError(f'Unsupported Adam state: {name}')
        for key,value in state.items():
            _finite(value,f'{name}.{key}')
            if key == 'step':
                if value.numel() != 1 or float(value) < 0:
                    raise ValueError('Invalid Adam step')
            else:
                if value.shape != param.shape:
                    raise ValueError(f'Adam state shape mismatch: {name}.{key}')
                if name in changed:
                    state[key] = value[rows].clone()
    result['ame_num_actions'] = 12
    result['m1_action_contract'] = contract
    result['m1_action_conversion'] = dict(source_sha256=source_sha,source_actions=16,
        destination_actions=12,source_iter=source['iter'],leg_rows=rows,sliced_parameters=sorted(changed),
        optimizer_parameter_names=[n for n,_ in params])
    return result
