import torch
import pytest

from extension.batch_mpc_planner.config import MpcPlannerCfg
from extension.batch_mpc_planner.semantic_policy import (
    SemanticObstacleMode,
    classify_semantic_obstacle_mode,
)
from extension.batch_mpc_planner.types import MpcPlannerTerrain, MpcRobotState


def test_m1_semantic_course_uses_configured_small_obstacle_height():
    height = torch.zeros((1, 41, 41), dtype=torch.float32)
    semantic = torch.zeros_like(height, dtype=torch.long)
    semantic[0, 20, 25] = 1
    terrain = MpcPlannerTerrain(
        height_map=height,
        semantic_map=semantic,
        world_x_range=(-2.0, 2.0),
        world_y_range=(-2.0, 2.0),
    )
    state = MpcRobotState(
        root_pos=torch.tensor([[0.0, 0.0, 0.55]]),
        root_rpy=torch.zeros((1, 3)),
        foot_pos=torch.zeros((1, 4, 3)),
        joint_angles=torch.zeros((1, 12)),
    )
    cfg = MpcPlannerCfg()
    cfg.runtime.robot_name = "m1"
    cfg.runtime.semantic_small_obstacle_height_m = 0.10
    policy = classify_semantic_obstacle_mode(
        terrain, state, torch.tensor([[0.2, 0.0, 0.0]]), cfg,
    )
    assert policy.mode.item() == int(SemanticObstacleMode.LOW_SMALL_FORWARD)
    assert policy.obstacle_height.item() == pytest.approx(0.10, abs=1e-6)


def test_flat_generic_semantic_course_keeps_zero_height_without_override():
    height = torch.zeros((1, 21, 21), dtype=torch.float32)
    semantic = torch.zeros_like(height, dtype=torch.long)
    semantic[0, 10, 13] = 1
    terrain = MpcPlannerTerrain(
        height_map=height,
        semantic_map=semantic,
        world_x_range=(-1.0, 1.0),
        world_y_range=(-1.0, 1.0),
    )
    state = MpcRobotState(
        root_pos=torch.tensor([[0.0, 0.0, 0.55]]),
        root_rpy=torch.zeros((1, 3)),
        foot_pos=torch.zeros((1, 4, 3)),
        joint_angles=torch.zeros((1, 12)),
    )
    policy = classify_semantic_obstacle_mode(
        terrain, state, torch.tensor([[0.2, 0.0, 0.0]]), MpcPlannerCfg(),
    )
    assert policy.obstacle_height.item() == pytest.approx(0.0, abs=1e-6)
