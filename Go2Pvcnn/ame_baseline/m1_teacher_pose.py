"""Pure world-frame teacher references, bounded candidate search and backtracking.

Quaternions are wxyz. No phase, measured support certificate, or state commit is
performed here. A returned reference and IK always describe the same candidate;
only composite ``valid`` permits a caller to commit that candidate.
"""
from dataclasses import dataclass, fields
import math

import torch

from ame_baseline.m1_teacher_ik import IKConfig, IKResult, solve_constrained_ik


def _tensor(value, shape, like, name):
    if (not isinstance(value, torch.Tensor) or value.shape != shape
            or value.device != like.device or value.dtype != like.dtype):
        raise ValueError(f'{name} must have shape {shape} and matching device/dtype')


@dataclass(frozen=True)
class BodyPose:
    pos_w: torch.Tensor
    quat_w: torch.Tensor

    def __post_init__(self):
        if (not isinstance(self.pos_w, torch.Tensor) or self.pos_w.ndim != 2
                or self.pos_w.shape[1] != 3
                or self.pos_w.dtype not in (torch.float32, torch.float64)):
            raise ValueError('pos_w must be float32/float64 [B,3]')
        _tensor(self.quat_w, (self.pos_w.shape[0], 4), self.pos_w, 'quat_w')


@dataclass(frozen=True)
class PoseReference:
    body: BodyPose
    wheels_w: torch.Tensor

    def __post_init__(self):
        if not isinstance(self.body, BodyPose):
            raise TypeError('body must be BodyPose')
        _tensor(self.wheels_w, (self.body.pos_w.shape[0], 4, 3), self.body.pos_w, 'wheels_w')


@dataclass(frozen=True)
class PoseChoice:
    reference: PoseReference
    ik: IKResult
    valid: torch.Tensor
    candidate_index: torch.Tensor
    predicted_margin_m: torch.Tensor
    candidate_count: torch.Tensor


@dataclass(frozen=True)
class ReferenceStep:
    reference: PoseReference
    ik: IKResult
    valid: torch.Tensor
    backtrack_index: torch.Tensor
    slew_ok: torch.Tensor


def _pose_valid(body):
    return (torch.isfinite(body.pos_w).all(-1) & torch.isfinite(body.quat_w).all(-1)
            & ((body.quat_w.norm(dim=-1)-1).abs() <= 1e-3))


def _unit(quat):
    return quat / quat.norm(dim=-1, keepdim=True).clamp_min(torch.finfo(quat.dtype).tiny)


def _rotation(quat):
    w, x, y, z = _unit(quat).unbind(-1)
    return torch.stack((1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y),
                        2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x),
                        2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)), -1).reshape(-1, 3, 3)


def world_to_goal_body(reference: PoseReference):
    """R_goal.T @ (wheel_world - root_goal_world), for all four wheels.

    Invalid numeric rows retain NaN targets so the IK refuses them. Structural
    shape/device/dtype errors are contract errors, not row-level rejections.
    """
    if not isinstance(reference, PoseReference):
        raise TypeError('reference must be PoseReference')
    target = torch.einsum('bij,bkj->bki', _rotation(reference.body.quat_w).transpose(-1, -2),
                          reference.wheels_w-reference.body.pos_w[:, None])
    valid = _pose_valid(reference.body) & torch.isfinite(reference.wheels_w).all(dim=(-1, -2))
    return torch.where(valid[:, None, None], target, torch.full_like(target, float('nan')))


