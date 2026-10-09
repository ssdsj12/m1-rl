"""Bounded vertical one-wheel target for diagnostic LIFT, not full crossing.

Caller must have passed PREPARE, own episode/obstacle identity, reject collisions,
and enforce the four-second single-leg deadline. Invalid output requests abort or
recovery; holding the previous command is not a recovery guarantee.

Optional pose_feedback uses frozen measured LIFT-entry pose, not an accumulated
correction. It counters measured drift with unit proportional gain, rejects
translation errors over25mm or angle errors over.08rad, and backtracks pose and
foot progress together under the existing joint slew bound. Caller keeps root
and rpy as fixed prepared commands and feeds returned root/rpy only as previous
commands. This experimental feedback is not a stability certificate.

advance_mask optionally holds selected-wheel height per row while a caller
repairs the support configuration; it never overrides the rejection guards.

attitude_feedback optionally counteracts roll/pitch error about the fixed rpy
reference with unit proportional gain, no translation or yaw correction. It
may coexist with selected-leg world-height correction, but not pose_feedback.
Stance anchors remain fixed and all proposals share the existing joint slew.
"""
import math
import torch
from extension.parallelism.m1_kinematics import m1_ik, m1_joint_limit_mask


def lift_target(*, root, rpy, anchor_w, selected_leg, previous_joint, height,
                force, tilt, tilt_rate, margin, dt, pose_feedback=None, advance_mask=None,
                world_feedback=None, target_height=None, vertical_speed=.08, attitude_feedback=None):
    if not math.isfinite(dt) or not 0 < dt <= .1:
        raise ValueError('dt must be finite in (0, .1] seconds')
    if not math.isfinite(vertical_speed) or not 0 < vertical_speed <= .12:
        raise ValueError('vertical_speed must be finite in (0,.12] m/s')
    if target_height is not None and (not math.isfinite(target_height) or not -.005 <= target_height <= .18):
        raise ValueError('target_height must be finite in [-.005,.18]')
    batch = root.shape[0]
    if world_feedback is not None and pose_feedback is not None:
        raise ValueError('world and whole-body pose feedback have separate ownership')
    if attitude_feedback is not None and pose_feedback is not None:
        raise ValueError('attitude and whole-body feedback have separate ownership')
    data = [(root, (batch, 3)), (rpy, (batch, 3)), (anchor_w, (batch, 4, 3)),
            (previous_joint, (batch, 12)), (height, (batch,)), (force, (batch, 4)),
            (tilt, (batch, 2)), (tilt_rate, (batch, 2)), (margin, (batch,))]
    if any(x.shape != shape or x.device != root.device or not x.is_floating_point()
           for x, shape in data):
        raise ValueError('invalid lift tensor shape, device or dtype')
    if (selected_leg.shape != (batch,) or selected_leg.dtype != torch.long
            or selected_leg.device != root.device):
        raise ValueError('selected_leg must be long [B] on input device')
    finite = torch.ones(batch, dtype=torch.bool, device=root.device)
    for value, _ in data:
        finite &= torch.isfinite(value).reshape(batch, -1).all(-1)
    target_root, target_rpy = root, rpy
    old_root, old_rpy = root, rpy
    feedback_ok = torch.ones_like(finite)
    if attitude_feedback is not None:
        if set(attitude_feedback)!= {'live_rpy','previous_rpy'}:
            raise ValueError('attitude feedback requires live and previous rpy')
        if any(x.shape!=(batch,3) or x.device!=root.device or x.dtype!=root.dtype
               for x in attitude_feedback.values()):
            raise ValueError('invalid attitude feedback tensor')
        for x in attitude_feedback.values():finite &= torch.isfinite(x).all(-1)
        error=rpy-attitude_feedback['live_rpy']
        error=torch.atan2(error.sin(),error.cos())
        old_rpy=attitude_feedback['previous_rpy']
        old_delta=torch.atan2((old_rpy-rpy).sin(),(old_rpy-rpy).cos())
        feedback_ok &= (error[:,:2].norm(dim=-1)<=.08)&(old_delta[:,:2].norm(dim=-1)<=.08)
        feedback_ok &= (old_delta[:,2].abs()<=1e-7)
        target_rpy=rpy.clone();target_rpy[:,:2]+=error[:,:2]
        feedback_ok &= (target_rpy[:,:2].abs()<=.15).all(-1)
    if pose_feedback is not None:
        keys = ('reference_root', 'reference_rpy', 'live_root', 'live_rpy',
                'previous_root', 'previous_rpy')
        if set(pose_feedback) != set(keys):
            raise ValueError('pose_feedback requires fixed references, live pose and previous commands')
        if any(pose_feedback[k].shape != (batch, 3)
               or pose_feedback[k].device != root.device
               or not pose_feedback[k].is_floating_point() for k in keys):
            raise ValueError('invalid pose_feedback tensor')
        for value in pose_feedback.values():
            finite &= torch.isfinite(value).all(-1)
        delta_root = pose_feedback['reference_root'] - pose_feedback['live_root']
        delta_rpy = pose_feedback['reference_rpy'] - pose_feedback['live_rpy']
        delta_rpy = torch.atan2(torch.sin(delta_rpy), torch.cos(delta_rpy))
        feedback_ok = (delta_root.norm(dim=-1) <= .025) & (delta_rpy.abs() <= .08).all(-1)
        target_root, target_rpy = root + delta_root, rpy + delta_rpy
        old_root, old_rpy = pose_feedback['previous_root'], pose_feedback['previous_rpy']
    candidate_root, candidate_rpy = old_root.clone(), old_rpy.clone()
    minimum_height = -.005 if target_height is not None and target_height < 0 else 0.
    finite &= (selected_leg >= 0) & (selected_leg < 4) & (height >= minimum_height) & (height <= .18)
    leg = selected_leg.clamp(0, 3)
    selected = torch.arange(4, device=root.device)[None] == leg[:, None]
    support_ok = ((force > 10.) | selected).all(-1)
    pose_ok = (tilt.abs() <= .15).all(-1) & (tilt_rate.abs() <= .20).all(-1)
    inside = margin >= 0
    requested = (height + vertical_speed * dt).clamp(max=.18)
    if target_height is not None:
        requested = height + (target_height-height).clamp(min=-vertical_speed*dt,max=vertical_speed*dt)
        if target_height < 0:
            # Reach nominal ground first, then search at <=1cm/s, at most5mm.
            step_down=torch.where(height>0,torch.full_like(height,vertical_speed*dt),torch.full_like(height,.01*dt))
            requested=height+torch.maximum(target_height-height,-step_down).clamp_max(vertical_speed*dt)
            requested=torch.where((height>0)&(requested<0),torch.zeros_like(height),requested)
    if advance_mask is not None:
        if (advance_mask.shape != (batch,) or advance_mask.dtype != torch.bool
                or advance_mask.device != root.device):
            raise ValueError('advance_mask must be bool [B] on input device')
        requested = torch.where(advance_mask, requested, height)
    candidate_height = height.clone()
    joint = previous_joint.clone()
    found = torch.zeros(batch, dtype=torch.bool, device=root.device)
    any_ik = torch.zeros_like(found)
    world_frame = None
    if world_feedback is not None:
        from ame_baseline.m1_selected_world import selected_world_target
        world_frame = {key: value.clone() for key,value in world_feedback['previous_frame'].items()}
    # Reduce Cartesian progress, never clip joints into a different foot pose.
    # Retiming changes Cartesian proposal, never the .5 rad/s joint limit.
    # Preserve legacy default sampling; opt-in faster motion uses finer trials
    # to avoid discarding nearly half the available safe joint increment.
    scales = tuple(i/32 for i in range(32,1,-1)) if vertical_speed > .08 else (1., .5, .25, .125, .0625)
    for scale in scales:
        trial_height = height + (requested - height) * scale
        target = anchor_w.clone()
        target[torch.arange(batch, device=root.device), leg, 2] += trial_height
        trial_root = old_root + scale * (target_root - old_root)
        trial_rpy = old_rpy + scale * (target_rpy - old_rpy)
        trial_joint, reachable = m1_ik(trial_root, trial_rpy, target)
        trial_joint = trial_joint.reshape(batch, 12)
        feasible = reachable.all(-1) & m1_joint_limit_mask(trial_joint) & m1_joint_limit_mask(previous_joint)
        if world_feedback is not None:
            corrected = selected_world_target(root=trial_root,rpy=trial_rpy,
                live_root=world_feedback['live_root'],live_rpy=world_feedback['live_rpy'],
                target=target,nominal=trial_joint,previous=previous_joint,selected=selected_leg,
                dt=dt,previous_frame=world_feedback['previous_frame'],
                vertical_only=world_feedback['vertical_only'],
                height_only=world_feedback.get('height_only',False),
                height_mask=world_feedback.get('height_mask'))
            trial_joint = corrected['joint']
            feasible &= corrected['valid']
        any_ik |= feasible
        accepted = feasible & ((trial_joint - previous_joint).abs() <= .5 * dt + 1e-7).all(-1)
        use = accepted & ~found
        candidate_height = torch.where(use, trial_height, candidate_height)
        candidate_root = torch.where(use[:, None], trial_root, candidate_root)
        candidate_rpy = torch.where(use[:, None], trial_rpy, candidate_rpy)
        joint = torch.where(use[:, None], trial_joint, joint)
        if world_feedback is not None:
            world_frame = {key: torch.where(use[:,None],corrected['frame'][key],value)
                           for key,value in world_frame.items()}
        found |= accepted
    ik_ok, slew_ok = any_ik, found
    reason = torch.zeros(batch, dtype=torch.long, device=root.device)
    for condition, code in [(slew_ok, 6), (ik_ok, 5), (inside, 4), (pose_ok, 3),
                            (support_ok, 2), (feedback_ok, 7), (finite, 1)]:
        reason = torch.where(condition, reason, code)
    valid = reason == 0
    return dict(joint=torch.where(valid[:, None], joint, previous_joint),
                root=torch.where(valid[:, None], candidate_root, old_root),
                rpy=torch.where(valid[:, None], candidate_rpy, old_rpy),
                height=torch.where(valid, candidate_height, height),
                valid=valid, reason=reason, world_frame=world_frame)
