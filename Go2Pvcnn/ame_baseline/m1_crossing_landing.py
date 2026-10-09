"""Separate far-side loaded touchdown from post-cross balance recovery."""
from __future__ import annotations

import torch


def crossing_touchdown_safe(*, support_contact: torch.Tensor,
                            support_force: torch.Tensor,
                            target_wheel: torch.Tensor,
                            target_min_force: float = 10.0,
                            support_min_force: float = 30.0) -> torch.Tensor:
    """Require loaded four-wheel touchdown, without requiring recovered pose."""
    support_contact = torch.as_tensor(support_contact)
    support_force = torch.as_tensor(support_force)
    target_wheel = torch.as_tensor(target_wheel, device=support_force.device)
    if (support_contact.dtype != torch.bool or support_contact.ndim != 2
            or support_contact.shape[1] != 4 or support_force.shape != support_contact.shape
            or target_wheel.shape != (support_contact.shape[0],)
            or target_wheel.dtype not in (torch.int32, torch.int64)
            or target_wheel.device != support_contact.device
            or support_force.device != support_contact.device
            or not support_force.is_floating_point()
            or not torch.isfinite(support_force).all()
            or not (float(target_min_force) > 0 and float(support_min_force) > 0)):
        raise ValueError("four finite support contacts/forces and one target wheel per row required")
    if bool(((target_wheel < 0) | (target_wheel >= 4)).any()):
        raise ValueError("target_wheel must index one of the four support wheels")
    wheel_ids = torch.arange(4, device=support_force.device).unsqueeze(0)
    target_mask = wheel_ids == target_wheel[:, None]
    force_ok = torch.where(target_mask, support_force > float(target_min_force),
                           support_force > float(support_min_force)).all(dim=-1)
    return support_contact.all(dim=-1) & force_ok


def m1_recovery_root_height_ready(root_z_w: torch.Tensor,
                                  nominal_root_z_w: torch.Tensor,
                                  tolerance_m: float = 0.08) -> torch.Tensor:
    """Require the body to return near its reset support height after crossing."""
    root_z_w = torch.as_tensor(root_z_w)
    nominal_root_z_w = torch.as_tensor(
        nominal_root_z_w, device=root_z_w.device, dtype=root_z_w.dtype,
    )
    tolerance = float(tolerance_m)
    if (root_z_w.ndim != 1 or nominal_root_z_w.shape != root_z_w.shape
            or not root_z_w.is_floating_point()
            or not nominal_root_z_w.is_floating_point()
            or not torch.isfinite(torch.tensor(tolerance)) or tolerance < 0.0):
        raise ValueError("root heights must be matching floating vectors and tolerance nonnegative")
    return (torch.isfinite(root_z_w) & torch.isfinite(nominal_root_z_w)
            & ((root_z_w - nominal_root_z_w).abs() <= tolerance))


def split_crossing_and_recovery_gates(*, touchdown_safe: torch.Tensor,
                                      balance_recovered: torch.Tensor,
                                      nominal_pose_ready: torch.Tensor,
                                      root_height_ready: torch.Tensor):
    """Keep successful far-side landing independent from later recovery.

    Crossing is established by geometry plus ``touchdown_safe`` in the strict
    tracker.  Balance and nominal-pose readiness gate only the post-cross
    recovery timer; they must never be prerequisites for counting a crossing.
    """
    touchdown_safe = torch.as_tensor(touchdown_safe)
    balance_recovered = torch.as_tensor(
        balance_recovered, device=touchdown_safe.device, dtype=torch.bool,
    )
    nominal_pose_ready = torch.as_tensor(
        nominal_pose_ready, device=touchdown_safe.device, dtype=torch.bool,
    )
    root_height_ready = torch.as_tensor(
        root_height_ready, device=touchdown_safe.device, dtype=torch.bool,
    )
    if (touchdown_safe.dtype != torch.bool or touchdown_safe.ndim != 1
            or balance_recovered.shape != touchdown_safe.shape
            or nominal_pose_ready.shape != touchdown_safe.shape
            or root_height_ready.shape != touchdown_safe.shape):
        raise ValueError("crossing and recovery gates must be matching bool vectors")
    crossing_gate = touchdown_safe
    recovery_gate = (touchdown_safe & balance_recovered & nominal_pose_ready
                     & root_height_ready)
    return crossing_gate, recovery_gate
