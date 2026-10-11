"""Diagnostic-only placement evidence; never imported by PPO/rewards.

Pose limits (2cm translation, 5deg rotation, .04rad joint error) constrain
whether the requested static sample was actually observed. Failing them is
inconclusive for layout feasibility, not a new runtime success threshold.
Paired measurements retain those limits on *additional* displacement relative
to an independently supported, stationary empty-ground control. Absolute
errors are still reported; no collision/clearance/support evidence is removed.
"""
import math
import torch


def assess_frame(*, wheel_force, bottom, ground, margin, expected,
                 nonwheel_force, clearance, root_error, angle_error, joint_error):
    values = (wheel_force, bottom, ground, margin, nonwheel_force, clearance,
              root_error, angle_error, joint_error)
    finite = all(bool(torch.isfinite(v).all()) for v in values)
    other = float(nonwheel_force.norm(dim=-1).max())
    grounded = (wheel_force[..., 2] > 10) & ((bottom-ground[:, None]).abs() <= .004) & (margin >= 0)
    unloaded = bool((wheel_force.norm(dim=-1)[~expected] < 1).all())
    return dict(finite=finite, ground_support=finite and bool(grounded[expected].all()) and unloaded,
                geometry_verified=finite and other < 1 and bool((margin[expected] >= 0).all()) and bool((clearance >= .03).all()),
                pose_verified=finite and bool((root_error <= .02).all()) and bool((angle_error <= math.radians(5)).all()) and bool((joint_error <= .04).all()),
                min_clearance=float(clearance.min()), min_support_margin=float(margin[expected].min()),
                max_nonwheel_force=other, max_root_error=float(root_error.max()),
                max_angle_error=float(angle_error.max()), max_joint_error=float(joint_error.max()),
                wheel_force=wheel_force.tolist(), wheel_bottom=bottom.tolist())


class PlacementEvidence:
    def __init__(self):
        self.frames = []

    def record(self, frame):
        self.frames.append(frame)

    def result(self):
        geometry = bool(self.frames) and all(f['geometry_verified'] for f in self.frames)
        pose = bool(self.frames) and all(f['pose_verified'] for f in self.frames)
        support = len(self.frames) >= 5 and all(f['ground_support'] for f in self.frames[-5:])
        return dict(verified=geometry and pose and support, geometry_verified=geometry,
                    pose_verified=pose, support_verified=support, frames=len(self.frames))


def compare_placement(frames, reference):
    """Compare loaded trajectories, never nominal FK to a compliant actuator.

Reference must have identical joint targets, sampling and shape; every frame
must be finite/collision-free, the last five supported and nearly stationary
(range <=1mm / .005rad joints and orientation). It must stay inside the existing recovery envelope
(8cm root height / .15rad joints), plus 2cm horizontal drift and 5deg tilt.
These are diagnostic rejection guards, not changes to runtime criteria.
"""
    history = PlacementEvidence()
    history.frames = frames
    result = history.result()
    result['absolute_pose_verified'] = result.pop('pose_verified')
    result.update(verified=False, baseline_valid=False, calibrated_pose_verified=False)
    if len(frames) < 5 or len(frames) != len(reference):
        return result
    keys = ('root_delta', 'joint_delta', 'root_quat', 'requested_joints')
    try:
        a = {k: torch.tensor([f[k] for f in frames], dtype=torch.float64) for k in keys}
        b = {k: torch.tensor([f[k] for f in reference], dtype=torch.float64) for k in keys}
        if any(a[k].shape != b[k].shape or not torch.isfinite(a[k]).all()
               or not torch.isfinite(b[k]).all() for k in keys):
            return result
        dt = [f['physics_dt'] for f in frames]
        same_sampling = all(math.isfinite(t) and t > 0 and t == r['physics_dt']
                            for t, r in zip(dt, reference)) and len(set(dt)) == 1
        same_targets = torch.equal(a['requested_joints'], b['requested_joints'])
        root_range = (b['root_delta'][-5:].amax(0)-b['root_delta'][-5:].amin(0)).norm(dim=-1).max()
        joint_range = (b['joint_delta'][-5:].amax(0)-b['joint_delta'][-5:].amin(0)).max()
        quaternions_valid = all(bool((x['root_quat'].norm(dim=-1)-1).abs().max() < 1e-4) for x in (a,b))
        if not quaternions_valid:
            return result
        for x in (a,b):
            x['root_quat'] = x['root_quat'] / x['root_quat'].norm(dim=-1,keepdim=True)
        tail = b['root_quat'][-5:]
        tail_dot = (tail[:,None]*tail[None,:]).sum(-1).abs().clamp(0,1)
        angle_range = (2*torch.acos(tail_dot)).max()
        step_dot = (tail[1:]*tail[:-1]).sum(-1).abs().clamp(0,1)
        max_angle_speed = (2*torch.acos(step_dot)).max()/dt[-1] if same_sampling else float('inf')
        baseline = (same_sampling and same_targets and quaternions_valid
                    and all(f['finite'] and f['geometry_verified'] for f in reference)
                    and all(f['ground_support'] for f in reference[-5:])
                    and root_range <= .001 and joint_range <= .005 and angle_range <= .005
                    and b['root_delta'][...,:2].norm(dim=-1).max() <= .02
                    and b['root_delta'][...,2].abs().max() <= .08
                    and b['joint_delta'].abs().max() <= .15
                    and all(f['max_angle_error'] <= math.radians(5) for f in reference))
        root = (a['root_delta']-b['root_delta']).norm(dim=-1).max()
        joint = (a['joint_delta']-b['joint_delta']).abs().max()
        dot = (a['root_quat']*b['root_quat']).sum(-1).abs().clamp(0,1)
        angle = (2*torch.acos(dot)).max()
        pose = bool(root <= .02 and joint <= .04 and angle <= math.radians(5))
        result.update(baseline_valid=bool(baseline), calibrated_pose_verified=bool(baseline) and pose,
                      max_paired_root_error=float(root),max_paired_joint_error=float(joint),
                      max_paired_angle_error=float(angle),reference_root_range=float(root_range),
                      reference_joint_range=float(joint_range),reference_angle_range=float(angle_range),
                      reference_max_angle_speed=float(max_angle_speed))
        result['verified'] = bool(baseline) and pose and result['geometry_verified'] and result['support_verified']
    except (KeyError, TypeError, ValueError, RuntimeError, IndexError):
        # Malformed/incomplete diagnostics are never acceptance evidence.
        pass
    return result


def summarize_native(recoveries, folds, *, reference_only=False):
    """Separate invalid fixtures from failed candidates; neither permits deployment."""
    if reference_only:
        assessment='controls_only'
    elif len(recoveries)!=96 or len(folds)!=120:
        assessment='incomplete'
    elif not all(x.get('baseline_valid',False) for x in (*recoveries,*folds)):
        assessment='inconclusive_fixture'
    elif not (all(x.get('verified',False) and x.get('runtime_ready',False) for x in recoveries)
              and all(x.get('verified',False) for x in folds)):
        assessment='placement_failed'
    else:
        assessment='placement_verified'
    return dict(accepted=assessment=='placement_verified',assessment=assessment)
