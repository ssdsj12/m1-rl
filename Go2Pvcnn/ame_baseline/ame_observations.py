"""Six-channel AME terrain observations from the semantic grid scanner."""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F


def _sensor_from_env(env, name: str):
    try:
        return env.scene.sensors[name]
    except (KeyError, TypeError):
        return getattr(env.scene.sensors, name)


def _yaw_quat(quat: torch.Tensor) -> torch.Tensor:
    """Return the yaw-only part of a ``(w, x, y, z)`` quaternion."""

    shape = quat.shape
    flat = quat.reshape(-1, 4)
    qw, qx, qy, qz = flat.unbind(dim=-1)
    yaw = torch.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy.square() + qz.square()))
    result = torch.zeros_like(flat)
    result[:, 0] = torch.cos(yaw / 2)
    result[:, 3] = torch.sin(yaw / 2)
    return F.normalize(result, dim=-1).reshape(shape)


def _quat_apply_inverse(quat: torch.Tensor, vec: torch.Tensor) -> torch.Tensor:
    """Apply an inverse ``(w, x, y, z)`` quaternion rotation without Isaac imports."""

    shape = vec.shape
    flat_quat = quat.reshape(-1, 4)
    flat_vec = vec.reshape(-1, 3)
    xyz = flat_quat[:, 1:]
    cross = xyz.cross(flat_vec, dim=-1) * 2
    return (flat_vec - flat_quat[:, :1] * cross + xyz.cross(cross, dim=-1)).reshape(shape)


def _local_ray_hits(sensor) -> torch.Tensor:
    data = sensor.data
    hits_w = torch.as_tensor(data.ray_hits_w)
    if hits_w.ndim != 3 or hits_w.shape[-1] != 3:
        raise ValueError(f"ray_hits_w must have shape [N,R,3], got {tuple(hits_w.shape)}")

    sensor_pos_w = torch.as_tensor(data.pos_w, dtype=hits_w.dtype, device=hits_w.device)
    sensor_quat_w = torch.as_tensor(data.quat_w, dtype=hits_w.dtype, device=hits_w.device)
    alignment = getattr(sensor.cfg, "ray_alignment", None) if hasattr(sensor, "cfg") else None
    if alignment == "yaw":
        sensor_quat_w = _yaw_quat(sensor_quat_w)

    batch, rays, _ = hits_w.shape
    relative_w = hits_w - sensor_pos_w.unsqueeze(1)
    expanded_quat = sensor_quat_w.unsqueeze(1).expand(batch, rays, 4).reshape(-1, 4)
    local = _quat_apply_inverse(expanded_quat, relative_w.reshape(-1, 3)).reshape(batch, rays, 3)
    return torch.nan_to_num(local, nan=0.0, posinf=25.0, neginf=-25.0).clamp_(-25.0, 25.0)


def downsampled_ame_scan(env, sensor_cfg, target_size: int = 16) -> torch.Tensor:
    """Return `[x_local,y_local,z_local,terrain,small,large]` as `[N,6,S,S]`."""

    if target_size <= 0:
        raise ValueError("target_size must be positive")
    sensor = _sensor_from_env(env, sensor_cfg.name)
    local = _local_ray_hits(sensor)
    batch, num_rays, _ = local.shape
    side = math.isqrt(num_rays)
    if side * side != num_rays:
        raise ValueError(f"ray scan length {num_rays} is not a perfect square")

    semantic = torch.as_tensor(sensor.data.semantic_map, dtype=torch.long, device=local.device)
    if semantic.shape != (batch, side, side):
        raise ValueError(
            f"semantic_map must have shape {(batch, side, side)}, got {tuple(semantic.shape)}"
        )
    if bool(torch.any((semantic < 0) | (semantic > 2))):
        values = torch.unique(semantic).detach().cpu().tolist()
        raise ValueError(f"semantic_map ids must be in {{0,1,2}}, got {values}")

    xyz = local.reshape(batch, side, side, 3).permute(0, 3, 1, 2)
    xyz = F.adaptive_avg_pool2d(xyz, (target_size, target_size))

    # Pool class ids before one-hot conversion so every output cell stays one-hot.
    pooled_ids = F.adaptive_max_pool2d(
        semantic.to(dtype=xyz.dtype).unsqueeze(1), (target_size, target_size)
    ).squeeze(1).to(dtype=torch.long)
    one_hot = F.one_hot(pooled_ids, num_classes=3).permute(0, 3, 1, 2).to(dtype=xyz.dtype)
    return torch.cat((xyz, one_hot), dim=1)


__all__ = ["downsampled_ame_scan"]
