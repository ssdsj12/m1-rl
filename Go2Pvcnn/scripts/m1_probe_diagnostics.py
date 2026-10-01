"""Diagnostic-only event extraction; never changes a reward or collider."""
import torch

from extension.parallelism.m1_collision import _quat_to_matrix
from extension.parallelism.terrain import query_height_semantic_valid


def knee_hit_records(robot, sensor, geometry, terrain, backend, bits, *, step, env_origins, limit):
    if limit <= 0:
        return []
    specs = backend.cfg.official_collision_shapes
    points_l, point_mask = backend.surface_points_builder(
        specs, backend.cfg, dtype=geometry.calf_pos_w.dtype, device=geometry.calf_pos_w.device,
    )
    result = []
    for shape_index, spec in enumerate(specs):
        if not spec.name.endswith("_knee_box"):
            continue
        leg = ("FL", "FR", "RL", "RR").index(spec.leg_name)
        hit_envs = torch.where(bits[:, leg, 0, shape_index])[0].tolist()
        if not hit_envs:
            continue
        rotation = geometry.calf_rot_w[:, leg]
        position = geometry.calf_pos_w[:, leg]
        world_points = torch.matmul(rotation[:, None], points_l[shape_index][None, :, :, None]).squeeze(-1) + position[:, None]
        query = query_height_semantic_valid(terrain, world_points[..., :2])
        hits = point_mask[shape_index][None] & (
            ~query.valid | (query.height >= world_points[..., 2] - backend.cfg.collision_margin_m)
        )
        name = spec.name.split("_", 1)[0] + "_KNEE_LINK"
        robot_index = tuple(robot.body_names).index(name)
        sensor_index = tuple(sensor.body_names).index(name)
        for env_index in hit_envs:
            indices = torch.where(hits[env_index])[0]
            if not indices.numel():
                raise AssertionError("Shape collision did not reconstruct to any surface sample")
            actual_pos = robot.data.body_link_pos_w[env_index, robot_index]
            actual_quat = robot.data.body_link_quat_w[env_index, robot_index]
            actual_rot = _quat_to_matrix(actual_quat)

            def data(value):
                return value.detach().cpu().tolist()

            result.append({
                "step": step, "env": env_index, "shape": spec.name,
                "env_origin_w": data(env_origins[env_index]),
                "hit_sample_indices": data(indices),
                "points_l": data(points_l[shape_index, indices]),
                "points_w": data(world_points[env_index, indices]),
                "terrain_height_m": data(query.height[env_index, indices]),
                "terrain_semantic": data(query.semantic[env_index, indices]),
                "terrain_valid": data(query.valid[env_index, indices]),
                "terrain_gap_m": data(query.height[env_index, indices] - world_points[env_index, indices, 2]),
                "body_name": name, "robot_body_index": robot_index, "sensor_body_index": sensor_index,
                "raw_net_force_history_w": data(sensor.data.net_forces_w_history[env_index, :, sensor_index]),
                "fk_link_pos_w": data(position[env_index]), "fk_link_rot_w": data(rotation[env_index]),
                "actual_body_pos_w": data(actual_pos), "actual_body_quat_w": data(actual_quat),
                "actual_body_rot_w": data(actual_rot),
                "fk_position_error_m": float((actual_pos - position[env_index]).norm()),
                "fk_rotation_max_abs_error": float((actual_rot - rotation[env_index]).abs().max()),
            })
            if len(result) >= limit:
                return result
    return result
