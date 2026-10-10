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


def _local_ray_hits(sensor, env_slice: slice = slice(None)) -> torch.Tensor:
    data = sensor.data
    hits_w = torch.as_tensor(data.ray_hits_w)[env_slice]
    if hits_w.ndim != 3 or hits_w.shape[-1] != 3:
        raise ValueError(f"ray_hits_w must have shape [N,R,3], got {tuple(hits_w.shape)}")

    sensor_pos_w = torch.as_tensor(data.pos_w, dtype=hits_w.dtype, device=hits_w.device)[env_slice]
    sensor_quat_w = torch.as_tensor(data.quat_w, dtype=hits_w.dtype, device=hits_w.device)[env_slice]
    alignment = getattr(sensor.cfg, "ray_alignment", None) if hasattr(sensor, "cfg") else None
    if alignment == "yaw":
        sensor_quat_w = _yaw_quat(sensor_quat_w)

    batch, rays, _ = hits_w.shape
    relative_w = hits_w - sensor_pos_w.unsqueeze(1)
    expanded_quat = sensor_quat_w.unsqueeze(1).expand(batch, rays, 4).reshape(-1, 4)
    local = _quat_apply_inverse(expanded_quat, relative_w.reshape(-1, 3)).reshape(batch, rays, 3)
    return torch.nan_to_num(local, nan=0.0, posinf=25.0, neginf=-25.0).clamp_(-25.0, 25.0)


def downsampled_ame_scan(env, sensor_cfg, target_size: int = 16) -> torch.Tensor:
    """Return `[x_local,y_local,z_local,terrain,small,large]` as `[N,6,S,S]`.

    Obstacle bins retain one real hit of the winning class (large > small),
    selected by world height. Terrain bins average finite hits as before.
    Bins without any finite hit have zero XYZ and all-zero semantic channels
    to represent unknown space, rather than fabricated terrain.
    """

    if target_size <= 0:
        raise ValueError("target_size must be positive")
    sensor = _sensor_from_env(env, sensor_cfg.name)
    hits_w = torch.as_tensor(sensor.data.ray_hits_w)
    if hits_w.ndim != 3 or hits_w.shape[-1] != 3:
        raise ValueError(f"ray_hits_w must have shape [N,R,3], got {tuple(hits_w.shape)}")
    batch, num_rays, _ = hits_w.shape
    side = math.isqrt(num_rays)
    if side * side != num_rays:
        raise ValueError(f"ray scan length {num_rays} is not a perfect square")

    semantic = torch.as_tensor(sensor.data.semantic_map, dtype=torch.long, device=hits_w.device)
    if semantic.shape != (batch, side, side):
        raise ValueError(
            f"semantic_map must have shape {(batch, side, side)}, got {tuple(semantic.shape)}"
        )
    if bool(torch.any((semantic < 0) | (semantic > 2))):
        values = torch.unique(semantic).detach().cpu().tolist()
        raise ValueError(f"semantic_map ids must be in {{0,1,2}}, got {values}")

    outputs = []
    # Bound transform/masking temporaries independently of the training env count.
    # Do not materialize an additional full [2048,151,151,3] geometry tensor.
    for start in range(0, batch, 128):
        env_slice = slice(start, start + 128)
        local = _local_ray_hits(sensor, env_slice)
        count = local.shape[0]
        source = hits_w[env_slice]
        valid = torch.isfinite(source).all(dim=-1)
        pose_valid = (
            torch.isfinite(torch.as_tensor(sensor.data.pos_w, device=hits_w.device)[env_slice]).all(dim=-1)
            & torch.isfinite(torch.as_tensor(sensor.data.quat_w, device=hits_w.device)[env_slice]).all(dim=-1)
        )
        valid = (valid & pose_valid.unsqueeze(1)).reshape(count, side, side)
        ids = semantic[env_slice]
        xyz = local.reshape(count, side, side, 3).permute(0, 3, 1, 2)
        weights = valid.unsqueeze(1).to(dtype=local.dtype)
        coverage = F.adaptive_avg_pool2d(weights, (target_size, target_size))
        xyz = F.adaptive_avg_pool2d(xyz * weights, (target_size, target_size))
        xyz = xyz / torch.where(coverage > 0, coverage, torch.ones_like(coverage))

        # Invalid source hits cannot win the semantic class or the height search.
        class_scores = ids.to(dtype=local.dtype).masked_fill(~valid, -1).unsqueeze(1)
        pooled_ids = F.adaptive_max_pool2d(class_scores, (target_size, target_size)).squeeze(1).long()
        world_z = source[..., 2].reshape(count, side, side)
        for obstacle_class in (1, 2):
            heights = world_z.masked_fill(~(valid & (ids == obstacle_class)), -torch.inf)
            _, indices = F.adaptive_max_pool2d(
                heights.unsqueeze(1), (target_size, target_size), return_indices=True
            )
            selected = local.gather(1, indices.flatten(1).unsqueeze(-1).expand(-1, -1, 3))
            selected = selected.transpose(1, 2).reshape(count, 3, target_size, target_size)
            xyz = torch.where((pooled_ids == obstacle_class).unsqueeze(1), selected, xyz)
        one_hot = F.one_hot(pooled_ids.clamp_min(0), num_classes=3).permute(0, 3, 1, 2)
        one_hot = one_hot.to(dtype=local.dtype) * (pooled_ids >= 0).unsqueeze(1)
        outputs.append(torch.cat((xyz, one_hot), dim=1))
    return torch.cat(outputs, dim=0)


__all__ = ["downsampled_ame_scan"]
