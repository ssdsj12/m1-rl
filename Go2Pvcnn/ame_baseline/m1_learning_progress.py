"""Bounded measurements for one latched encounter; never an action policy."""
import torch


class LearningProgress:
    def __init__(self,num_envs,device):
        self.key=torch.full((num_envs,),-1,dtype=torch.long,device=device)
        self.baseline=torch.full((num_envs,),float('nan'),device=device)
        self.unload_high=torch.zeros(num_envs,device=device)
        self.passage_high=torch.zeros_like(self.unload_high)

    def reset(self,rows):
        self.key[rows]=-1;self.baseline[rows]=float('nan')
        self.unload_high[rows]=0.;self.passage_high[rows]=0.

    @torch.no_grad()
    def update(self,*,key,selected,forces,weight,active,safe,before,airborne,progress):
        changed=key!=self.key
        self.reset(changed);self.key.copy_(key)
        rows=torch.arange(key.numel(),device=key.device)
        finite=torch.isfinite(forces).all(dim=(-1,-2))&torch.isfinite(weight)&(weight>0)
        upward=forces[...,2].clamp_min(0.)
        load=upward[rows,selected]
        other=torch.arange(4,device=key.device)[None]!=selected[:,None]
        # A minimum upward load on each support, >=half body weight in total,
        # and non-sidewall-dominated force. These shape feedback, not success.
        individual=(upward>10)&(upward>=.1*weight[:,None])
        individual &= forces[...,:2].norm(dim=-1)<=upward
        support=(individual|~other).all(-1)&torch.where(other,upward,0.).sum(-1).ge(.5*weight)
        eligible=(key>=0)&active&safe&finite&support
        establish=eligible&before&~airborne&(load>10)&~torch.isfinite(self.baseline)
        self.baseline=torch.where(establish,load,self.baseline)
        score=(1-load/self.baseline).clamp(0.,1.)
        known=(key>=0)&finite&torch.isfinite(score)
        delta=(score-self.unload_high).clamp_min(0.)
        unload=torch.where(eligible&before&known,delta,0.)
        self.unload_high=torch.where(known,torch.maximum(self.unload_high,score),self.unload_high)
        valid_progress=(key>=0)&torch.isfinite(progress)
        position=progress.clamp(0.,1.)
        passage=torch.where(eligible&airborne&valid_progress,
            (position-self.passage_high).clamp_min(0.),0.)
        # Observe unsafe or loaded advance too: support restored at the same
        # position must not pay old movement retroactively.
        self.passage_high=torch.where(valid_progress,
            torch.maximum(self.passage_high,position),self.passage_high)
        return {'unload_delta':unload,'passage_delta':passage}
