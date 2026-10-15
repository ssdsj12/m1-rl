"""Pure bounded teacher position feedback, with no IK or state commits.

All [B,3] columns are heading X/Y/Z. Legacy FeedbackConfig has X in m/s
and Y/Z in m; BodyFeedbackConfig uses meters on all three axes. Wheel
ordering and total motor-speed limits belong to the caller's transaction.
"""
from dataclasses import dataclass, fields
import math

import torch


def _vector(value, name):
    if (not isinstance(value, torch.Tensor) or value.ndim != 2
            or value.shape[1] != 3 or value.dtype not in (torch.float32, torch.float64)):
        raise ValueError(f'{name} must be float32/float64 [B,3]')
    if value.device.type == 'meta' or not bool(torch.isfinite(value).all()):
        raise ValueError(f'{name} must be finite and materialized')


def _tensor(value, shape, like, name, *, boolean=False):
    dtype = torch.bool if boolean else like.dtype
    if (not isinstance(value, torch.Tensor) or value.shape != shape
            or value.device != like.device or value.dtype != dtype):
        raise ValueError(f'{name} must have shape {shape} and matching device/dtype')
    if not boolean and not bool(torch.isfinite(value).all()):
        raise ValueError(f'{name} must be finite')


@dataclass(frozen=True)
class FeedbackConfig:
    """Approved candidate constants; changing these needs a new design."""
    kp_x: float = 1.
    ki_x: float = .2
    integral_limit_x: float = .02
    output_limit_x: float = .04
    slew_rate_x: float = .10
    kp_yz: float = .5
    ki_yz: float = .5
    integral_limit_yz: float = .01
    output_limit_yz: float = .02
    slew_rate_yz: float = .02

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value != field.default):
                raise ValueError(f'{field.name} must equal fixed finite value {field.default}')


@dataclass(frozen=True)
class BodyFeedbackConfig(FeedbackConfig):
    """XYZ are body displacements in meters; wheel speeds are a separate command."""
    kp_x: float = .5
    ki_x: float = .5
    integral_limit_x: float = .01
    output_limit_x: float = .02
    slew_rate_x: float = .02


@dataclass(frozen=True)
class FeedbackState:
    integral: torch.Tensor
    output: torch.Tensor

    def __post_init__(self):
        _vector(self.integral, 'integral')
        _tensor(self.output, self.integral.shape, self.integral, 'output')


@dataclass(frozen=True)
class FeedbackProposal:
    error_h: torch.Tensor
    integral_candidate: torch.Tensor
    raw_output: torch.Tensor
    output: torch.Tensor
    limited: torch.Tensor

    def __post_init__(self):
        _vector(self.error_h, 'error_h')
        for name in ('integral_candidate', 'raw_output', 'output'):
            _tensor(getattr(self, name), self.error_h.shape, self.error_h, name)
        _tensor(self.limited, self.error_h.shape, self.error_h, 'limited', boolean=True)


def _axis_values(like, x, yz):
    return like.new_tensor([x, yz, yz])


def _validate_step(error_h, previous, dt, cfg, active):
    _vector(error_h, 'error_h')
    if not isinstance(previous, FeedbackState):
        raise TypeError('previous must be FeedbackState')
    previous.__post_init__()
    _tensor(previous.integral, error_h.shape, error_h, 'previous.integral')
    _tensor(previous.output, error_h.shape, error_h, 'previous.output')
    if not isinstance(cfg, FeedbackConfig):
        raise TypeError('cfg must be FeedbackConfig')
    cfg.__post_init__()
    _tensor(dt, (error_h.shape[0],), error_h, 'dt')
    if not bool((dt > 0).all()):
        raise ValueError('dt must be strictly positive')
    _tensor(active, (error_h.shape[0],), error_h, 'active', boolean=True)
    integral_limit = _axis_values(error_h, cfg.integral_limit_x, cfg.integral_limit_yz)
    output_limit = _axis_values(error_h, cfg.output_limit_x, cfg.output_limit_yz)
    if (bool((previous.integral.abs() > integral_limit).any())
            or bool((previous.output.abs() > output_limit).any())):
        raise ValueError('previous feedback state exceeds approved bounds')


def _bounded_proposal(error_h, previous, dt, cfg, active, integral, integral_limited):
    kp = _axis_values(error_h, cfg.kp_x, cfg.kp_yz)
    limit = _axis_values(error_h, cfg.output_limit_x, cfg.output_limit_yz)
    slew = dt[:, None] * _axis_values(error_h, cfg.slew_rate_x, cfg.slew_rate_yz)
    integral = torch.where(active[:, None], integral, torch.zeros_like(integral))
    raw = torch.where(active[:, None], kp * error_h + integral, torch.zeros_like(error_h))
    bounded = torch.clamp(raw, min=-limit, max=limit)
    output = previous.output + torch.clamp(bounded - previous.output, min=-slew, max=slew)
    limited = (integral_limited & active[:, None]) | (raw != bounded) | (bounded != output)
    return FeedbackProposal(error_h.clone(), integral.clone(), raw, output, limited)


