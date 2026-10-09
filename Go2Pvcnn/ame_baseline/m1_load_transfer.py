"""Bounded flat-ground PREPARE proposal using frozen wheel anchors and M1 IK.

This is not a contact controller. Caller owns frozen stage-entry data, measured
contact/identity checks, timeouts and recovery. Invalid proposals MUST NOT advance
the state machine. A returned previous command is not proof of safe recovery.
"""
import math
import torch
from extension.parallelism.m1_kinematics import m1_ik, m1_joint_limit_mask


def _nearest_halfplane_point(inward, required):
    """Minimum-norm displacement satisfying three inward halfplanes."""
    batch = inward.shape[0]
    valid = torch.ones(batch, dtype=torch.bool, device=inward.device)
    candidates, candidate_ok = [torch.zeros_like(inward[:, 0])], [valid]
    for i in range(3):
        candidates.append(inward[:, i] * required[:, i, None])
        candidate_ok.append(valid)
    for i, j in ((0, 1), (0, 2), (1, 2)):
        a, b = inward[:, i], inward[:, j]
        det = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
        denominator = torch.where(det.abs() > 1e-10, det, torch.ones_like(det))
        x = (required[:, i] * b[:, 1] - a[:, 1] * required[:, j]) / denominator
        y = (a[:, 0] * required[:, j] - required[:, i] * b[:, 0]) / denominator
        candidates.append(torch.stack((x, y), dim=-1))
        candidate_ok.append(det.abs() > 1e-10)
    candidates = torch.stack(candidates, dim=1)
    satisfied = ((candidates[:, :, None] * inward[:, None]).sum(-1)
                 >= required[:, None] - 1e-7).all(-1)
    satisfied &= torch.stack(candidate_ok, dim=1) & torch.isfinite(candidates).all(-1)
    cost = torch.where(satisfied, candidates.square().sum(-1), torch.inf)
    best = cost.argmin(-1)
    return candidates[torch.arange(batch, device=inward.device), best], satisfied.any(-1)


