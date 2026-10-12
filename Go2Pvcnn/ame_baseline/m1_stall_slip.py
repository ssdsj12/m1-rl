"""Bounded reward-only costs; no control, termination or success authority."""
from __future__ import annotations

import math
import torch


def reward_contract():
    return dict(version='stall-slip-v1', stages=[1,2,3], window_s=2.,
                progress_m=.05, stall_rate=.5, slip_rate=.25,
                slip_deadband_m_s=.03, slip_scale_m_s=.27,
                current_upward_force_n=10., progress='world_x_high_water')


class StallWindow:
    """Per-row rolling high-water progress; reset never borrows another episode."""
    def __init__(self, n, device, dt):
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError('finite positive dt required')
        self.dt=float(dt)
        self.lag=2./self.dt
        self.size=math.ceil(self.lag)+2
        self.history=torch.zeros(n,self.size,device=device)
        self.high=torch.zeros(n,device=device)
        self.count=torch.zeros(n,device=device,dtype=torch.long)
        self.ready=torch.zeros(n,device=device,dtype=torch.bool)
        self.identity=None
        self.cursor=-1

    def reset(self, rows):
        self.ready[rows]=False
        self.count[rows]=0
        self.high[rows]=0
        self.history[rows]=0

    @torch.no_grad()
    def update(self, x, identity, active, complete):
        if x.shape != self.high.shape or identity.shape[0]!=x.shape[0]:
            raise ValueError('one x and identity row per environment required')
        finite=torch.isfinite(x)&torch.isfinite(identity).all(-1)
        if self.identity is None:
            self.identity=identity.clone()
        changed=(self.identity!=identity).any(-1)
        self.identity.copy_(identity)
        enabled=active&~complete&finite
        self.reset(changed|~enabled)
        fresh=~self.ready
        clean=torch.where(finite,x,torch.zeros_like(x))
        self.high=torch.where(fresh,clean,torch.maximum(self.high,clean))
        self.history=torch.where(fresh[:,None],self.high[:,None],self.history)
        self.count=torch.where(fresh,torch.zeros_like(self.count),self.count+1)
        self.cursor=(self.cursor+1)%self.size
        self.history[:,self.cursor]=self.high
        lo=math.floor(self.lag);frac=self.lag-lo
        past=(self.history[:,(self.cursor-lo)%self.size]*(1-frac)
              +self.history[:,(self.cursor-lo-1)%self.size]*frac)
        progress=(self.high-past).clamp_min(0.)
        warm=enabled&(self.count*self.dt>=2.-1e-7)
        rate=torch.where(warm,.5*(1-progress/.05).clamp(0.,1.),0.)
        self.ready=enabled
        return dict(rate=rate,progress=torch.where(warm,progress,0.),warm=warm,invalid=~finite)


def rolling_contact_speed(linear, angular, quat, radius):
    """Gravity-normal disk contact approximation, total wheel-body velocity."""
    w,x,y,z=quat.unbind(-1)
    axle=torch.stack((2*(x*y-w*z),1-2*(x*x+z*z),2*(y*z+w*x)),-1)
    down=torch.zeros_like(axle);down[...,2]=-1
    radial=down-(down*axle).sum(-1,keepdim=True)*axle
    radial=radius*radial/radial.norm(dim=-1,keepdim=True).clamp_min(1e-6)
    return (linear+torch.linalg.cross(angular,radial,dim=-1))[...,:2].norm(dim=-1)


def bounded_slip(speed, forces):
    finite=torch.isfinite(speed)&torch.isfinite(forces).all(-1)
    contact=finite&(forces[...,2]>10.)
    clean=torch.where(finite,speed,0.)
    costs=((clean-.03)/.27).clamp(0.,1.).square()
    return dict(rate=.25*torch.where(contact,costs,0.).amax(-1),contact=contact,
                invalid=~finite.all(-1),speed=torch.where(contact,clean,0.))


def prepare_stall_snapshot(env, tracker, levels, course, required, recovered):
    """Old-episode snapshot; consume before Isaac's automatic reset."""
    active=(levels>=1)&(levels<=3)
    origins=env.scene.env_origins
    identity=torch.cat((course['ids'].to(torch.float64),levels[:,None].to(torch.float64),
                        origins.to(torch.float64)),dim=-1)
    valid=course['valid']
    complete=valid.any(-1)&((~required|recovered).all(-1)|~valid).all(-1)
    x=env.scene['robot'].data.root_pos_w[:,0]-origins[:,0]
    env._m1_stall_slip_stage=active.clone()
    env._m1_stall_snapshot=tracker.update(x,identity,active,complete)


