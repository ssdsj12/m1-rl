"""Pure world-frame teacher references, bounded candidate search and backtracking.

Quaternions are wxyz. No phase, measured support certificate, or state commit is
performed here. A returned reference and IK always describe the same candidate;
only composite ``valid`` permits a caller to commit that candidate.
"""
from dataclasses import dataclass, fields
import math

import torch

from ame_baseline.m1_teacher_ik import IKConfig, IKResult
from ame_baseline.m1_teacher_seed_recovery import solve_pose_ik as solve_constrained_ik


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
    measured_triangle_margin_m: torch.Tensor
    candidate_count: torch.Tensor


@dataclass(frozen=True)
class ReferenceStep:
    reference: PoseReference
    ik: IKResult
    valid: torch.Tensor
    backtrack_index: torch.Tensor
    slew_ok: torch.Tensor


@dataclass(frozen=True)
class FeedbackReferenceStep:
    physical: PoseReference
    command: PoseReference
    nominal_ik: IKResult
    command_ik: IKResult
    output: torch.Tensor
    valid: torch.Tensor
    backtrack_index: torch.Tensor
    slew_ok: torch.Tensor
    execution_target: object = None


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


def _rank_load_candidates(cost, weakest, extension_margin, active_wheel, eligible):
    """Exact load priority, then nonactive knee reserve, motion cost and index."""
    support = torch.arange(4, device=cost.device)[None, None] != active_wheel[:, None, None]
    reserve = torch.where(support, extension_margin,
                          torch.full_like(extension_margin, float('inf'))).amin(-1)
    reserve = torch.where(eligible, reserve, torch.full_like(reserve, -float('inf')))
    score = torch.where(eligible, weakest, torch.full_like(weakest, -float('inf')))
    safe_cost = torch.where(eligible, cost, torch.full_like(cost, float('inf')))
    order = torch.argsort(safe_cost, dim=-1, stable=True)
    order = order.gather(1, torch.argsort(reserve.gather(1, order), dim=-1, descending=True, stable=True))
    order = order.gather(1, torch.argsort(score.gather(1, order), dim=-1, descending=True, stable=True))
    return order[:, 0]


def _bounded_attitude_quaternions(yaw):
    """Nine fixed roll/pitch choices, always in the captured heading frame."""
    if not isinstance(yaw,torch.Tensor) or yaw.ndim!=1 or yaw.dtype not in (torch.float32,torch.float64):
        raise ValueError('yaw must be a floating vector')
    pairs=[(0.,0.)]+[(r,p) for r in (-.1,0.,.1) for p in (-.1,0.,.1) if (r,p)!=(0.,0.)]
    angles=yaw.new_tensor(pairs)/2
    r,p=angles[:,0][None],angles[:,1][None];y=yaw[:,None]/2
    return torch.stack((r.cos()*p.cos()*y.cos()+r.sin()*p.sin()*y.sin(),
        r.sin()*p.cos()*y.cos()-r.cos()*p.sin()*y.sin(),
        r.cos()*p.sin()*y.cos()+r.sin()*p.cos()*y.sin(),
        r.cos()*p.cos()*y.sin()-r.sin()*p.sin()*y.cos()),-1)


