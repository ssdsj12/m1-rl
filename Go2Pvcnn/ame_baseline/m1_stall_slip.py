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