def stall_penalty(env):
    snapshot=getattr(env,'_m1_stall_snapshot',None)
    if snapshot is None:
        return torch.zeros(env.num_envs,device=env.device)
    return -snapshot['rate']


def replace_slip(env, legacy):
    """Replace the existing -0.1 term, not add another slip charge. No dt here."""
    if not getattr(env.cfg,'m1_flat_first',False):
        return legacy
    active=getattr(env,'_m1_stall_slip_stage',torch.zeros_like(legacy,dtype=torch.bool))
    from .m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices
    from extension.parallelism.m1_kinematics import M1_WHEEL_RADIUS_M
    robot=env.scene['robot'];sensor=env.scene['contact_forces']
    bi=list(resolve_named_indices(robot.body_names,M1_SUPPORT_BODY_NAMES))
    si=list(resolve_named_indices(sensor.body_names,M1_SUPPORT_BODY_NAMES))
    speed=rolling_contact_speed(robot.data.body_link_lin_vel_w[:,bi],
        robot.data.body_ang_vel_w[:,bi],robot.data.body_quat_w[:,bi],M1_WHEEL_RADIUS_M)
    out=bounded_slip(speed,sensor.data.net_forces_w[:,si])
    rate=torch.where(active,out['rate'],0.)
    env._m1_slip_snapshot=dict(rate=rate,old_rate=torch.where(active,.1*legacy,0.),
        speed=out['speed'].amax(-1),loaded=out['contact'].float().mean(-1),invalid=out['invalid'])
    return torch.where(active,rate/.1,legacy)


def convert_reward_checkpoint(source, source_sha256):
    """Explicit stage0 reference-v2 migration; tensors and Adam stay unchanged."""
    import copy
    import re
    from .m1_ame_contract import m1_training_contract
    from .m1_fixed_wheel_checkpoint import validate_action_contract, validate_checkpoint_state
    from .actor_critic_ame import ActorCriticAME
    from .ame_runner import AME_ARCHITECTURE_SIGNATURE
    from .m1_learning_curriculum import LearningCurriculumGate
    target=m1_training_contract();old=copy.deepcopy(target);old.pop('reward_contract')
    if source.get('m1_training_contract')!=old or not re.fullmatch('[0-9a-f]{64}',source_sha256):
        raise ValueError('Expected unconverted reference-v2 source and full SHA256')
    if source.get('ame_architecture_signature')!=AME_ARCHITECTURE_SIGNATURE:
        raise ValueError('AME architecture mismatch')
    if tuple(source.get(k) for k in ('ame_num_actor_obs','ame_num_critic_obs','ame_num_actions'))!=(1621,1624,12):
        raise ValueError('AME dimensions mismatch')
    gate=source.get('m1_learning_curriculum')
    if not isinstance(gate,dict) or gate.get('stage')!=0 or 'streak' not in gate:
        raise ValueError('Migration requires a saved stage0 curriculum')
    LearningCurriculumGate(1,'cpu').load_state_dict(gate)
    def finite_tree(value):
        if torch.is_tensor(value):
            if not bool(torch.isfinite(value).all()):raise ValueError('Nonfinite checkpoint metadata')
        elif isinstance(value,float):
            if not math.isfinite(value):raise ValueError('Nonfinite checkpoint metadata')
        elif isinstance(value,dict):
            for child in value.values():finite_tree(child)
        elif isinstance(value,(list,tuple)):
            for child in value:finite_tree(child)
    finite_tree(source['optimizer_state_dict'])
    if not isinstance(source.get('iter'),int) or source.get('next_iter')!=source['iter']+1:
        raise ValueError('Invalid checkpoint iteration')
    validate_action_contract(source,12,.3)
    state=source['model_state_dict']
    def hidden(prefix):
        keys=sorted((k for k in state if re.fullmatch(prefix+r'\.\d+\.weight',k)),
                    key=lambda k:int(k.split('.')[1]))
        return [state[k].shape[0] for k in keys[:-1]]
    actor=ActorCriticAME(1621,1624,12,actor_hidden_dims=hidden('actor'),critic_hidden_dims=hidden('critic'))
    validate_checkpoint_state(source,actor,load_optimizer=True)
    out=copy.deepcopy(source)
    out['m1_training_contract']=target
    out['m1_reward_conversion']=dict(source_sha256=source_sha256,source_iter=source['iter'],
        from_reward_contract='reference-learning-v1',to_reward_contract=reward_contract())
    return out
