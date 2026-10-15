"""Pure bounded support-ranking and measured-lift calculations.

These heuristics do not certify support or crossing. Callers retain raw
physical guards and commit results only with the complete action transaction.
"""
from dataclasses import dataclass
import math

import torch


def _float(value, shape, like=None):
    if (not isinstance(value, torch.Tensor) or value.shape != shape
            or value.dtype not in (torch.float32, torch.float64)
            or not bool(torch.isfinite(value).all())):
        raise ValueError('expected finite floating tensor with matching shape')
    if like is not None and (value.dtype != like.dtype or value.device != like.device):
        raise ValueError('tensor dtype/device mismatch')


def _history(value, like):
    if (not isinstance(value, torch.Tensor) or value.shape != (like.shape[0],)
            or value.dtype != torch.bool or value.device != like.device):
        raise ValueError('history_valid must be matching bool vector')


def _positive(*values):
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('parameters must be positive finite')


def filter_support_fz(raw_fz, previous, history_valid, dt, tau_s):
    if not isinstance(raw_fz, torch.Tensor) or raw_fz.ndim != 2:
        raise ValueError('raw force must be [B,4]')
    b = raw_fz.shape[0]
    _float(raw_fz, (b,4)); _float(previous, (b,4), raw_fz)
    _float(dt, (b,), raw_fz); _history(history_valid, raw_fz)
    _positive(tau_s)
    if bool((dt <= 0).any()):
        raise ValueError('dt must be positive')
    raw = raw_fz.clamp_min(0)
    alpha = -torch.expm1(-dt/tau_s)
    return torch.where(history_valid[:,None], previous.clamp_min(0)+alpha[:,None]*(raw-previous.clamp_min(0)), raw)


def desired_support_com_xy(wheels_w, filtered_fz, active_wheel):
    if not isinstance(wheels_w, torch.Tensor) or wheels_w.ndim != 3:
        raise ValueError('wheels must be [B,4,3]')
    b = wheels_w.shape[0]
    _float(wheels_w, (b,4,3)); _float(filtered_fz, (b,4), wheels_w)
    if (not isinstance(active_wheel, torch.Tensor) or active_wheel.shape != (b,)
            or active_wheel.dtype != torch.long or active_wheel.device != wheels_w.device
            or bool(((active_wheel < 0) | (active_wheel > 3)).any())):
        raise ValueError('active wheel must be matching long vector in 0..3')
    weights = filtered_fz.clamp_min(torch.finfo(filtered_fz.dtype).eps).reciprocal()
    weights = weights.scatter(1, active_wheel[:,None], 0.)
    weights = weights/weights.sum(-1, keepdim=True)
    return (wheels_w[:,:,:2]*weights[:,:,None]).sum(1)


@dataclass(frozen=True)
class LiftStep:
    next_z: torch.Tensor
    increment: torch.Tensor
    reserve: torch.Tensor
    conservative_fz: torch.Tensor
    conservative_margin: torch.Tensor
    lead_error: torch.Tensor
    freeze_code: torch.Tensor  # 0 advancing, 1 reserve, 2 lead, 3 ceiling


def combined_tripod_reserve(min_loads_n, valid):
    """Current, anchor-target and measured-target predictions; invalid freezes."""
    if (not isinstance(min_loads_n,torch.Tensor) or min_loads_n.ndim!=2
            or min_loads_n.shape[1]!=3 or min_loads_n.dtype not in (torch.float32,torch.float64)
            or not isinstance(valid,torch.Tensor) or valid.shape!=min_loads_n.shape
            or valid.dtype!=torch.bool or valid.device!=min_loads_n.device):
        raise ValueError('expected floating [B,3] predictions and matching bool validity')
    safe=valid.all(-1)&torch.isfinite(min_loads_n).all(-1)
    reserve=((min_loads_n.amin(-1)-30.)/15.).clamp(0,1)
    return torch.where(safe,reserve,torch.zeros_like(reserve))


def measured_lift_step(accepted_z, measured_z, max_z, min_fz, margin,
                       previous_min_fz, previous_margin, history_valid, dt, *,
                       rate_m_s, lead_m, force_floor_n, force_band_n,
                       margin_floor_m, margin_band_m, external_reserve=None, measured_floor=False):
    if not isinstance(accepted_z, torch.Tensor) or accepted_z.ndim != 1:
        raise ValueError('accepted_z must be vector')
    shape = accepted_z.shape
    for v in (accepted_z, measured_z, max_z, min_fz, margin, previous_min_fz, previous_margin, dt):
        _float(v, shape, accepted_z)
    _history(history_valid, accepted_z)
    if type(measured_floor) is not bool:
        raise ValueError('measured_floor must be bool')
    _positive(rate_m_s, lead_m, force_floor_n, force_band_n, margin_floor_m, margin_band_m)
    if bool((dt <= 0).any()):
        raise ValueError('dt must be positive')
    fz = torch.where(history_valid, torch.minimum(min_fz,2*min_fz-previous_min_fz),min_fz)
    cm = torch.where(history_valid, torch.minimum(margin,2*margin-previous_margin),margin)
    reserve = torch.minimum(((fz-force_floor_n)/force_band_n).clamp(0,1),
                            ((cm-margin_floor_m)/margin_band_m).clamp(0,1))
    if external_reserve is not None:
        _float(external_reserve, shape, accepted_z)
        if bool(((external_reserve < 0) | (external_reserve > 1)).any()):
            raise ValueError('external_reserve must be in [0,1]')
        reserve = torch.minimum(reserve, external_reserve)
    ceiling = (accepted_z>=max_z) | ((measured_z>=max_z) if measured_floor else torch.zeros_like(history_valid))
    base = accepted_z
    if measured_floor:
        base=torch.where((reserve>0)&~ceiling,torch.maximum(accepted_z,measured_z),accepted_z)
    lead_room = (measured_z+lead_m-base).clamp_min(0)
    remaining = torch.where(ceiling,torch.zeros_like(base),(max_z-base).clamp_min(0))
    increment = torch.minimum(rate_m_s*dt*reserve,torch.minimum(lead_room,remaining))
    code = torch.zeros_like(accepted_z,dtype=torch.long)
    code = torch.where(reserve <= 0,1,code)
    code = torch.where(lead_room <= 0,2,code)
    code = torch.where(remaining <= 0,3,code)
    return LiftStep(base+increment,increment,reserve,fz,cm,accepted_z-measured_z,code)
