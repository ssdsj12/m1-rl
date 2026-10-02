"""CPU contracts for the diagnostic-only contact event recorder."""
from types import SimpleNamespace
import ast
from pathlib import Path

import torch

from extension.parallelism.robot_backend import get_robot_backend
from extension.parallelism.types import ParallelismTerrain


def test_knee_events_record_surface_indices_and_use_independent_body_orders():
    from scripts.m1_probe_diagnostics import knee_hit_records

    backend = get_robot_backend("m1")
    batch = 2
    calf_pos = torch.zeros(batch, 4, 3)
    calf_pos[..., 2] = 1.
    calf_pos[0, 0, 2] = .2
    calf_pos[1, :, 0] = 10.
    rotation = torch.eye(3).expand(batch, 4, 3, 3).clone()
    geometry = SimpleNamespace(calf_pos_w=calf_pos, calf_rot_w=rotation)
    terrain = ParallelismTerrain(
        height_w=torch.zeros(batch, 11, 11),
        semantic_id=torch.zeros(batch, 11, 11, dtype=torch.long),
        valid_mask=torch.ones(batch, 11, 11, dtype=torch.bool),
        origin_w=torch.tensor([[-.5, -.5, 0.], [9.5, -.5, 0.]]),
        yaw_w=torch.zeros(batch), resolution=.1,
    )
    bits = torch.zeros(batch, 4, 1, len(backend.cfg.official_collision_shapes), dtype=torch.bool)
    shape_index = next(i for i, s in enumerate(backend.cfg.official_collision_shapes) if s.name == "FBL_knee_box")
    bits[0, 0, 0, shape_index] = True
    robot = SimpleNamespace(
        body_names=["FBL_KNEE_LINK", "FAR_KNEE_LINK"],
        data=SimpleNamespace(
            body_link_pos_w=calf_pos[:, :2],
            body_link_quat_w=torch.tensor([1., 0., 0., 0.]).expand(batch, 2, 4),
        ),
    )
    history = torch.zeros(batch, 3, 2, 3)
    history[0, :, 0, 0] = 999.  # FAR in sensor order; must not label it FBL.
    history[0, :, 1, 0] = 7.
    sensor = SimpleNamespace(
        body_names=["FAR_KNEE_LINK", "FBL_KNEE_LINK"],
        data=SimpleNamespace(net_forces_w_history=history),
    )
    records = knee_hit_records(
        robot, sensor, geometry, terrain, backend, bits,
        step=30, env_origins=torch.tensor([[0., 0., 0.], [10., 0., 0.]]), limit=16,
    )
    assert len(records) == 1
    event = records[0]
    assert event["env"] == 0 and event["step"] == 30
    assert event["shape"] == "FBL_knee_box"
    assert max(event["hit_sample_indices"]) > 3  # Not a leg index from the shape-level bit mask.
    assert len(event["points_l"]) == len(event["hit_sample_indices"])
    assert event["sensor_body_index"] == 1 and event["robot_body_index"] == 0
    assert event["raw_net_force_history_w"] == [[7., 0., 0.]] * 3
    assert event["fk_position_error_m"] == 0.
    assert event["fk_rotation_max_abs_error"] == 0.
    assert all(z == 0. for z in event["terrain_height_m"])
    assert all(event["terrain_valid"])


def test_probe_uses_isolated_evaluation_spacing_for_full_traversal():
    tree = ast.parse((Path(__file__).resolve().parents[1] / "scripts/probe_m1_rewards.py").read_text())
    spacing = [node.value.value for node in ast.walk(tree)
               if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
               and any(ast.unparse(target) == "cfg.scene.env_spacing" for target in node.targets)]
    assert spacing and spacing[-1] >= 8.0, "The 600-step probe must not scan a neighbor's box at x=3.5m"
