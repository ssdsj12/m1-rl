"""Pure body-frame numerical IK and per-leg rejection evidence."""
from dataclasses import dataclass
from enum import IntEnum
import math

import torch

from extension.parallelism.m1_kinematics import (
    M1_PLANNER_JOINT_NAMES, m1_fk, m1_joint_limit_mask,
)


class IKReason(IntEnum):
    OK = 0
    NONFINITE = 1
    JOINT_LIMIT = 2
    BRANCH = 3
    NEAR_STRAIGHT = 4
    WORKSPACE = 5
    RESIDUAL = 6


@dataclass(frozen=True)
class IKConfig:
    damping: float = .05
    fd_epsilon: float = 1e-4
    dq_component_limit_rad: float = .25
    ik_iterations: int = 32
    ik_tolerance_m: float = .002
    min_knee_abs_rad: float = .10

    def __post_init__(self):
        for name in ('damping', 'fd_epsilon', 'dq_component_limit_rad',
                     'ik_tolerance_m', 'min_knee_abs_rad'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be finite and positive')
        if self.damping != .05 or self.fd_epsilon != 1e-4:
            raise ValueError('damping and fd_epsilon are fixed at .05 and 1e-4')
        if type(self.ik_iterations) is not int or not 1 <= self.ik_iterations <= 32:
            raise ValueError('ik_iterations must be an integer in [1,32]')
        if self.dq_component_limit_rad > .25 or self.ik_tolerance_m > .002 or self.min_knee_abs_rad < .10:
            raise ValueError('IK step/residual/near-straight bounds may only be tightened')


@dataclass(frozen=True)
class IKResult:
    q: torch.Tensor
    valid: torch.Tensor
    residual_m: torch.Tensor
    joint_limit_ok: torch.Tensor
    branch_ok: torch.Tensor
    extension_margin_rad: torch.Tensor
    workspace_ok: torch.Tensor
    iterations: torch.Tensor
    reason: torch.Tensor


def body_feet(q):
    zero = q.new_zeros((*q.shape[:-1], 3))
    return m1_fk(zero, zero, q, capsule_samples=1).foot_pos_w


def body_jacobian(q, epsilon=1e-4):
    """Central differences at body origin: no world-position subtraction."""
    perturbations = []
    for joint in range(3):
        delta = torch.zeros_like(q)
        ids = [M1_PLANNER_JOINT_NAMES.index(f'{prefix}_{name}_JOINT')
               for prefix in ('FBL', 'FAR', 'RBL', 'RAR')
               for name in (('ABAD', 'HIP', 'KNEE')[joint],)]
        delta[:, ids] = epsilon
        perturbations.extend((q + delta, q - delta))
    feet = body_feet(torch.cat(perturbations, 0)).split(q.shape[0])
    return torch.stack([(feet[2*j] - feet[2*j+1]) / (2*epsilon) for j in range(3)], -1)


def dls_step(jacobian, error, damping=.05, component_limit=.25):
    eye = torch.eye(3, device=jacobian.device, dtype=jacobian.dtype)
    solved = torch.linalg.solve(jacobian @ jacobian.transpose(-1, -2) + damping**2*eye,
                                error.unsqueeze(-1))
    return (jacobian.transpose(-1, -2) @ solved).squeeze(-1).clamp(-component_limit, component_limit)


def _workspace_mask(target_b):
    """Exact unconstrained positional workspace of the existing FK chain.

    ABAD rotates Y/Z about its mount; every hip/knee Y offset is invariant
    under the subsequent Y rotations. Removing that fixed lateral offset
    gives the two planar link reach. Derive mounts and link lengths from FK
    rather than comparing a wheel's root radius with the planar link sum.
    Joint and knee-branch constraints are checked separately by the solver.
    """
    zero = target_b.new_zeros(1, 3)
    geometry = m1_fk(zero, zero, target_b.new_zeros(1, 12), capsule_samples=1)
    mount = geometry.thigh_pos_w
    hip_offset = geometry.hip_pos_w - mount
    thigh = geometry.knee_pos_w - geometry.hip_pos_w
    calf = geometry.foot_pos_w - geometry.knee_pos_w
    lateral = hip_offset[..., 1] + thigh[..., 1] + calf[..., 1]
    relative = target_b - mount
    yz_planar_sq = relative[..., 1:].square().sum(-1) - lateral.square()
    planar_x = relative[..., 0] - hip_offset[..., 0]
    reach_sq = planar_x.square() + yz_planar_sq
    thigh_length = thigh[..., (0, 2)].norm(dim=-1)
    calf_length = calf[..., (0, 2)].norm(dim=-1)
    # Roundoff only: no physical workspace or residual tolerance expansion.
    roundoff = torch.finfo(target_b.dtype).eps * 8
    return (torch.isfinite(target_b).all(-1) & (yz_planar_sq >= -roundoff)
            & (reach_sq >= (thigh_length - calf_length).square() - roundoff)
            & (reach_sq <= (thigh_length + calf_length).square() + roundoff))


def solve_constrained_ik(q_seed, target_b, branch_q, cfg=None, *, tolerance_m=None):
    """At most 32 DLS attempts per leg, accepting only legal improving steps.

    Invalid inputs freeze that leg. A failed solve returns its last accepted
    iterate and explicit evidence, never a clipped solution or valid label.
    NONFINITE inputs are sanitized solely to keep numerical batch operations
    isolated; their residual is inf and their reason remains NONFINITE.
    iterations counts attempted updates (including rejected proposals).
    """
    cfg = cfg or IKConfig()
    if not isinstance(cfg, IKConfig):
        raise TypeError('cfg must be IKConfig')
    if q_seed.ndim != 2 or q_seed.shape[1] != 12 or target_b.shape != (q_seed.shape[0], 4, 3) or branch_q.shape != q_seed.shape:
        raise ValueError('q_seed/target_b/branch_q must be [B,12]/[B,4,3]/[B,12]')
    if q_seed.dtype not in (torch.float32, torch.float64):
        raise ValueError('IK requires float32 or float64 tensors')
    if any(t.device != q_seed.device or t.dtype != q_seed.dtype for t in (target_b, branch_q)):
        raise ValueError('IK tensors must have the same device and dtype')
    batch = q_seed.shape[0]
    if tolerance_m is None:
        tolerance_m = q_seed.new_full((batch, 4), cfg.ik_tolerance_m)
    elif (not isinstance(tolerance_m, torch.Tensor)
          or tolerance_m.shape != (batch, 4)
          or tolerance_m.dtype != q_seed.dtype or tolerance_m.device != q_seed.device
          or not bool(torch.isfinite(tolerance_m).all())
          or bool(((tolerance_m <= 0) | (tolerance_m > cfg.ik_tolerance_m)).any())):
        raise ValueError('tolerance_m must be matching finite positive [B,4], no looser than config')
    leg_ids = torch.arange(4, device=q_seed.device)

    def limits(value):
        return m1_joint_limit_mask(value.reshape(batch, 4, 3), leg_ids)

    def branch(value):
        return (value[:, 2::3].sign() == branch_q[:, 2::3].sign()) & (branch_q[:, 2::3] != 0)

    finite = (torch.isfinite(q_seed.reshape(batch, 4, 3)).all(-1)
              & torch.isfinite(target_b).all(-1)
              & torch.isfinite(branch_q.reshape(batch, 4, 3)).all(-1))
    # Nonfinite rows remain invalid; zero is an operation placeholder only.
    q = torch.where(torch.isfinite(q_seed), q_seed, torch.zeros_like(q_seed)).clone()
    target = torch.where(finite[..., None], target_b, body_feet(q))
    workspace_ok = finite & _workspace_mask(target)
    seed_limits = limits(q)
    seed_branch = branch(q)
    seed_extension = q[:, 2::3].abs() >= cfg.min_knee_abs_rad
    eligible = finite & workspace_ok & seed_limits & seed_branch & seed_extension
    iterations = torch.zeros((batch, 4), device=q.device, dtype=torch.long)
    error = target - body_feet(q)
    residual = error.norm(dim=-1)
    for _ in range(cfg.ik_iterations):
        active = eligible & (residual > tolerance_m)
        if not bool(active.any()):
            break
        iterations += active.long()
        jacobian = body_jacobian(q, cfg.fd_epsilon)
        dq = dls_step(jacobian,
                      torch.where(active[..., None], error, torch.zeros_like(error)),
                      cfg.damping, cfg.dq_component_limit_rad)
        proposal = q + dq.flatten(1)
        proposal_finite = torch.isfinite(proposal.reshape(batch, 4, 3)).all(-1)
        # Constrain the optimization candidate, not the returned solution.
        # Rejecting the entire leg at this boundary also discards legal
        # ABAD/HIP tangent progress. Full legality and improvement still gate it.
        knee_sign = branch_q[:, 2::3].sign()
        knee_crossed = knee_sign * proposal[:, 2::3] < cfg.min_knee_abs_rad
        proposal[:, 2::3] = knee_sign * torch.maximum(
            knee_sign * proposal[:, 2::3],
            torch.full_like(proposal[:, 2::3], cfg.min_knee_abs_rad))
        legal = (proposal_finite & torch.isfinite(proposal.reshape(batch, 4, 3)).all(-1)
                 & limits(proposal) & branch(proposal)
                 & (proposal[:, 2::3].abs() >= cfg.min_knee_abs_rad))
        # Evaluate only admissible proposed joints: invalid proposals hold.
        admissible = torch.where((active & legal)[..., None],
                                  proposal.reshape(batch, 4, 3), q.reshape(batch, 4, 3)).flatten(1)
        proposed_error = target - body_feet(admissible)
        proposed_residual = proposed_error.norm(dim=-1)
        tangent_eligible = active & proposal_finite & knee_crossed
        if bool(tangent_eligible.any()):
            # A clipped full DLS direction is not the constrained optimum.
            # Account for the legal knee step, then solve its remaining error
            # using only the free ABAD/HIP directions in this same iteration.
            knee_step = proposal[:, 2::3] - q[:, 2::3]
            remaining_error = error - jacobian[..., 2] * knee_step[..., None]
            tangent = q.reshape(batch, 4, 3).clone()
            tangent[..., :2] += dls_step(jacobian[..., :2], remaining_error,
                                        cfg.damping, cfg.dq_component_limit_rad)
            tangent[..., 2] = proposal[:, 2::3]
            tangent = tangent.flatten(1)
            tangent_legal = (tangent_eligible
                             & torch.isfinite(tangent.reshape(batch, 4, 3)).all(-1)
                             & limits(tangent) & branch(tangent)
                             & (tangent[:, 2::3].abs() >= cfg.min_knee_abs_rad))
            tangent = torch.where(tangent_legal[..., None],
                                  tangent.reshape(batch, 4, 3), q.reshape(batch, 4, 3)).flatten(1)
            tangent_error = target - body_feet(tangent)
            tangent_residual = tangent_error.norm(dim=-1)
            take_tangent = tangent_legal & (tangent_residual < proposed_residual)
            admissible = torch.where(take_tangent[..., None], tangent.reshape(batch, 4, 3),
                                     admissible.reshape(batch, 4, 3)).flatten(1)
            proposed_error = torch.where(take_tangent[..., None], tangent_error, proposed_error)
            proposed_residual = torch.where(take_tangent, tangent_residual, proposed_residual)
            legal = legal | take_tangent
        accept = active & legal & (proposed_residual < residual)
        q = torch.where(accept[..., None], admissible.reshape(batch, 4, 3), q.reshape(batch, 4, 3)).flatten(1)
        error = torch.where(accept[..., None], proposed_error, error)
        residual = torch.where(accept, proposed_residual, residual)
    joint_ok = finite & limits(q)
    branch_ok = finite & branch(q)
    # Diagnostic margin is always relative to the approved .10rad boundary,
    # even if a caller opts for a stricter configured guard.
    extension_margin = q[:, 2::3].abs() - .10
    extension_margin = torch.where(finite, extension_margin, torch.full_like(extension_margin, float('nan')))
    residual = torch.where(finite, residual, torch.full_like(residual, float('inf')))
    # Stable precedence. Every per-leg flag still records its own check.
    reason = torch.full((batch, 4), int(IKReason.OK), device=q.device, dtype=torch.long)
    for check, code in ((residual <= tolerance_m, IKReason.RESIDUAL),
                        (workspace_ok, IKReason.WORKSPACE),
                        (q[:, 2::3].abs() >= cfg.min_knee_abs_rad, IKReason.NEAR_STRAIGHT),
                        (branch_ok, IKReason.BRANCH),
                        (joint_ok, IKReason.JOINT_LIMIT),
                        (finite, IKReason.NONFINITE)):
        reason = torch.where(check, reason, int(code))
    return IKResult(q, (reason == int(IKReason.OK)).all(-1), residual,
                    joint_ok, branch_ok, extension_margin, workspace_ok,
                    iterations, reason)
