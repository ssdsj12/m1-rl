"""Physics-measured metrics for single-wheel crossing probes."""
from __future__ import annotations

import torch


def strict_target_leg_mismatch_mask(
    *,
    selected_leg: torch.Tensor,
    target_wheel: torch.Tensor,
    awaiting_recovery: torch.Tensor,
    failed: torch.Tensor,
) -> torch.Tensor:
    """Flag a teacher leg that disagrees with the wheel latched for crossing."""
    target_wheel = torch.as_tensor(target_wheel)
    if target_wheel.ndim != 1 or target_wheel.dtype not in (torch.int32, torch.int64):
        raise ValueError("target_wheel must be an integer [B] vector")
    device = target_wheel.device
    selected_leg = torch.as_tensor(selected_leg, device=device)
    awaiting_recovery = torch.as_tensor(awaiting_recovery, device=device)
    failed = torch.as_tensor(failed, device=device)
    if (selected_leg.shape != target_wheel.shape
            or awaiting_recovery.shape != target_wheel.shape
            or failed.shape != target_wheel.shape
            or selected_leg.dtype not in (torch.int32, torch.int64)
            or awaiting_recovery.dtype != torch.bool or failed.dtype != torch.bool):
        raise ValueError("strict target and teacher state must be matching typed vectors")
    crossing_active = (target_wheel >= 0) & ~awaiting_recovery & ~failed
    return crossing_active & (selected_leg != target_wheel)


def crossing_attempt_mask(
    *,
    teacher_active: torch.Tensor,
    selected_leg: torch.Tensor,
    target_wheel: torch.Tensor,
    awaiting_recovery: torch.Tensor,
    failed: torch.Tensor,
) -> torch.Tensor:
    """Select only active, latched obstacle-crossing rows, not recovery rows."""
    teacher_active = torch.as_tensor(teacher_active)
    if teacher_active.ndim != 1 or teacher_active.dtype != torch.bool:
        raise ValueError("teacher_active must be bool [B]")
    device = teacher_active.device
    selected_leg = torch.as_tensor(selected_leg, device=device)
    target_wheel = torch.as_tensor(target_wheel, device=device)
    awaiting_recovery = torch.as_tensor(awaiting_recovery, device=device)
    failed = torch.as_tensor(failed, device=device)
    vectors = (selected_leg, target_wheel, awaiting_recovery, failed)
    if (any(value.shape != teacher_active.shape for value in vectors)
            or selected_leg.dtype not in (torch.int32, torch.int64)
            or target_wheel.dtype not in (torch.int32, torch.int64)
            or awaiting_recovery.dtype != torch.bool or failed.dtype != torch.bool):
        raise ValueError("crossing-attempt state must be matching typed vectors")
    return (teacher_active & (selected_leg >= 0) & (target_wheel >= 0)
            & ~awaiting_recovery & ~failed)


def measured_swing_leg_count(
    wheel_center_z: torch.Tensor,
    wheel_force_norm: torch.Tensor,
    *,
    ground_z: torch.Tensor | float,
    wheel_radius: float,
    minimum_lift_m: float = 0.02,
    unload_force_n: float = 10.0,
) -> torch.Tensor:
    """Count wheels physically elevated and unloaded, per environment.

    Nonzero action targets are intentionally not used: stance holds and normal
    rolling commands can move several leg joints while only one wheel is in
    swing. A swing is counted only when its measured wheel bottom is above the
    local ground by ``minimum_lift_m`` and its measured contact force is low.
    """
    wheel_center_z = torch.as_tensor(wheel_center_z)
    wheel_force_norm = torch.as_tensor(
        wheel_force_norm, device=wheel_center_z.device, dtype=wheel_center_z.dtype,
    )
    ground_z = torch.as_tensor(
        ground_z, device=wheel_center_z.device, dtype=wheel_center_z.dtype,
    )
    radius = float(wheel_radius)
    lift = float(minimum_lift_m)
    unload = float(unload_force_n)
    if (wheel_center_z.ndim != 2 or wheel_center_z.shape[1] != 4
            or wheel_force_norm.shape != wheel_center_z.shape
            or not wheel_center_z.is_floating_point()
            or ground_z.ndim not in (0, 1)
            or (ground_z.ndim == 1 and ground_z.shape[0] != wheel_center_z.shape[0])
            or not torch.isfinite(wheel_center_z).all()
            or not torch.isfinite(wheel_force_norm).all()
            or not torch.isfinite(ground_z).all()
            or not torch.isfinite(torch.tensor((radius, lift, unload))).all()
            or radius <= 0.0 or lift < 0.0 or unload <= 0.0):
        raise ValueError("swing measurements must be finite [B,4] values with valid thresholds")
    if ground_z.ndim == 0:
        ground_z = ground_z.expand(wheel_center_z.shape[0])
    wheel_bottom_above_ground = wheel_center_z - radius - ground_z[:, None]
    physically_swinging = (
        (wheel_bottom_above_ground >= lift)
        & (wheel_force_norm <= unload)
    )
    return physically_swinging.sum(dim=-1)