def support_margin(com_w, wheel_w, active_wheel):
    """Signed inward XY distance to the other three wheel-center edges.

    This is the same flat-ground projection approximation as the read-only
    support observer, independent of load and dynamic stability. Validity here
    means numeric/nondegenerate geometry, not the 10mm preparation threshold.
    """
    if (not isinstance(com_w, torch.Tensor) or com_w.ndim != 2 or com_w.shape[1] != 3
            or com_w.dtype not in (torch.float32, torch.float64)):
        raise ValueError('com_w must be float32/float64 [B,3]')
    batch = com_w.shape[0]
    _tensor(wheel_w, (batch, 4, 3), com_w, 'wheel_w')
    if (not isinstance(active_wheel, torch.Tensor) or active_wheel.shape != (batch,)
            or active_wheel.dtype != torch.long or active_wheel.device != com_w.device):
        raise ValueError('active_wheel must be long [B] on the geometry device')
    valid = (torch.isfinite(com_w).all(-1) & torch.isfinite(wheel_w).all(dim=(-1, -2))
             & (active_wheel >= 0) & (active_wheel < 4))
    table = torch.tensor([[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]], device=com_w.device)
    ids = table[active_wheel.clamp(0, 3)]
    triangle = wheel_w.gather(1, ids[..., None].expand(-1, -1, 3))[..., :2]
    edge = triangle.roll(-1, dims=1)-triangle
    relative = com_w[:, None, :2]-triangle
    ab, ac = triangle[:, 1]-triangle[:, 0], triangle[:, 2]-triangle[:, 0]
    area = ab[:, 0]*ac[:, 1]-ab[:, 1]*ac[:, 0]
    length = edge.norm(dim=-1)
    valid &= (area.abs() > 1e-10) & (length > 1e-10).all(-1)
    margin = ((edge[..., 0]*relative[..., 1]-edge[..., 1]*relative[..., 0])
              * area.sign()[:, None]/length.clamp_min(1e-12)).amin(-1)
    valid &= torch.isfinite(margin)
    return torch.where(valid, margin, torch.full_like(margin, float('nan'))), valid


def _check_pose_like(body, like, name):
    if not isinstance(body, BodyPose):
        raise TypeError(f'{name} must be BodyPose')
    _tensor(body.pos_w, like.pos_w.shape, like.pos_w, f'{name}.pos_w')
    _tensor(body.quat_w, like.quat_w.shape, like.pos_w, f'{name}.quat_w')


def _ik_rows(result, ids):
    return IKResult(*(getattr(result, field.name)[ids] for field in fields(IKResult)))