def choose_support_pose(measured, anchor, accepted, com_w, wheel_anchors_w,
                        active_wheel, nominal_root_z_w, q_seed, branch_q, cfg: IKConfig,
                        *, measured_wheels_w, desired_com_xy=None,
                        tripod_total_load_n=None, tripod_min_load_n=30., bounded_attitude=False,
                        require_support=True):
    """Search 125 fixed heading-frame offsets and previous accepted pose125.

    Ordering is x outer/y middle/lowering inner. Candidate count is the number
    within the geometric envelope and origin-relative height floor, including
    duplicates, before COM/IK filtering. Grid orientation is level with anchor
    yaw; previous accepted orientation may still be returning toward level.
    The same predicted COM must pass both fixed-anchor and measured-wheel
    support triangles. Only fixed anchors form the four-leg IK targets.

    Opt-in bounded attitude repeats the125 positions for nine fixed orientations
    and retains accepted once (1126 total). Default geometry/order stays126.
    No feasible choice returns the accepted candidate as diagnostics with index=-1 and
    valid=False. Its reference and IK still correspond; caller must retain its
    prior accepted state. Predicted COM is a rigid transform of the measured
    body COM offset and cannot certify measured support.
    """
    if not isinstance(measured, BodyPose):
        raise TypeError('measured must be BodyPose')
    _check_pose_like(anchor, measured, 'anchor')
    _check_pose_like(accepted, measured, 'accepted')
    batch, pos = measured.pos_w.shape[0], measured.pos_w
    if type(bounded_attitude) is not bool:
        raise ValueError('bounded_attitude must be bool')
    if type(require_support) is not bool:
        raise ValueError('require_support must be bool')
    if tripod_total_load_n is not None:
        if desired_com_xy is not None:
            raise ValueError('tripod load ordering and desired_com_xy are mutually exclusive')
        _tensor(tripod_total_load_n, (batch,), pos, 'tripod_total_load_n')
        if (isinstance(tripod_min_load_n, bool) or not isinstance(tripod_min_load_n, (float, int))
                or not math.isfinite(tripod_min_load_n) or tripod_min_load_n <= 0):
            raise ValueError('tripod_min_load_n must be finite and positive')
    for value, shape, name in ((com_w, (batch, 3), 'com_w'),
                              (wheel_anchors_w, (batch, 4, 3), 'wheel_anchors_w'),
                              (measured_wheels_w, (batch, 4, 3), 'measured_wheels_w'),
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
    if bounded_attitude:
        grid=grid.repeat(9,1)
        candidate_quats=_bounded_attitude_quaternions(yaw).repeat_interleave(125,dim=1)
    else:
        candidate_quats=yaw_quat[:,None].expand(-1,125,-1)
    size=grid.shape[0]+1
    positions = anchor.pos_w[:, None]+torch.einsum('bij,nj->bni', heading, grid)
    positions = torch.cat((positions, accepted.pos_w[:, None]), 1)
    quats = torch.cat((candidate_quats, accepted.quat_w[:, None]), 1)
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
    envelope[:, -1] &= _pose_valid(accepted)
    if bounded_attitude:
        rotations=_rotation(quats.reshape(-1,4)).reshape(batch,size,3,3)
        candidate_yaw=torch.atan2(rotations[:,:,1,0],rotations[:,:,0,0])
        yaw_delta=candidate_yaw-yaw[:,None]
        yaw_delta=torch.atan2(yaw_delta.sin(),yaw_delta.cos())
        envelope &= (rotations[:,:,2,2]>=math.cos(.15)-eps)&(yaw_delta.abs()<=1e-5)
    count = envelope.sum(-1)
    candidate = PoseReference(BodyPose(positions.reshape(-1, 3), quats.reshape(-1, 4)),
                              wheel_anchors_w[:, None].expand(-1, size, -1, -1).reshape(-1, 4, 3))
    com_offset = torch.einsum('bij,bj->bi', _rotation(measured.quat_w).transpose(-1, -2), com_w-measured.pos_w)
    predicted = positions+torch.einsum('bnij,bj->bni', _rotation(quats.reshape(-1, 4)).reshape(batch, size, 3, 3), com_offset)
    margins, support_ok = support_margin(predicted.reshape(-1, 3), candidate.wheels_w,
                                         active_wheel[:, None].expand(-1, size).reshape(-1))
    measured_margins, measured_support_ok = support_margin(predicted.reshape(-1, 3),
        measured_wheels_w[:, None].expand(-1, size, -1, -1).reshape(-1, 4, 3),
        active_wheel[:, None].expand(-1, size).reshape(-1))
    solves = solve_constrained_ik(q_seed[:, None].expand(-1, size, -1).reshape(-1, 12),
                                  world_to_goal_body(candidate),
                                  branch_q[:, None].expand(-1, size, -1).reshape(-1, 12), cfg)
    eligible = (envelope & solves.valid.reshape(batch, size) & _pose_valid(measured)[:, None]
                & _pose_valid(accepted)[:, None])
    if require_support:
        eligible &= (support_ok.reshape(batch,size) & (margins.reshape(batch,size)>=.01)
                     & measured_support_ok.reshape(batch,size) & (measured_margins.reshape(batch,size)>=.01))
    if tripod_total_load_n is not None:
        from ame_baseline.m1_teacher_tripod_load import tripod_load
        expanded_load = tripod_total_load_n[:, None].expand(-1, size).reshape(-1)
        expanded_active = active_wheel[:, None].expand(-1, size).reshape(-1)
        anchor_load = tripod_load(predicted.reshape(-1, 3), candidate.wheels_w,
                                  expanded_active, expanded_load)
        measured_load = tripod_load(predicted.reshape(-1, 3),
            measured_wheels_w[:, None].expand(-1, size, -1, -1).reshape(-1, 4, 3),
            expanded_active, expanded_load)
        weakest = torch.minimum(anchor_load.min_load_n, measured_load.min_load_n).reshape(batch, size)
        # 45N is full lift reserve, not a candidate feasibility threshold.
        # Keep maximizing the weakest support above the strict safety floor.
        if require_support:
            eligible &= (anchor_load.valid & measured_load.valid).reshape(batch, size) & (weakest > tripod_min_load_n)
        else:
            weakest=torch.nan_to_num(weakest,nan=-1e9,posinf=-1e9,neginf=-1e9)
    cost = ((offsets-accepted_offset[:, None])/pos.new_tensor([.04, .06, .08])).square().sum(-1)
    if bounded_attitude:
        dot=(_unit(quats)*_unit(accepted.quat_w)[:,None]).sum(-1).abs().clamp(0,1)
        cost=cost+(2*torch.acos(dot)/.15).square()
    cost = torch.where(eligible, cost, torch.full_like(cost, float('inf')))
    best = cost.argmin(-1)  # First index resolves equal normalized costs.
    if tripod_total_load_n is not None:
        best = _rank_load_candidates(cost, weakest.clamp_max(45.) if bounded_attitude else weakest,
            solves.extension_margin_rad.reshape(batch, size, 4), active_wheel, eligible)
    if desired_com_xy is not None:
        _tensor(desired_com_xy, (batch, 2), pos, 'desired_com_xy')
        if not bool(torch.isfinite(desired_com_xy).all()):
            raise ValueError('desired_com_xy must be finite')
        distance = (predicted[..., :2]-desired_com_xy[:, None]).square().sum(-1)
        distance = torch.where(eligible, distance, torch.full_like(distance, float('inf')))
        # Stable secondary ordering retains original index for exact ties;
        # never trade a geometric preference for an arbitrary weighted cost.
        secondary = torch.argsort(cost, dim=-1, stable=True)
        primary = torch.argsort(distance.gather(1, secondary), dim=-1, stable=True)
        best = secondary.gather(1, primary)[:, 0]
    valid = eligible.any(-1)
    diagnostic_index = torch.where(valid, best, size-1)
    ids = torch.arange(batch, device=pos.device)*size+diagnostic_index
    reference = PoseReference(BodyPose(candidate.body.pos_w[ids], candidate.body.quat_w[ids]), candidate.wheels_w[ids])
    return PoseChoice(reference, _ik_rows(solves, ids), valid,
                       torch.where(valid, best, -1), margins[ids], measured_margins[ids], count)


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


def feedback_command(physical, output, captured_yaw, *, body_x=False):
    """Virtual body shift with fixed world wheels; body_x opts into XYZ meters."""
    c, s = captured_yaw.cos(), captured_yaw.sin()
    x = output[:,0] if body_x else torch.zeros_like(output[:,0])
    delta = torch.stack((c*x-s*output[:, 1], s*x+c*output[:, 1], output[:, 2]), -1)
    return PoseReference(BodyPose(physical.body.pos_w+delta, physical.body.quat_w), physical.wheels_w)


def backtrack_feedback_reference(accepted, requested, previous_output, proposed_output,
                                 captured_yaw, q_seed, branch_q, last_applied_q, dt,
                                 cfg: IKConfig, *, execution_valid, body_x=False,
                                 measured=None, active_wheel=None, execution_mode=None,
                                 previous_support_offset=None, proposed_support_offset=None,
                                 previous_support_reference_w_z=None, proposed_support_reference_w_z=None,
                                 previous_support_heave=None, proposed_support_heave=None,
                                 support_capture_root_z=None):
    """Eight coarse candidates plus four safe execution refinements at most.

    All changes share beta. Coarse index remains an anti-windup diagnostic;
    execution_target.fraction is the precise accepted fraction. Refinements
    never overwrite a safe point with a rejected point. The caller's validator
    must be pure. Entirely rejected rows retain the final coarse diagnostics.
    """
    if not isinstance(accepted, PoseReference) or not isinstance(requested, PoseReference):
        raise TypeError('accepted/requested must be PoseReference')
    _check_pose_like(requested.body, accepted.body, 'requested.body')
    batch, pos = accepted.body.pos_w.shape[0], accepted.body.pos_w
    for value, shape, name in ((previous_output,(batch,3),'previous_output'),
                              (proposed_output,(batch,3),'proposed_output'),
                              (captured_yaw,(batch,),'captured_yaw'),
                              (q_seed,(batch,12),'q_seed'),(branch_q,(batch,12),'branch_q'),
                              (last_applied_q,(batch,12),'last_applied_q')):
        _tensor(value, shape, pos, name)
    if isinstance(dt,bool) or not isinstance(dt,(int,float)) or not math.isfinite(dt) or dt <= 0:
        raise ValueError('dt must be finite and positive')
    if not isinstance(cfg,IKConfig) or not callable(execution_valid):
        raise TypeError('IKConfig and execution_valid callback required')
    input_ok = (_pose_valid(accepted.body) & _pose_valid(requested.body)
        & torch.isfinite(accepted.wheels_w).all(dim=(-1,-2))
        & torch.isfinite(requested.wheels_w).all(dim=(-1,-2))
        & torch.isfinite(previous_output).all(-1) & torch.isfinite(proposed_output).all(-1)
        & torch.isfinite(captured_yaw))
    chosen=torch.zeros(batch,device=pos.device,dtype=torch.bool)
    index=torch.full((batch,),-1,device=pos.device,dtype=torch.long)
    physical=command=nominal_result=command_result=output=slew_output=None
    target_output=None
    use_execution=any(x is not None for x in (measured,active_wheel,execution_mode))
    if use_execution and any(x is None for x in (measured,active_wheel,execution_mode)):
        raise ValueError('measured, active_wheel and execution_mode are required together')
    if use_execution:
        from ame_baseline.m1_teacher_execution_targets import ExecutionTarget, execution_targets
    support_feedback=previous_support_offset is not None or proposed_support_offset is not None
    if support_feedback:
        if not use_execution or previous_support_offset is None or proposed_support_offset is None:
            raise ValueError('support offsets require execution context and paired offsets')
        for offset in (previous_support_offset,proposed_support_offset):
            _tensor(offset,(batch,4),pos,'support offset')
            if (not bool(torch.isfinite(offset).all())
                    or bool((offset.abs()>.015000001).any())
                    or bool((offset.sum(-1).abs()>1e-8).any())
                    or bool((offset.gather(1,active_wheel[:,None])!=0).any())):
                raise ValueError('support offset contract')
        if bool(((proposed_support_offset-previous_support_offset).abs()>.01*dt+1e-8).any()):
            raise ValueError('support offset rate limit')
    support_height=previous_support_reference_w_z is not None or proposed_support_reference_w_z is not None
    if support_height:
        if not use_execution or previous_support_reference_w_z is None or proposed_support_reference_w_z is None:
            raise ValueError('support height requires execution context and paired history')
        if (not isinstance(execution_mode,torch.Tensor) or execution_mode.shape!=(batch,)
                or execution_mode.device!=pos.device or execution_mode.dtype!=torch.long):
            raise ValueError('execution_mode must be long [B] on reference device')
        if bool(((execution_mode!=1)&(execution_mode!=2)).any()):
            raise ValueError('support height requires LIFT/PASS or RESTORE')
        for height in (previous_support_reference_w_z,proposed_support_reference_w_z):
            _tensor(height,(batch,4),pos,'support reference world Z')
            if not bool(torch.isfinite(height).all()):
                raise ValueError('support reference world Z must be finite')
        change=(proposed_support_reference_w_z-previous_support_reference_w_z).abs()
        if bool(((execution_mode==1)[:,None] & (change!=0)).any()):
            raise ValueError('LIFT/PASS support height must remain fixed')
        if bool(((execution_mode==2)[:,None] & (change>.01*dt+1e-8)).any()):
            raise ValueError('RESTORE support height rate limit')
    if support_capture_root_z is not None:
        _tensor(support_capture_root_z,(batch,),pos,'support capture root Z')
        if not support_height or not bool(torch.isfinite(support_capture_root_z).all()):
            raise ValueError('support capture origin requires finite paired height context')
    support_heave=previous_support_heave is not None or proposed_support_heave is not None
    if support_heave:
        if not support_height or previous_support_heave is None or proposed_support_heave is None:
            raise ValueError('heave requires paired history and support height context')
        for heave in (previous_support_heave,proposed_support_heave):
            _tensor(heave,(batch,),pos,'support heave')
            if not bool(torch.isfinite(heave).all()) or bool((heave.abs()>.020000001).any()):
                raise ValueError('support heave must be finite and bounded')
        if bool(((proposed_support_heave-previous_support_heave).abs()>.02*dt+1e-8).any()):
            raise ValueError('support heave rate limit')
    def merge_ref(old,new,use):
        return PoseReference(BodyPose(torch.where(use[:,None],new.body.pos_w,old.body.pos_w),
            torch.where(use[:,None],new.body.quat_w,old.body.quat_w)),
            torch.where(use[:,None,None],new.wheels_w,old.wheels_w))
    lower=upper=eligible=None
    for attempt in range(12):
        refining=attempt>=8
        if refining:
            if not use_execution: break
            if attempt==8:
                eligible=chosen & (index>0) & (execution_mode!=0)
                if not bool(eligible.any()): break
                lower=target_output.fraction.clone()
                upper=(2*lower).clamp_max(1.)
            beta=torch.where(eligible,(lower+upper)/2,torch.ones_like(lower))
        else:
            if bool(chosen.all()): continue
            beta=pos.new_full((batch,),2.**(-attempt))
        beta_column=beta[:,None]
        quat=_slerp(accepted.body.quat_w,requested.body.quat_w,beta_column)
        invalid_quat=torch.where(_pose_valid(requested.body)[:,None],accepted.body.quat_w,requested.body.quat_w)
        phys=PoseReference(BodyPose(accepted.body.pos_w+beta_column*(requested.body.pos_w-accepted.body.pos_w),
            torch.where(input_ok[:,None],quat,invalid_quat)),
            accepted.wheels_w+beta[:,None,None]*(requested.wheels_w-accepted.wheels_w))
        u=previous_output+beta_column*(proposed_output-previous_output)
        cmd=feedback_command(phys,u,captured_yaw,body_x=body_x)
        nominal=solve_constrained_ik(q_seed,world_to_goal_body(phys),branch_q,cfg)
        target=None
        if use_execution:
            support_kwargs={}
            if support_feedback:
                # The old command already carries the old compensation. The
                # execution builder interpolates it once toward this full goal.
                support_kwargs['support_offset_w_z']=proposed_support_offset
            if support_height:
                support_kwargs['support_reference_w_z']=proposed_support_reference_w_z
            if support_capture_root_z is not None:
                support_kwargs['support_capture_root_z']=support_capture_root_z
            if support_heave:
                support_kwargs['support_heave_w_z']=proposed_support_heave
            target=execution_targets(cmd,measured,active_wheel,last_applied_q,beta,execution_mode,**support_kwargs)
            seed=torch.where((execution_mode!=0)[:,None],last_applied_q,q_seed)
            tolerance=pos.new_full((batch,4),cfg.ik_tolerance_m)
            tight=(torch.arange(4,device=pos.device)[None]==active_wheel[:,None])&(execution_mode[:,None]==1)
            if support_feedback or support_height:
                tight |= (torch.arange(4,device=pos.device)[None]!=active_wheel[:,None])&(execution_mode[:,None]!=0)
            tolerance=torch.where(tight,tolerance.clamp_max(.0001),tolerance)
            execution=solve_constrained_ik(seed,target.body_step,branch_q,cfg,tolerance_m=tolerance)
        else:
            execution=solve_constrained_ik(q_seed,world_to_goal_body(cmd),branch_q,cfg)
        slew=(torch.isfinite(last_applied_q).all(-1) & torch.isfinite(execution.q).all(-1)
            & ((execution.q-last_applied_q).abs() <= 2.5*dt).all(-1))
        executable=execution_valid(execution,u)
        if not isinstance(executable,torch.Tensor) or executable.shape != (batch,) or executable.dtype != torch.bool or executable.device != pos.device:
            raise ValueError('execution_valid must return bool [B] on reference device')
        valid=input_ok & nominal.valid & execution.valid & slew & executable
        use=eligible & valid if refining else ~chosen
        if refining:
            lower=torch.where(use,beta,lower)
            upper=torch.where(eligible & ~valid,beta,upper)
        if target is not None:
            if target_output is None:
                target_output=target
            else:
                target_output=ExecutionTarget(*(torch.where(use.reshape((-1,)+(1,)*(getattr(target,f.name).ndim-1)),
                    getattr(target,f.name),getattr(target_output,f.name)) for f in fields(ExecutionTarget)))
        if physical is None:
            physical,command,nominal_result,command_result,output,slew_output=phys,cmd,nominal,execution,u,slew
        else:
            physical,command=merge_ref(physical,phys,use),merge_ref(command,cmd,use)
            nominal_result,command_result=_merge_ik(nominal_result,nominal,use),_merge_ik(command_result,execution,use)
            output=torch.where(use[:,None],u,output); slew_output=torch.where(use,slew,slew_output)
        if not refining:
            index=torch.where(use & valid,attempt,index); chosen |= valid
    if target_output is not None:
        from .m1_teacher_active_progress import improve_active_progress
        target_output,command_result=improve_active_progress(target_output,command_result,
            last_applied_q,branch_q,active_wheel,dt,cfg,chosen,
            lambda result:execution_valid(result,output))
    step=FeedbackReferenceStep(physical,command,nominal_result,command_result,output,chosen,index,slew_output,target_output)
    if target_output is not None:
        from .m1_teacher_active_intent import improve_active_intent
        step=improve_active_intent(step,accepted,requested,measured,active_wheel,
            last_applied_q,q_seed,branch_q,dt,cfg,execution_valid)
    return step
