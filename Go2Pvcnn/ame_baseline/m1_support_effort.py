"""Quasi-static vertical-contact diagnostic; not a whole-body controller.

World-Z forces at the supplied wheel points balance floating-base gravity.
No friction, acceleration or contact moments are modeled. Floor-active minimum
norm candidates are searched; rejection is not proof that a full QP is infeasible.
Invalid rows return zero effort, never clipped commands. Callers must separately
own actuator ramp/reset and account for existing position-controller effort.
"""
import math
import torch


def vertical_support_solution(point_jacobian, gravity, support_mask,
                              effort_limits, min_force=10.):
    batch = gravity.shape[0]
    if (gravity.shape != (batch, 22)
            or point_jacobian.shape != (batch, 4, 3, 22)
            or support_mask.shape != (batch, 4)
            or effort_limits.shape != (batch, 16)):
        raise ValueError('expected M1 floating-base 6 + 16 DOFs and four contacts')
    if support_mask.dtype != torch.bool:
        raise ValueError('support_mask must be boolean')
    if not math.isfinite(min_force) or min_force <= 0:
        raise ValueError('min_force must be finite and positive')
    for value in (point_jacobian, effort_limits):
        if value.dtype != gravity.dtype or value.device != gravity.device:
            raise ValueError('floating inputs must share dtype and device')
    if support_mask.device != gravity.device or not gravity.is_floating_point():
        raise ValueError('invalid device or nonfloating dynamics')
    finite = (torch.isfinite(point_jacobian).all(dim=(1, 2, 3))
              & torch.isfinite(gravity).all(dim=1)
              & torch.isfinite(effort_limits).all(dim=1)
              & (effort_limits > 0).all(dim=1) & support_mask.any(dim=1))
    # Sanitize invalid rows before SVD; retain their invalid flag independently.
    jac = torch.where(finite[:, None, None, None], point_jacobian, 0.).double()
    g = torch.where(finite[:, None], gravity, 0.).double()
    a = jac[:, :, 2, :6].transpose(1, 2)
    floor = support_mask.double() * min_force
    rhs = g[:, :6] - (a @ floor.unsqueeze(-1)).squeeze(-1)
    best = torch.full((batch,), float('inf'), device=g.device)
    force = torch.zeros_like(floor)
    effort = torch.zeros_like(g[:, 6:])
    residual = torch.zeros_like(g[:, :6])
    for subset in range(16):
        free = torch.tensor([(subset >> i) & 1 for i in range(4)],
                            device=g.device, dtype=torch.bool) & support_mask
        matrix = a * free[:, None, :]
        delta = (torch.linalg.pinv(matrix) @ rhs.unsqueeze(-1)).squeeze(-1)
        candidate = floor + delta * free
        error = (a @ candidate.unsqueeze(-1)).squeeze(-1) - g[:, :6]
        tau = g[:, 6:] - torch.einsum('bkj,bk->bj', jac[:, :, 2, 6:], candidate)
        accepted = (finite & (candidate >= floor - 1e-7).all(dim=1)
                    & (error.abs() <= 1e-3).all(dim=1)
                    & (tau.abs() <= effort_limits).all(dim=1))
        score = candidate.square().sum(dim=1)
        take = accepted & (score < best)
        best = torch.where(take, score, best)
        force = torch.where(take[:, None], candidate, force)
        effort = torch.where(take[:, None], tau, effort)
        residual = torch.where(take[:, None], error, residual)
    return dict(valid=torch.isfinite(best), normal_force=force.to(gravity.dtype),
                effort=effort.to(gravity.dtype), base_residual=residual.to(gravity.dtype))