def choose_support_pose(measured, anchor, accepted, com_w, wheel_anchors_w,
                        active_wheel, nominal_root_z_w, q_seed, branch_q, cfg: IKConfig):
    """Search 125 fixed heading-frame offsets and previous accepted pose125.

    Ordering is x outer/y middle/lowering inner. Candidate count is the number
    within the geometric envelope and origin-relative height floor, including
    duplicates, before COM/IK filtering. Grid orientation is level with anchor
    yaw; previous accepted orientation may still be returning toward level.

    No feasible choice returns candidate125 as diagnostics with index=-1 and
    valid=False. Its reference and IK still correspond; caller must retain its
    prior accepted state. Predicted COM is a rigid transform of the measured
    body COM offset and cannot certify measured support.
    """
    if not isinstance(measured, BodyPose):
        raise TypeError('measured must be BodyPose')
    _check_pose_like(anchor, measured, 'anchor')
    _check_pose_like(accepted, measured, 'accepted')
    batch, pos = measured.pos_w.shape[0], measured.pos_w
    for value, shape, name in ((com_w, (batch, 3), 'com_w'),
                              (wheel_anchors_w, (batch, 4, 3), 'wheel_anchors_w'),
                              (nominal_root_z_w, (batch,), 'nominal_root_z_w'),
                              (q_seed, (batch, 12), 'q_seed'), (branch_q, (batch, 12), 'branch_q')):
        _tensor(value, shape, pos, name)
    # Also enforces the active-wheel contract before candidate expansion.
    support_margin(com_w, wheel_anchors_w, active_wheel)
    if not isinstance(cfg, IKConfig):
        raise TypeError('cfg must be IKConfig')
    w, x, y, z = _unit(anchor.quat_w).unbind(-1)
    yaw = torch.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
    yaw_quat = torch.stack((torch.cos(yaw/2), torch.zeros_like(yaw),
                            torch.zeros_like(yaw), torch.sin(yaw/2)), -1)
    heading = _rotation(yaw_quat)
    grid = torch.stack(torch.meshgrid(pos.new_tensor([-.04, -.02, 0., .02, .04]),
                                     pos.new_tensor([-.06, -.03, 0., .03, .06]),
                                     pos.new_tensor([0., -.02, -.04, -.06, -.08]), indexing='ij'), -1).reshape(125, 3)
    positions = anchor.pos_w[:, None]+torch.einsum('bij,nj->bni', heading, grid)
    positions = torch.cat((positions, accepted.pos_w[:, None]), 1)
    quats = torch.cat((yaw_quat[:, None].expand(-1, 125, -1), accepted.quat_w[:, None]), 1)
    accepted_offset = torch.einsum('bij,bj->bi', heading.transpose(-1, -2), accepted.pos_w-anchor.pos_w)
    offsets = torch.cat((grid[None].expand(batch, -1, -1), accepted_offset[:, None]), 1)
    # Only floating roundoff at the exact envelope/floor boundary, not a
    # physical expansion of the approved 4/6/8cm bounds.
    eps = torch.finfo(pos.dtype).eps*8
    floor_offset = nominal_root_z_w-anchor.pos_w[:, 2]-.08
    envelope = ((offsets[..., 0].abs() <= .04+eps) & (offsets[..., 1].abs() <= .06+eps)
                & (offsets[..., 2] >= -.08-eps) & (offsets[..., 2] <= eps)
                & (offsets[..., 2] >= floor_offset[:, None]-eps)
                & torch.isfinite(nominal_root_z_w)[:, None] & _pose_valid(anchor)[:, None])
    envelope[:, 125] &= _pose_valid(accepted)
    count = envelope.sum(-1)
    candidate = PoseReference(BodyPose(positions.reshape(-1, 3), quats.reshape(-1, 4)),
                              wheel_anchors_w[:, None].expand(-1, 126, -1, -1).reshape(-1, 4, 3))
    com_offset = torch.einsum('bij,bj->bi', _rotation(measured.quat_w).transpose(-1, -2), com_w-measured.pos_w)
    predicted = positions+torch.einsum('bnij,bj->bni', _rotation(quats.reshape(-1, 4)).reshape(batch, 126, 3, 3), com_offset)
    margins, support_ok = support_margin(predicted.reshape(-1, 3), candidate.wheels_w,
                                         active_wheel[:, None].expand(-1, 126).reshape(-1))
    solves = solve_constrained_ik(q_seed[:, None].expand(-1, 126, -1).reshape(-1, 12),
                                  world_to_goal_body(candidate),
                                  branch_q[:, None].expand(-1, 126, -1).reshape(-1, 12), cfg)
    eligible = (envelope & support_ok.reshape(batch, 126) & (margins.reshape(batch, 126) >= .01)
                & solves.valid.reshape(batch, 126) & _pose_valid(measured)[:, None]
                & _pose_valid(accepted)[:, None])
    cost = ((offsets-accepted_offset[:, None])/pos.new_tensor([.04, .06, .08])).square().sum(-1)
    cost = torch.where(eligible, cost, torch.full_like(cost, float('inf')))
    best = cost.argmin(-1)  # First index resolves equal normalized costs.
    valid = eligible.any(-1)
    diagnostic_index = torch.where(valid, best, 125)
    ids = torch.arange(batch, device=pos.device)*126+diagnostic_index
    reference = PoseReference(BodyPose(candidate.body.pos_w[ids], candidate.body.quat_w[ids]), candidate.wheels_w[ids])
    return PoseChoice(reference, _ik_rows(solves, ids), valid,
                       torch.where(valid, best, -1), margins[ids], count)


def _slerp(start, end, alpha):
    start, end = _unit(start), _unit(end)
    dot = (start*end).sum(-1, keepdim=True)
    end = torch.where(dot < 0, -end, end)
    dot = dot.abs().clamp(max=1)
    theta = torch.acos(dot)
    sin_theta = torch.sin(theta).clamp_min(torch.finfo(start.dtype).eps)
    arc = (torch.sin((1-alpha)*theta)*start+torch.sin(alpha*theta)*end)/sin_theta
    linear = (1-alpha)*start+alpha*end
    return _unit(torch.where(dot > 1-1e-6, linear, arc))