def propose_feedback(root_ref_w, root_meas_w, captured_yaw, previous: FeedbackState,
                     dt, cfg: FeedbackConfig, *, active) -> FeedbackProposal:
    """Integrate once, then independently bound integral, amplitude and slew.

    Inactive rows only clear the integral candidate and slew the old output
    toward zero; they never apply position PI. Inputs are never mutated.
    """
    _vector(root_ref_w, 'root_ref_w')
    _tensor(root_meas_w, root_ref_w.shape, root_ref_w, 'root_meas_w')
    _tensor(captured_yaw, (root_ref_w.shape[0],), root_ref_w, 'captured_yaw')
    delta = root_ref_w - root_meas_w
    c, s = captured_yaw.cos(), captured_yaw.sin()
    error_h = torch.stack((c * delta[:, 0] + s * delta[:, 1],
                           -s * delta[:, 0] + c * delta[:, 1], delta[:, 2]), -1)
    _validate_step(error_h, previous, dt, cfg, active)
    ki = _axis_values(error_h, cfg.ki_x, cfg.ki_yz)
    limit = _axis_values(error_h, cfg.integral_limit_x, cfg.integral_limit_yz)
    active_error = torch.where(active[:, None], error_h, torch.zeros_like(error_h))
    candidate = previous.integral + ki * active_error * dt[:, None]
    if not bool(torch.isfinite(candidate).all()):
        raise ValueError('integral candidate must be finite')
    bounded = torch.clamp(candidate, min=-limit, max=limit)
    return _bounded_proposal(error_h, previous, dt, cfg, active, bounded, candidate != bounded)


def recompute_feedback(error_h, previous: FeedbackState, dt, cfg: FeedbackConfig,
                       *, active, integral) -> FeedbackProposal:
    """Recompute from a selected fixed integral without accumulating again.

    Pass the first proposal's error_h and select_integral's result. The caller
    owns the one-recompute/two-transaction-pass budget. Inactive rows still
    clear the candidate. No rejected history is added to the supplied integral.
    """
    _validate_step(error_h, previous, dt, cfg, active)
    _tensor(integral, error_h.shape, error_h, 'integral')
    limit = _axis_values(error_h, cfg.integral_limit_x, cfg.integral_limit_yz)
    if bool((integral.abs() > limit).any()):
        raise ValueError('fixed integral exceeds approved bounds')
    return _bounded_proposal(error_h, previous, dt, cfg, active, integral,
                             torch.zeros_like(error_h, dtype=torch.bool))


def select_integral(previous: FeedbackState, proposal: FeedbackProposal, *, safe,
                    transaction_valid, backtracked, cfg=None) -> torch.Tensor:
    """Choose integral only; normal updates require an entirely unlimited row.

    Any axis limitation or transaction backtrack freezes normal integration
    on every axis. A limited axis may strictly reduce |I|, including after a
    backtrack, only when safe and transaction_valid. Total wheel-speed limiting
    must be supplied by the caller in proposal.limited before this selection.
    """
    if not isinstance(previous, FeedbackState) or not isinstance(proposal, FeedbackProposal):
        raise TypeError('previous/proposal must be FeedbackState/FeedbackProposal')
    previous.__post_init__()
    proposal.__post_init__()
    _tensor(proposal.error_h, previous.integral.shape, previous.integral, 'proposal.error_h')
    cfg=FeedbackConfig() if cfg is None else cfg
    if not isinstance(cfg,FeedbackConfig):
        raise TypeError('cfg must be FeedbackConfig')
    cfg.__post_init__()
    integral_limit=_axis_values(previous.integral,cfg.integral_limit_x,cfg.integral_limit_yz)
    output_limit=_axis_values(previous.integral,cfg.output_limit_x,cfg.output_limit_yz)
    for value,limit in ((previous.integral,integral_limit),(proposal.integral_candidate,integral_limit),
                        (previous.output,output_limit),(proposal.output,output_limit)):
        if bool((value.abs()>limit).any()):
            raise ValueError('integral selection state/proposal exceeds approved bounds')
    for name, value in (('safe', safe), ('transaction_valid', transaction_valid), ('backtracked', backtracked)):
        _tensor(value, (previous.integral.shape[0],), previous.integral, name, boolean=True)
    normal = (~backtracked & ~proposal.limited.any(dim=-1))[:, None]
    unwind = proposal.limited & (proposal.integral_candidate.abs() < previous.integral.abs())
    accept = (safe & transaction_valid)[:, None] & (normal | unwind)
    return torch.where(accept, proposal.integral_candidate, previous.integral).clone()
