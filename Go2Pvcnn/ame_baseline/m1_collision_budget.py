"""Per-episode collision costs; one immutable snapshot per physical control step."""
from __future__ import annotations
import math
import torch


def collision_budget_contract():
    return dict(version=1, rate_per_s=5., episode_budget=20., combination='max',
                immediate_reset=False, budget_terminal_extra_cost=0.,
                other_failure_cost=20., intermittent='retain_until_reset')


def combine_collision_signals(geometry, contact):
    def clean(signal):
        return torch.nan_to_num(signal, nan=1., posinf=1., neginf=1.).clamp(0.,1.)
    return torch.maximum(clean(geometry), clean(contact))


class CollisionBudget:
    def __init__(self, n, device, dt):
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError('finite positive dt required')
        self.dt=float(dt)
        self.total=torch.zeros(n,device=device,dtype=torch.float64)
        self.step=None
        self.snapshot=None

    @torch.no_grad()
    def update(self, signal, step):
        if self.step == step:
            return self.snapshot
        if signal.shape != self.total.shape:
            raise ValueError('one collision signal per environment required')
        if self.step is not None and step < self.step:
            raise ValueError('control step must be monotonic')
        clean=combine_collision_signals(signal,torch.zeros_like(signal)).double()
        remaining=(20.-self.total).clamp_min(0.)
        requested=5.*self.dt*clean
        cost=torch.minimum(requested,remaining)
        # Close only roundoff at the budget boundary, not a physical tolerance.
        exhausted=(remaining-requested<=1e-10)
        cost=torch.where(exhausted,remaining,cost)
        self.total=torch.where(exhausted,torch.full_like(self.total,20.),self.total+cost)
        self.step=step
        self.snapshot=dict(cost=cost.float(),total=self.total.float().clone(),
                           exhausted=exhausted.clone(),signal=clean.float().clone())
        return self.snapshot

    def reset(self, env_ids=None):
        self.total[slice(None) if env_ids is None else env_ids]=0.
        # Managers reset after reward computation; wrapper telemetry still needs
        # this step's OLD episode snapshot. Next control step replaces it.


def current_collision_snapshot(env):
    budget=getattr(env,'_m1_collision_budget',None)
    if budget is None or budget.step != env.common_step_counter or budget.snapshot is None:
        raise RuntimeError('current collision budget snapshot is unavailable')
    return budget.snapshot


def collision_budget_cost(env):
    return -current_collision_snapshot(env)['cost']/float(env.step_dt)


def collision_budget_exhausted(env):
    return current_collision_snapshot(env)['exhausted']