def transfer_target(*, entry_root, entry_rpy, anchor_w, support_w, live_root, live_com,
                    selected_leg, previous_root, previous_joint, dt, root_speed=.02,
                    max_root_shift=.06, wheel_force=None, total_weight=None, support_floor=30.):
    """Propose bounded horizontal shift, <=.5rad/s joints; default .06m entry bound.

    Aim toward .03m projected COM margin until the measured .02m gate margin
    is reached, then hold for temporal readiness confirmation. Root height and RPY
    stay at stage entry. If the soft target exceeds the entry bound, first check
    the minimum-entry-displacement hard .02m solution under the same COM model.
    Reasons: 0 usable, 1 invalid data, 2 triangle infeasible,
    3 required displacement exceeds bound, 4 IK/limits, 5 joint slew,
    6 insufficient measured supporting load/contact.
    Optional wheel_force adds a quasi-static support_floor proposal with total
    supporting load conserved; the physical response is unproven. Omission
    preserves the geometric-only interface used by PREPARE.
    The COM translation model is a proposal only; measured readiness must verify it.
    Optional total_weight [B] in N adds hypothetical post-lift30N support floors
    through barycentric halfplanes; soft target35N. Flat quasi-static model only.
    This option is separate from measured four-contact force redistribution.
    support_floor accepts a scalar or floating [B] tensor, each in [30,40] N,
    so a constrained front-lift row need not inherit a rear-lift reserve.
    """
    if not math.isfinite(dt) or not 0 < dt <= .1:
        raise ValueError('dt must be finite in (0, .1] seconds')
    if not math.isfinite(root_speed) or not 0 < root_speed <= .04:
        raise ValueError('root_speed must be finite in (0, .04] m/s')
    if not math.isfinite(max_root_shift) or not 0 < max_root_shift <= .08:
        raise ValueError('max_root_shift must be finite in (0, .08] m')
    batch = entry_root.shape[0]
    if torch.is_tensor(support_floor):
        if support_floor.shape!=(batch,) or support_floor.device!=entry_root.device or not support_floor.is_floating_point():
            raise ValueError('support_floor tensor must be floating [B] on input device')
        reserve=support_floor.to(entry_root.dtype)
    else:
        reserve=torch.full((batch,),float(support_floor),device=entry_root.device,dtype=entry_root.dtype)
    if not (torch.isfinite(reserve)&(reserve>=30.)&(reserve<=40.)).all():
        raise ValueError('support_floor must be in [30,40] N')
    if total_weight is not None and wheel_force is not None:
        raise ValueError('test post-lift model separately from measured force feedback')
    values = [(entry_root, (batch, 3)), (entry_rpy, (batch, 3)),
              (support_w, (batch, 4, 3)),
              (anchor_w, (batch, 4, 3)), (live_root, (batch, 3)),
              (live_com, (batch, 3)), (previous_root, (batch, 3)),
              (previous_joint, (batch, 12))]
    if any(v.shape != shape or not v.is_floating_point() or v.device != entry_root.device
           for v, shape in values):
        raise ValueError('invalid transfer tensor shape, dtype or device')
    if (selected_leg.shape != (batch,) or selected_leg.dtype != torch.long
            or selected_leg.device != entry_root.device):
        raise ValueError('selected_leg must be long [B] on input device')
    finite = torch.ones(batch, dtype=torch.bool, device=entry_root.device)
    for value, _ in values:
        finite &= torch.isfinite(value).reshape(batch, -1).all(-1)
    finite &= (selected_leg >= 0) & (selected_leg < 4)
    if total_weight is not None:
        if total_weight.shape != (batch,) or total_weight.device != entry_root.device:
            raise ValueError('total_weight must be [B] on input device')
        finite &= torch.isfinite(total_weight) & (total_weight >= 3.*reserve)
    if wheel_force is not None:
        if (wheel_force.shape != (batch, 4) or not wheel_force.is_floating_point()
                or wheel_force.device != entry_root.device):
            raise ValueError('wheel_force must be float [B,4] on input device')
        finite &= torch.isfinite(wheel_force).all(-1)
    indices = torch.tensor([[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]],
                           device=entry_root.device)[selected_leg.clamp(0, 3)]
    # Feedback geometry is measured; IK anchors stay frozen at stage entry.
    # Using the anchors here would silently count slipped contacts as unmoved.
    triangle = support_w.gather(1, indices[..., None].expand(-1, -1, 3))[..., :2]
    edge = triangle.roll(-1, dims=1) - triangle
    lengths = edge.norm(dim=-1)
    ab, ac = triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0]
    area = ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]
    inward = torch.stack([-edge[..., 1], edge[..., 0]], dim=-1)
    inward = inward * area.sign()[:, None, None] / lengths.clamp_min(1e-12)[..., None]
    distance = ((live_com[:, None, :2] - triangle) * inward).sum(-1)
    hard_margin = torch.full_like(distance, .02)
    soft_margin = torch.full_like(distance, .03)
    if total_weight is not None:
        # Distance to an edge / opposite altitude is the corresponding support
        # barycentric load fraction. All three edge constraints apply together.
        altitude = area.abs()[:, None] / lengths.clamp_min(1e-12)
        weight = torch.where(torch.isfinite(total_weight) & (total_weight >= 90.),
                             total_weight, torch.ones_like(total_weight))
        hard_margin = torch.maximum(hard_margin, altitude * (reserve / weight)[:, None])
        soft_margin = torch.maximum(soft_margin, altitude * ((reserve+5.) / weight)[:, None])
    post_lift_load_ready = (distance >= hard_margin).all(-1) & finite
    correction, soft_feasible = _nearest_halfplane_point(inward, soft_margin - distance)
    desired = entry_root.clone()
    # Correct the last command using measured COM error. Re-anchoring every
    # update to the measured root discards persistent actuator tracking offset
    # and can reverse a still-needed correction. The fixed entry bound below
    # remains the anti-windup limit; no measured height/RPY is accumulated.
    desired[:, :2] = previous_root[:, :2] + correction
    # A soft-margin target outside the entry ball does not prove the hard
    # requirement infeasible. Project the entry origin onto hard halfplanes:
    # this is the minimum possible entry displacement under the rigid COM model.
    entry_delta = entry_root[:, :2] - previous_root[:, :2]
    entry_distance = distance + (entry_delta[:, None] * inward).sum(-1)
    hard_correction, hard_feasible = _nearest_halfplane_point(inward, hard_margin - entry_distance)
    hard_desired = entry_root.clone()
    hard_desired[:, :2] += hard_correction
    use_hard = ~soft_feasible | ((desired - entry_root).norm(dim=-1) > max_root_shift)
    desired = torch.where(use_hard[:, None], hard_desired, desired)
    geometric = (area.abs() > 1e-10) & (lengths > 1e-10).all(-1)
    geometric &= torch.where(use_hard, hard_feasible, soft_feasible)
    load_ok = torch.ones_like(finite)
    load_satisfied = torch.ones_like(finite)
    force_target = None
    if wheel_force is not None:
        support_force = wheel_force.gather(1, indices)
        total = support_force.sum(-1)
        load_ok = (support_force > 10.).all(-1) & (total >= 3.*reserve)
        load_satisfied = (support_force >= reserve[:,None]).all(-1)
        deficit = (reserve[:,None] - support_force).clamp_min(0.)
        supply = (support_force - reserve[:,None]).clamp_min(0.)
        force_target = support_force + deficit - supply * (
            deficit.sum(-1) / supply.sum(-1).clamp_min(1e-8))[:, None]
        # Quasi-static load-redistribution proposal. Preserve total supported
        # load; shift toward underloaded contacts. Physical contacts must verify
        # the response, since force-weighted centers are not stability proofs.
        load_shift = (((force_target-support_force) / total.clamp_min(1e-8)[:, None])
                      [..., None] * (triangle-triangle[:, :1])).sum(1)
        projected_distance = distance + (load_shift[:, None] * inward).sum(-1)
        extra, load_geometric = _nearest_halfplane_point(inward, .02-projected_distance)
        load_desired = entry_root.clone()
        load_desired[:, :2] = previous_root[:, :2] + load_shift + extra
        desired = torch.where(load_satisfied[:, None], desired, load_desired)
        geometric &= load_satisfied | load_geometric
    # Stop transferring at the hard PREPARE margin and let the five-frame
    # gate assess stability. Continuing toward the soft .03m target can reject
    # an already-ready pose at the displacement bound. Do not recapture drift.
    satisfied_now = post_lift_load_ready & load_satisfied
    desired = torch.where(satisfied_now[:, None], previous_root, desired)
    in_bound = ((desired - entry_root).norm(dim=-1) <= max_root_shift)
    in_bound &= ((previous_root - entry_root).norm(dim=-1) <= max_root_shift + 1e-6)
    in_bound &= (previous_root[:, 2] - entry_root[:, 2]).abs() < 1e-6
    delta = desired - previous_root
    scale = (root_speed * dt / delta.norm(dim=-1).clamp_min(1e-12)).clamp(max=1)
    candidate_root = previous_root + delta * scale[:, None]
    candidate_root[:, 2] = entry_root[:, 2]
    joint, reachable = m1_ik(candidate_root, entry_rpy, anchor_w)
    joint = joint.reshape(batch, 12)
    ik_ok = reachable.all(-1) & m1_joint_limit_mask(joint) & m1_joint_limit_mask(previous_joint)
    slew_ok = ((joint - previous_joint).abs() <= .5 * dt + 1e-7).all(-1)
    reason = torch.zeros(batch, dtype=torch.long, device=entry_root.device)
    # Later writes have higher priority, ensuring missing evidence is not mislabeled.
    for condition, code in [(slew_ok, 5), (ik_ok, 4), (in_bound, 3), (geometric, 2), (load_ok, 6), (finite, 1)]:
        reason = torch.where(condition, reason, code)
    valid = reason == 0
    return dict(root=torch.where(valid[:, None], candidate_root, previous_root),
                joint=torch.where(valid[:, None], joint, previous_joint),
                valid=valid, reason=reason, desired_root=desired,
                support_force_target=force_target, post_lift_load_ready=post_lift_load_ready)
