"""Diagnostic same-episode handoff gate; not obstacle/crossing acceptance.

Create a new instance for every episode/leg batch. Actual support guards remain
authoritative during and after rolling. Does not extend phase time budgets.
"""
import math
import torch


class LiftHandoffGate:
    def __init__(self,batch,device='cpu'):
        self.count=torch.zeros(batch,dtype=torch.long,device=device)
        self.poisoned=torch.zeros(batch,dtype=torch.bool,device=device)
        self.step=-1

    def update(self,step,*,height,previous_height,force,selected,tilt,tilt_rate,
               margin,valid,collision,target,dt):
        b=len(self.count)
        if type(step) is not int or step<0 or not math.isfinite(dt) or not 0<dt<=.1 or not math.isfinite(target) or target<=0:
            raise ValueError('invalid handoff time/target')
        floats=((height,(b,)),(previous_height,(b,)),(force,(b,4)),(tilt,(b,2)),(tilt_rate,(b,2)),(margin,(b,)))
        if any(x.shape!=shape or not x.is_floating_point() or x.device!=self.count.device for x,shape in floats):
            raise ValueError('invalid handoff floating inputs')
        if any(x.shape!=(b,) or x.device!=self.count.device or x.dtype!=dtype for x,dtype in ((selected,torch.long),(valid,torch.bool),(collision,torch.bool))):
            raise ValueError('invalid handoff masks')
        if ((selected<0)|(selected>3)).any():raise ValueError('invalid selected leg')
        finite=torch.ones(b,dtype=torch.bool,device=self.count.device)
        for x,_ in floats:finite &= torch.isfinite(x).reshape(b,-1).all(-1)
        mask=torch.arange(4,device=self.count.device)[None]!=selected[:,None]
        self.poisoned |= collision
        safe=finite & valid & ~self.poisoned
        safe &= ((height-target).abs()<=.001)&((height-previous_height).abs()/dt<=.01)
        safe &= ((force>=30.)|~mask).all(-1)&(force.gather(1,selected[:,None]).squeeze(1)<=10.)
        safe &= (tilt.abs()<=.15).all(-1)&(tilt_rate.abs()<=.2).all(-1)&(margin>=.02)
        self.count=torch.where(safe,self.count+1 if step==self.step+1 else 1,0).clamp(max=5)
        self.step=step
        return self.count>=5
