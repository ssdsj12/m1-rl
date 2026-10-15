"""Bounded yaw-only support feedback; no active-leg trajectory changes."""
import torch
from ame_baseline.m1_teacher_pose import _rotation


def support_heading_goal(goal, measured_quat, command_quat, active, enabled):
    measured_rotation = _rotation(measured_quat)
    command_rotation = _rotation(command_quat)
    measured_yaw = torch.atan2(measured_rotation[:, 1, 0], measured_rotation[:, 0, 0])
    command_yaw = torch.atan2(command_rotation[:, 1, 0], command_rotation[:, 0, 0])
    error = measured_yaw - command_yaw
    delta = torch.atan2(torch.sin(error), torch.cos(error)).clamp(-.05, .05)
    delta = torch.where(enabled, delta, torch.zeros_like(delta))
    relative = torch.einsum('bij,bkj->bki', measured_rotation, goal)
    rotated = relative.clone()
    cosine, sine = torch.cos(delta)[:, None], torch.sin(delta)[:, None]
    rotated[:, :, 0] = cosine * relative[:, :, 0] - sine * relative[:, :, 1]
    rotated[:, :, 1] = sine * relative[:, :, 0] + cosine * relative[:, :, 1]
    corrected = torch.einsum('bij,bkj->bki', measured_rotation.transpose(-1, -2), rotated)
    support = torch.arange(4, device=goal.device)[None] != active[:, None]
    use = enabled[:, None] & support & (delta[:, None] != 0)
    return torch.where(use[:, :, None], corrected, goal), delta
