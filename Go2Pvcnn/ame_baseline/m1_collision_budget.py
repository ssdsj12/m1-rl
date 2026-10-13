"""Per-episode collision costs; one immutable snapshot per physical control step."""
from __future__ import annotations
import math
import torch


EPISODE_BUDGET = 20.


def _validate_cost_per_step(value):
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                              or not math.isfinite(value) or value <= 0):
        raise ValueError('finite positive cost_per_step required')
    return None if value is None else float(value)


def collision_budget_contract(*, cost_per_step=None):
    cost_per_step = _validate_cost_per_step(cost_per_step)
    contract = dict(version=1, rate_per_s=5., episode_budget=EPISODE_BUDGET, combination='max',
                    immediate_reset=False, budget_terminal_extra_cost=0.,
                    other_failure_cost=20., intermittent='retain_until_reset')
    if cost_per_step is not None:
        contract.pop('rate_per_s')
        contract.update(version=2, mode='per_control_step', cost_per_step=cost_per_step)
    return contract


def combine_collision_signals(geometry, contact):
    def clean(signal):
        return torch.nan_to_num(signal, nan=1., posinf=1., neginf=1.).clamp(0.,1.)
    return torch.maximum(clean(geometry), clean(contact))


class CollisionBudget:
    def __init__(self, n, device, dt, *, cost_per_step=None):
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError('finite positive dt required')
        self.dt=float(dt)
        self._cost_per_step = _validate_cost_per_step(cost_per_step)
        self.total=torch.zeros(n,device=device,dtype=torch.float64)
        self.step=None
        self.snapshot=None

    @property
    def cost_per_step(self):
        return self._cost_per_step

    @property
    def contract(self):
        """A fresh contract derived from the settings used by update()."""
        return collision_budget_contract(cost_per_step=self.cost_per_step)

    @torch.no_grad()
    def update(self, signal, step):
        if self.step == step:
            return self.snapshot
        if signal.shape != self.total.shape:
            raise ValueError('one collision signal per environment required')
        if self.step is not None and step < self.step:
            raise ValueError('control step must be monotonic')
        clean=combine_collision_signals(signal,torch.zeros_like(signal)).double()
        remaining=(EPISODE_BUDGET-self.total).clamp_min(0.)
        requested=(5.*self.dt*clean if self.cost_per_step is None
                   else self.cost_per_step*(clean > 0).to(clean.dtype))
        cost=torch.minimum(requested,remaining)
        # Close only roundoff at the budget boundary, not a physical tolerance.
        exhausted=(remaining-requested<=1e-10)
        cost=torch.where(exhausted,remaining,cost)
        self.total=torch.where(exhausted,torch.full_like(self.total,EPISODE_BUDGET),self.total+cost)
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