def _merge_ik(previous, current, use):
    return IKResult(*(torch.where(use.reshape((-1,)+(1,)*(getattr(current, f.name).ndim-1)),
                                   getattr(current, f.name), getattr(previous, f.name))
                       for f in fields(IKResult)))


def backtrack_reference(accepted, requested, q_seed, branch_q, last_applied_q, dt, cfg: IKConfig):
    """Try fractions1..1/128, rebuilding world targets and solving every time.

    The first valid all-leg solve within 2.5rad/s of actual last applied joints
    wins per row. No joints are clipped. A refused row returns its final1/128
    candidate with matching IK diagnostics and index=-1. Composite valid=False
    means the caller must freeze its accepted reference/progress/state.
    """
    if not isinstance(accepted, PoseReference) or not isinstance(requested, PoseReference):
        raise TypeError('accepted/requested must be PoseReference')
    _check_pose_like(requested.body, accepted.body, 'requested.body')
    batch, pos = accepted.body.pos_w.shape[0], accepted.body.pos_w
    for value, name in ((q_seed, 'q_seed'), (branch_q, 'branch_q'), (last_applied_q, 'last_applied_q')):
        _tensor(value, (batch, 12), pos, name)
    if isinstance(dt, bool) or not isinstance(dt, (int, float)) or not math.isfinite(dt) or dt <= 0:
        raise ValueError('dt must be finite and positive')
    if not isinstance(cfg, IKConfig):
        raise TypeError('cfg must be IKConfig')
    input_ok = (_pose_valid(accepted.body) & _pose_valid(requested.body)
                & torch.isfinite(accepted.wheels_w).all(dim=(-1, -2))
                & torch.isfinite(requested.wheels_w).all(dim=(-1, -2)))
    chosen = torch.zeros(batch, device=pos.device, dtype=torch.bool)
    index = torch.full((batch,), -1, device=pos.device, dtype=torch.long)
    output = result = slew_output = None
    for attempt in range(8):
        alpha = 2.**(-attempt)
        interpolated_quat = _slerp(accepted.body.quat_w, requested.body.quat_w, alpha)
        # Keep the offending raw quaternion on an invalid input row. Merely
        # normalizing it would make returned reference geometry disagree with
        # the refused IK target, and hide the original measurement failure.
        invalid_quat = torch.where(_pose_valid(requested.body)[:, None],
                                   accepted.body.quat_w, requested.body.quat_w)
        reference = PoseReference(BodyPose(accepted.body.pos_w+alpha*(requested.body.pos_w-accepted.body.pos_w),
                                           torch.where(input_ok[:, None], interpolated_quat, invalid_quat)),
                                   accepted.wheels_w+alpha*(requested.wheels_w-accepted.wheels_w))
        target = world_to_goal_body(reference)
        solved = solve_constrained_ik(q_seed, target, branch_q, cfg)
        slew = (torch.isfinite(last_applied_q).all(-1)
                & torch.isfinite(solved.q).all(-1) & ((solved.q-last_applied_q).abs() <= 2.5*dt).all(-1))
        valid = input_ok & solved.valid & slew
        use = ~chosen
        if output is None:
            output, result, slew_output = reference, solved, slew
        else:
            output = PoseReference(BodyPose(torch.where(use[:, None], reference.body.pos_w, output.body.pos_w),
                                            torch.where(use[:, None], reference.body.quat_w, output.body.quat_w)),
                                    torch.where(use[:, None, None], reference.wheels_w, output.wheels_w))
            result, slew_output = _merge_ik(result, solved, use), torch.where(use, slew, slew_output)
        index = torch.where(use & valid, attempt, index)
        chosen |= valid
        if bool(chosen.all()):
            break
    return ReferenceStep(output, result, chosen, index, slew_output)
