"""Diagnostic-only placement evidence; never imported by PPO/rewards.

Pose limits (2cm translation, 5deg rotation, .04rad joint error) constrain
whether the requested static sample was actually observed. Failing them is
inconclusive for layout feasibility, not a new runtime success threshold.
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
