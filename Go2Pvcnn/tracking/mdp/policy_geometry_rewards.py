"""Planner-free geometry rewards for the live policy pose."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace as dataclass_replace

import torch
from torch import Tensor

try:
    from isaaclab.managers import SceneEntityCfg
except Exception:  # noqa: BLE001 - keeps tensor tests independent of IsaacLab imports.
    class SceneEntityCfg:  # type: ignore[no-redef]
        def __init__(self, name: str, **kwargs) -> None:
            self.name = name
            for key, value in kwargs.items():
                setattr(self, key, value)

from extension.convention import extract_roll_pitch_batch, extract_yaw_batch
from extension.parallelism.collision import official_collision_mask
from extension.parallelism.config import ParallelismCfg
from extension.parallelism.kinematics import Go2ParallelGeometry, fk_go2
from extension.parallelism.rl_adapter import select_named_joint_state
from extension.parallelism.robot_backend import get_robot_backend
from extension.parallelism.types import ParallelismTerrain


_PLANNER_JOINT_ORDER = (
    "FL_hip_joint",
    "FL_thigh_joint",
    "FL_calf_joint",
    "FR_hip_joint",
    "FR_thigh_joint",
    "FR_calf_joint",
    "RL_hip_joint",
    "RL_thigh_joint",
    "RL_calf_joint",
    "RR_hip_joint",
    "RR_thigh_joint",
    "RR_calf_joint",
)
_COLLISION_CFG = ParallelismCfg()


def _normalize_name(name: str) -> str:
    value = str(name).split("/")[-1]
    return value.split(":")[-1].lower()


def _order_indices(
    source_order: Sequence[str],
    target_order: Sequence[str],
    *,
    device: torch.device,
) -> Tensor | None:
    source_to_index = {_normalize_name(name): index for index, name in enumerate(source_order)}
    indices: list[int] = []
    for name in target_order:
        index = source_to_index.get(_normalize_name(name))
        if index is None:
            return None
        indices.append(index)
    return torch.tensor(indices, dtype=torch.long, device=device)


def _reorder_joint_to_planner(joint_pos: Tensor, joint_names: Sequence[str] | None) -> Tensor:
    values = torch.as_tensor(joint_pos)
    if not joint_names or int(values.shape[-1]) != len(tuple(joint_names)):
        return values
    indices = _order_indices(tuple(joint_names), _PLANNER_JOINT_ORDER, device=values.device)
    if indices is None:
        return values
    return values.index_select(-1, indices)


def parallelism_terrain_from_scan(
    ray_hits_w: Tensor,
    semantic_map: Tensor,
    valid_mask: Tensor | None,
    *,
    resolution: float,
) -> ParallelismTerrain:
    """Build the static terrain object required by official collision checks."""

    hits = torch.as_tensor(ray_hits_w, dtype=torch.float32)
    if hits.ndim != 3 or int(hits.shape[-1]) != 3:
        raise ValueError(f"ray_hits_w must have shape [B,H*W,3], got {tuple(hits.shape)}")
    batch, ray_count, _ = hits.shape
    side = int(round(float(ray_count) ** 0.5))
    if side * side != int(ray_count):
        raise ValueError(f"scanner ray count {ray_count} is not a square grid")

    grid = hits.reshape(batch, side, side, 3)
    semantic = torch.as_tensor(semantic_map, dtype=torch.long, device=hits.device)
    if semantic.ndim == 2:
        semantic = semantic.unsqueeze(0).expand(batch, -1, -1)
    if tuple(semantic.shape) != (batch, side, side):
        raise ValueError(
            f"semantic_map must have shape {(batch, side, side)}, got {tuple(semantic.shape)}"
        )

    if valid_mask is None:
        valid = torch.isfinite(grid).all(dim=-1)
    else:
        valid = torch.as_tensor(valid_mask, dtype=torch.bool, device=hits.device)
        if valid.ndim == 2:
            valid = valid.unsqueeze(0).expand(batch, -1, -1)
        if tuple(valid.shape) != (batch, side, side):
            raise ValueError(
                f"valid_mask must have shape {(batch, side, side)}, got {tuple(valid.shape)}"
            )
        valid = valid & torch.isfinite(grid).all(dim=-1)

    if side > 1:
        col_step = grid[:, 0, 1, :2] - grid[:, 0, 0, :2]
        row_step = grid[:, 1, 0, :2] - grid[:, 0, 0, :2]
        # Isaac GridPattern is X-major, while terrain queries index [Y, X].
        # Detect handedness so both Isaac scans and conventional Y-major grids
        # preserve obstacle locations, including when the scanner is yawed.
        transpose = (col_step[:, 0] * row_step[:, 1] - col_step[:, 1] * row_step[:, 0]) < 0
        grid = torch.where(transpose[:, None, None, None], grid.transpose(1, 2), grid)
        semantic = torch.where(transpose[:, None, None], semantic.transpose(1, 2), semantic)
        valid = torch.where(transpose[:, None, None], valid.transpose(1, 2), valid)

    origin = torch.zeros(batch, 3, dtype=hits.dtype, device=hits.device)
    origin[:, :2] = grid[:, 0, 0, :2]
    if side > 1:
        step_xy = grid[:, 0, 1, :2] - grid[:, 0, 0, :2]
        yaw = torch.atan2(step_xy[:, 1], step_xy[:, 0])
    else:
        yaw = torch.zeros(batch, dtype=hits.dtype, device=hits.device)

    return ParallelismTerrain(
        height_w=torch.nan_to_num(grid[..., 2], nan=0.0, posinf=0.0, neginf=0.0),
        semantic_id=semantic,
        valid_mask=valid,
        origin_w=origin,
        yaw_w=yaw,
        resolution=float(resolution),
    )


def _terrain_from_scanner(scanner, root_pos_w: Tensor, *, resolution: float) -> ParallelismTerrain:
    data = scanner.data
    ray_hits_w = getattr(data, "ray_hits_w", None)
    semantic_map = getattr(data, "semantic_map", None)
    valid_mask = getattr(data, "valid_mask", None)
    if semantic_map is None:
        raise RuntimeError("semantic_height_scanner.data.semantic_map is required")
    if ray_hits_w is not None:
        return parallelism_terrain_from_scan(
            ray_hits_w,
            semantic_map,
            valid_mask,
            resolution=resolution,
        )

    elevation_map = getattr(data, "elevation_map", None)
    if elevation_map is None:
        raise RuntimeError("semantic_height_scanner requires ray_hits_w or elevation_map")
    height = torch.as_tensor(elevation_map, dtype=torch.float32, device=root_pos_w.device)
    if height.ndim != 3:
        raise ValueError(f"elevation_map must have shape [B,H,W], got {tuple(height.shape)}")
    batch, height_size, width = height.shape
    if height_size != width:
        raise ValueError(f"elevation_map must be square, got {tuple(height.shape)}")
    side = int(height_size)
    semantic = torch.as_tensor(semantic_map, dtype=torch.long, device=height.device)
    if semantic.ndim == 2:
        semantic = semantic.unsqueeze(0).expand(batch, -1, -1)
    valid = (
        torch.isfinite(height)
        if valid_mask is None
        else torch.as_tensor(valid_mask, dtype=torch.bool, device=height.device)
    )
    valid = valid & torch.isfinite(height)
    half_extent = 0.5 * float(side - 1) * float(resolution)
    origin = torch.zeros(batch, 3, dtype=height.dtype, device=height.device)
    origin[:, 0] = root_pos_w[:, 0] - half_extent
    origin[:, 1] = root_pos_w[:, 1] - half_extent
    return ParallelismTerrain(
        height_w=torch.nan_to_num(height, nan=0.0, posinf=0.0, neginf=0.0),
        semantic_id=semantic,
        valid_mask=valid,
        origin_w=origin,
        yaw_w=torch.zeros(batch, dtype=height.dtype, device=height.device),
        resolution=float(resolution),
    )


def _expand_geometry_for_collision(geometry: Go2ParallelGeometry) -> Go2ParallelGeometry:
    batch, leg_count = geometry.foot_pos_w.shape[:2]

    def expand_pose(value: Tensor) -> Tensor:
        return value[:, None, None].expand(batch, leg_count, 1, *value.shape[1:])

    def expand_samples(value: Tensor) -> Tensor:
        return value[:, None, None].expand(batch, leg_count, 1, *value.shape[1:])

    return Go2ParallelGeometry(
        hip_pos_w=expand_pose(geometry.hip_pos_w),
        hip_rot_w=expand_pose(geometry.hip_rot_w),
        foot_pos_w=expand_pose(geometry.foot_pos_w),
        knee_pos_w=expand_pose(geometry.knee_pos_w),
        calf_samples_w=expand_samples(geometry.calf_samples_w),
        thigh_samples_w=expand_samples(geometry.thigh_samples_w),
        thigh_pos_w=expand_pose(geometry.thigh_pos_w),
        thigh_rot_w=expand_pose(geometry.thigh_rot_w),
        calf_pos_w=expand_pose(geometry.calf_pos_w),
        calf_rot_w=expand_pose(geometry.calf_rot_w),
        foot_rot_w=expand_pose(geometry.foot_rot_w),
    )


def live_policy_geometry_collision_event(
    root_pos_w: Tensor,
    root_quat_w: Tensor,
    joint_pos: Tensor,
    joint_names: Sequence[str] | None,
    terrain: ParallelismTerrain,
    cfg: ParallelismCfg = _COLLISION_CFG,
) -> Tensor:
    """Return one collision event per environment for the live policy pose."""

    root_pos = torch.as_tensor(root_pos_w, dtype=torch.float32)
    root_quat = torch.as_tensor(root_quat_w, dtype=root_pos.dtype, device=root_pos.device)
    joint = _reorder_joint_to_planner(joint_pos, joint_names).to(dtype=root_pos.dtype, device=root_pos.device)
    roll, pitch = extract_roll_pitch_batch(root_quat)
    yaw = extract_yaw_batch(root_quat)
    root_rpy = torch.stack((roll, pitch, yaw), dim=-1)
    geometry = fk_go2(root_pos, root_rpy, joint, capsule_samples=int(cfg.capsule_samples))
    expanded_geometry = _expand_geometry_for_collision(geometry)
    _, collision_bits = official_collision_mask(terrain, expanded_geometry, cfg)
    return collision_bits.any(dim=(1, 2, 3)).to(dtype=torch.float32)


def policy_geometry_collision_penalty(
    env,
    asset_cfg: SceneEntityCfg = SceneEntityCfg("robot"),
    scanner_cfg: SceneEntityCfg = SceneEntityCfg("semantic_height_scanner"),
) -> Tensor:
    """Return the raw live-policy geometry collision event.

    The negative sign belongs to the RewardTerm weight. No reference trajectory,
    contact phase, or Parallelism manager is consulted here.
    """

    robot = env.scene[asset_cfg.name]
    scanner = env.scene[scanner_cfg.name]
    default_device = torch.as_tensor(robot.data.root_pos_w).device
    device = torch.device(getattr(env, "device", default_device))
    root_pos_w = torch.as_tensor(robot.data.root_pos_w, dtype=torch.float32, device=device)
    pattern_cfg = getattr(getattr(scanner, "cfg", None), "pattern_cfg", None)
    resolution = float(getattr(pattern_cfg, "resolution", 0.01))
    terrain = _terrain_from_scanner(scanner, root_pos_w, resolution=resolution)
    return live_policy_geometry_collision_event(
        root_pos_w=root_pos_w,
        root_quat_w=robot.data.root_quat_w,
        joint_pos=robot.data.joint_pos,
        joint_names=tuple(getattr(robot, "joint_names", ())),
        terrain=terrain,
    )


def live_m1_policy_geometry_collision_event(
    root_pos_w: Tensor,
    root_quat_w: Tensor,
    joint_pos: Tensor,
    joint_names: Sequence[str],
    terrain: ParallelismTerrain,
) -> Tensor:
    """Return M1 live-policy collision events using named planner joints."""

    backend = get_robot_backend("m1")
    root_pos = torch.as_tensor(root_pos_w, dtype=torch.float32)
    root_quat = torch.as_tensor(root_quat_w, dtype=root_pos.dtype, device=root_pos.device)
    joint = torch.as_tensor(joint_pos, dtype=root_pos.dtype, device=root_pos.device)
    planner_joint = select_named_joint_state(
        joint,
        source_names=tuple(joint_names),
        selected_names=backend.planner_joint_names,
    )
    roll, pitch = extract_roll_pitch_batch(root_quat)
    yaw = extract_yaw_batch(root_quat)
    root_rpy = torch.stack((roll, pitch, yaw), dim=-1)
    geometry = backend.fk(
        root_pos,
        root_rpy,
        planner_joint,
        capsule_samples=int(backend.cfg.capsule_samples),
    )
    expanded_geometry = _expand_geometry_for_collision(geometry)
    _, collision_bits = backend.collision_mask(terrain, expanded_geometry, backend.cfg)
    return collision_bits.reshape(collision_bits.shape[0], -1).any(dim=-1).to(dtype=torch.float32)


def live_m1_policy_geometry_collision_by_leg(
    root_pos_w: Tensor,
    root_quat_w: Tensor,
    joint_pos: Tensor,
    joint_names: Sequence[str],
    terrain: ParallelismTerrain,
    margin_m: float = 0.0,
    lookahead_m: float = 0.0,
) -> Tensor:
    """Return semantic-obstacle collision bits reduced to ``[batch, 4]`` legs.

    The online teacher uses this one-step-late safety signal to hand the
    swing to a support leg that is actually touching an obstacle.  Keeping
    this separate from the scalar reward avoids hiding which leg caused the
    event and prevents a fixed timer from repeatedly lifting the wrong foot.
    """
    backend = get_robot_backend("m1")
    root_pos = torch.as_tensor(root_pos_w, dtype=torch.float32)
    root_quat = torch.as_tensor(root_quat_w, dtype=root_pos.dtype, device=root_pos.device)
    joint = torch.as_tensor(joint_pos, dtype=root_pos.dtype, device=root_pos.device)
    # Probe the live geometry a short distance along the measured heading.
    # This is deliberately separate from ``margin_m``: inflating every
    # collision shape causes the teacher to react to support-ground contacts,
    # whereas a forward probe detects the obstacle before the wheel reaches
    # its leading face and keeps the authored clearance unchanged.
    if float(lookahead_m) > 0.0:
        yaw = extract_yaw_batch(root_quat)
        root_pos = root_pos.clone()
        root_pos[:, 0] = root_pos[:, 0] + float(lookahead_m) * torch.cos(yaw)
        root_pos[:, 1] = root_pos[:, 1] + float(lookahead_m) * torch.sin(yaw)
    planner_joint = select_named_joint_state(joint, source_names=tuple(joint_names), selected_names=backend.planner_joint_names)
    roll, pitch = extract_roll_pitch_batch(root_quat)
    yaw = extract_yaw_batch(root_quat)
    geometry = backend.fk(root_pos, torch.stack((roll, pitch, yaw), dim=-1), planner_joint, capsule_samples=int(backend.cfg.capsule_samples))
    collision_cfg = backend.cfg if float(margin_m) <= 0.0 else dataclass_replace(
        backend.cfg, collision_margin_m=float(margin_m),
    )
    _, bits = backend.collision_mask(terrain, _expand_geometry_for_collision(geometry), collision_cfg)
    return bits.any(dim=(2, 3))


def live_m1_obstacle_proximity_by_leg(
    root_pos_w: Tensor,
    root_quat_w: Tensor,
    joint_pos: Tensor,
    joint_names: Sequence[str],
    terrain: ParallelismTerrain,
    forward_m: float = 0.24,
    lateral_m: float = 0.09,
    rear_forward_extra_m: float = 0.12,
) -> Tensor:
    """Detect semantic-small terrain in a short corridor ahead of each M1 foot.

    This is an anticipatory selector, not a collision/success metric.  It
    samples the live scanner in each foot's lane so the serial teacher can
    lift the threatened leg before the current geometry intersects the block.
    Large semantic obstacles are intentionally excluded; their side-avoidance
    branch remains owned by the environment/policy.
    """
    backend = get_robot_backend("m1")
    root_pos = torch.as_tensor(root_pos_w, dtype=torch.float32)
    root_quat = torch.as_tensor(root_quat_w, dtype=root_pos.dtype, device=root_pos.device)
    joint = torch.as_tensor(joint_pos, dtype=root_pos.dtype, device=root_pos.device)
    planner_joint = select_named_joint_state(
        joint, source_names=tuple(joint_names), selected_names=backend.planner_joint_names,
    )
    roll, pitch = extract_roll_pitch_batch(root_quat)
    yaw = extract_yaw_batch(root_quat)
    geometry = backend.fk(
        root_pos, torch.stack((roll, pitch, yaw), dim=-1), planner_joint,
        capsule_samples=1,
    )
    foot_xy = geometry.foot_pos_w[..., :2]
    heading = torch.stack((yaw.cos(), yaw.sin()), dim=-1)
    lateral = torch.stack((-heading[:, 1], heading[:, 0]), dim=-1)
    sample_x = torch.linspace(
        0.04, max(float(forward_m), 0.04), 6,
        dtype=foot_xy.dtype, device=foot_xy.device,
    )
    sample_y = foot_xy.new_tensor((-float(lateral_m), 0.0, float(lateral_m)))
    leg_extra = foot_xy.new_tensor((0.0, 0.0, float(rear_forward_extra_m), float(rear_forward_extra_m)))
    sample_x_leg = (sample_x[None, None, :] + leg_extra[None, :, None]).clamp_max(
        max(float(forward_m), 0.04) + max(float(rear_forward_extra_m), 0.0)
    )
    # Keep the leg and lateral-sample axes explicit.  The previous expression
    # aligned ``sample_y`` with the xy coordinate axis (2 vs 3), which raised a
    # broadcasting error and was then hidden by the wrapper's safety fallback.
    offsets = heading[:, None, None, None, :] * sample_x_leg[:, :, :, None, None]
    offsets = offsets + lateral[:, None, None, None, :] * sample_y[None, None, None, :, None]
    # [B,4,Sx,Sy,2] -> query batch points.
    query_xy = foot_xy[:, :, None, None, :] + offsets
    from extension.parallelism.terrain import query_height_semantic_valid
    query = query_height_semantic_valid(
        terrain, query_xy.reshape(query_xy.shape[0], -1, 2),
    )
    valid = query.valid.reshape(query_xy.shape[:-1])
    semantic = query.semantic.reshape(query_xy.shape[:-1])
    return (valid & (semantic == 1)).any(dim=(-1, -2))


def m1_policy_geometry_collision_penalty(
    env,
    asset_cfg: SceneEntityCfg = SceneEntityCfg("robot"),
    scanner_cfg: SceneEntityCfg = SceneEntityCfg("semantic_height_scanner"),
) -> Tensor:
    """Return the raw M1 live-policy geometry collision event."""

    robot = env.scene[asset_cfg.name]
    scanner = env.scene[scanner_cfg.name]
    default_device = torch.as_tensor(robot.data.root_pos_w).device
    device = torch.device(getattr(env, "device", default_device))
    root_pos_w = torch.as_tensor(robot.data.root_pos_w, dtype=torch.float32, device=device)
    pattern_cfg = getattr(getattr(scanner, "cfg", None), "pattern_cfg", None)
    resolution = float(getattr(pattern_cfg, "resolution", 0.01))
    terrain = _terrain_from_scanner(scanner, root_pos_w, resolution=resolution)
    # This reward is specifically for hitting semantic obstacles.  The live
    # FK collision checker also detects a leg/body intersecting the ground
    # heightfield, which is useful for planner safety but makes every normal
    # stance look like an obstacle collision (and invalidates every episode).
    # Keep ground contacts available to the planner while masking semantic 0
    # for this M1 episode metric/reward.
    obstacle_mask = terrain.semantic_id > 0
    obstacle_terrain = ParallelismTerrain(
        height_w=torch.where(
            obstacle_mask,
            terrain.height_w,
            torch.full_like(terrain.height_w, -torch.inf),
        ),
        semantic_id=terrain.semantic_id,
        valid_mask=terrain.valid_mask & obstacle_mask,
        origin_w=terrain.origin_w,
        yaw_w=terrain.yaw_w,
        resolution=terrain.resolution,
    )
    return live_m1_policy_geometry_collision_event(
        root_pos_w=root_pos_w,
        root_quat_w=robot.data.root_quat_w,
        joint_pos=robot.data.joint_pos,
        joint_names=tuple(getattr(robot, "joint_names", ())),
        terrain=obstacle_terrain,
    )


__all__ = [
    "live_m1_policy_geometry_collision_by_leg",
    "live_m1_obstacle_proximity_by_leg",
    "live_m1_policy_geometry_collision_event",
    "live_policy_geometry_collision_event",
    "m1_policy_geometry_collision_penalty",
    "parallelism_terrain_from_scan",
    "policy_geometry_collision_penalty",
]
