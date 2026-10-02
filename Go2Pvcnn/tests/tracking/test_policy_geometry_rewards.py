from dataclasses import replace
from types import SimpleNamespace

import torch

import tracking.mdp.policy_geometry_rewards as rewards
from extension.parallelism.collision import official_collision_mask
from extension.parallelism.config import OfficialCollisionShapeSpec, ParallelismCfg
from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES,
    M1_PLANNER_JOINT_NAMES,
)
from extension.parallelism.rl_adapter import select_named_joint_state
from extension.parallelism.types import ParallelismTerrain


def _scan(batch: int = 2, side: int = 5, resolution: float = 0.1) -> torch.Tensor:
    axis = torch.arange(side, dtype=torch.float32) * resolution
    yy, xx = torch.meshgrid(axis, axis, indexing="ij")
    xyz = torch.stack((xx, yy, torch.zeros_like(xx)), dim=-1)
    return xyz.reshape(1, side * side, 3).expand(batch, -1, -1).clone()


def _joint_names() -> tuple[str, ...]:
    return (
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


def test_parallelism_terrain_from_scan_preserves_grid_pose():
    hits = _scan()
    semantic = torch.zeros(2, 5, 5, dtype=torch.long)
    terrain = rewards.parallelism_terrain_from_scan(hits, semantic, None, resolution=0.1)

    assert terrain.height_w.shape == (2, 5, 5)
    assert terrain.semantic_id.shape == (2, 5, 5)
    assert terrain.valid_mask.all()
    assert torch.allclose(terrain.origin_w[:, :2], hits[:, 0, :2])
    assert torch.allclose(terrain.yaw_w, torch.zeros(2))
    assert terrain.resolution == 0.1


def test_parallelism_terrain_from_scan_rejects_nonfinite_hits_despite_explicit_valid_mask():
    hits = _scan(batch=1)
    hits[0, 6, 2] = torch.nan
    hits[0, 18, 2] = torch.inf
    terrain = rewards.parallelism_terrain_from_scan(
        hits,
        torch.zeros(1, 5, 5, dtype=torch.long),
        torch.ones(1, 5, 5, dtype=torch.bool),
        resolution=0.1,
    )

    assert not terrain.valid_mask[0, 1, 1]
    assert not terrain.valid_mask[0, 3, 3]
    assert terrain.valid_mask.sum().item() == 23


def test_terrain_from_elevation_rejects_nonfinite_heights_despite_explicit_valid_mask():
    height = torch.zeros(1, 5, 5)
    height[0, 1, 1] = torch.nan
    height[0, 3, 3] = -torch.inf
    scanner = SimpleNamespace(
        data=SimpleNamespace(
            ray_hits_w=None,
            elevation_map=height,
            semantic_map=torch.zeros(1, 5, 5, dtype=torch.long),
            valid_mask=torch.ones(1, 5, 5, dtype=torch.bool),
        )
    )

    terrain = rewards._terrain_from_scanner(
        scanner, torch.zeros(1, 3), resolution=0.1
    )

    assert not terrain.valid_mask[0, 1, 1]
    assert not terrain.valid_mask[0, 3, 3]
    assert terrain.valid_mask.sum().item() == 23
    assert torch.isfinite(terrain.height_w).all()


def test_live_policy_collision_aggregates_all_legs(monkeypatch):
    bits = torch.zeros(2, 4, 1, 6, dtype=torch.bool)
    bits[1, 2, 0, 1] = True
    monkeypatch.setattr(
        rewards,
        "official_collision_mask",
        lambda terrain, geometry, cfg: (~bits.any(-1), bits),
    )

    event = rewards.live_policy_geometry_collision_event(
        root_pos_w=torch.tensor([[0.0, 0.0, 0.3], [0.0, 0.0, 0.3]]),
        root_quat_w=torch.tensor(
            [[1.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]]
        ),
        joint_pos=torch.zeros(2, 12),
        joint_names=_joint_names(),
        terrain=rewards.parallelism_terrain_from_scan(
            _scan(), torch.zeros(2, 5, 5), None, resolution=0.1
        ),
    )

    assert event.tolist() == [0.0, 1.0]


def test_live_m1_policy_collision_selects_12_planner_joints_by_name(monkeypatch):
    bits = torch.zeros(2, 4, 1, 16, dtype=torch.bool)
    bits[1, 2, 0, 13] = True
    captured = {}

    def fake_fk(root_pos_w, root_rpy_w, joint_pos, capsule_samples):
        captured["joint_pos"] = joint_pos
        return SimpleNamespace(foot_pos_w=torch.zeros(2, 4, 3))

    backend = SimpleNamespace(
        planner_joint_names=M1_PLANNER_JOINT_NAMES,
        cfg=SimpleNamespace(capsule_samples=5),
        fk=fake_fk,
        collision_mask=lambda terrain, geometry, cfg: (~bits.any(-1), bits),
    )
    monkeypatch.setattr(rewards, "get_robot_backend", lambda name: backend)
    monkeypatch.setattr(rewards, "_expand_geometry_for_collision", lambda geometry: geometry)

    joint_pos = torch.arange(32, dtype=torch.float32).reshape(2, 16)
    event = rewards.live_m1_policy_geometry_collision_event(
        root_pos_w=torch.tensor([[0.0, 0.0, 0.5], [0.0, 0.0, 0.5]]),
        root_quat_w=torch.tensor(
            [[1.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]]
        ),
        joint_pos=joint_pos,
        joint_names=M1_ASSET_JOINT_NAMES,
        terrain=rewards.parallelism_terrain_from_scan(
            _scan(), torch.zeros(2, 5, 5), None, resolution=0.1
        ),
    )

    expected = select_named_joint_state(
        joint_pos,
        source_names=M1_ASSET_JOINT_NAMES,
        selected_names=M1_PLANNER_JOINT_NAMES,
    )
    torch.testing.assert_close(captured["joint_pos"], expected)
    assert event.tolist() == [0.0, 1.0]


def test_policy_reward_does_not_require_reference_manager(monkeypatch):
    monkeypatch.setattr(
        rewards,
        "live_policy_geometry_collision_event",
        lambda **kwargs: torch.tensor([0.0, 1.0]),
    )
    robot = SimpleNamespace(
        data=SimpleNamespace(
            root_pos_w=torch.zeros(2, 3),
            root_quat_w=torch.tensor([[1.0, 0.0, 0.0, 0.0]]).expand(2, -1),
            joint_pos=torch.zeros(2, 12),
        ),
        joint_names=_joint_names(),
    )
    scanner = SimpleNamespace(
        cfg=SimpleNamespace(pattern_cfg=SimpleNamespace(resolution=0.1)),
        data=SimpleNamespace(
            ray_hits_w=_scan(),
            semantic_map=torch.zeros(2, 5, 5),
            valid_mask=None,
        ),
    )
    env = SimpleNamespace(
        scene={"robot": robot, "semantic_height_scanner": scanner}
    )

    result = rewards.policy_geometry_collision_penalty(
        env,
        asset_cfg=SimpleNamespace(name="robot"),
        scanner_cfg=SimpleNamespace(name="semantic_height_scanner"),
    )

    assert result.tolist() == [0.0, 1.0]


def test_policy_reward_source_has_no_reference_manager_dependency():
    from pathlib import Path

    source_path = Path(__file__).resolve().parents[2] / "tracking" / "mdp" / "policy_geometry_rewards.py"
    source = source_path.read_text()
    assert "get_parallelism_reference_manager" not in source
    assert "tracking.managers" not in source


def test_real_m1_geometry_accepts_support_contact_and_rejects_tall_obstacle():
    from extension.parallelism.m1_kinematics import M1_DEFAULT_ASSET_JOINT_POS, M1_ROOT_Z_M
    side, resolution = 41, 0.1
    hits = _scan(3, side, resolution)
    hits[..., :2] -= 2.0
    # Case 1 flat; case 2 raised small platform with robot on top;
    # case 3 a tall obstacle intersecting the default standing robot.
    hits[1, :, 2] = .15
    hits[2, :, 2] = .8
    terrain = rewards.parallelism_terrain_from_scan(hits, torch.zeros(3, side, side), None, resolution=resolution)
    events = rewards.live_m1_policy_geometry_collision_event(
        root_pos_w=torch.tensor([[0., 0., M1_ROOT_Z_M], [0., 0., M1_ROOT_Z_M + .15], [0., 0., M1_ROOT_Z_M]]),
        root_quat_w=torch.tensor([[1., 0., 0., 0.]]).expand(3, -1),
        joint_pos=torch.tensor(M1_DEFAULT_ASSET_JOINT_POS).expand(3, -1),
        joint_names=M1_ASSET_JOINT_NAMES, terrain=terrain,
    )
    assert events.tolist() == [0., 0., 1.]


def test_support_wheel_allows_small_semantic_contact_but_rejects_large_semantic_contact():
    """A rolling wheel must meet a small obstacle face without earning a body-collision penalty."""

    wheel = OfficialCollisionShapeSpec(
        "wheel", None, "foot", (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0, 0.0), "cylinder", radius_m=0.1, height_m=0.05,
    )
    cfg = replace(
        ParallelismCfg(),
        official_collision_shapes=(wheel,),
        contact_tolerant_collision_shape_names=(),
        contact_tolerant_support_shape_names=("wheel",),
        contact_tolerant_support_semantic_ids=(1,),
        cylinder_angles=12,
    )
    # Both cases have flat support below the wheel and a 0.10m vertical face
    # at the leading sample. Only the semantic class differs.
    height = torch.zeros(2, 5, 5)
    semantic = torch.zeros(2, 5, 5, dtype=torch.long)
    height[:, 2, 3] = 0.1
    semantic[0, 2, 3] = 1
    semantic[1, 2, 3] = 2
    terrain = ParallelismTerrain(
        height_w=height,
        semantic_id=semantic,
        valid_mask=torch.ones_like(height, dtype=torch.bool),
        origin_w=torch.tensor([[-0.2, -0.2, 0.0]]).expand(2, -1),
        yaw_w=torch.zeros(2),
        resolution=0.1,
    )
    geometry = SimpleNamespace(
        foot_pos_w=torch.tensor([[[[[0.0, 0.0, 0.1]]]]]).expand(2, -1, -1, -1, -1),
        foot_rot_w=torch.eye(3).reshape(1, 1, 1, 1, 3, 3).expand(2, -1, -1, -1, -1, -1),
    )

    def two_wheel_points(specs, config, *, dtype, device):
        del specs, config
        points = torch.tensor([[[0.0, 0.0, -0.1], [0.1, 0.0, 0.0]]], dtype=dtype, device=device)
        return points, torch.ones(1, 2, dtype=torch.bool, device=device)

    valid, bits = official_collision_mask(
        terrain, geometry, cfg, surface_points_builder=two_wheel_points,
    )
    # Semantic-small side contact is a collision; only the lowest ground
    # support point is tolerant. Large semantic contact remains a collision.
    assert valid[:, 0, 0].tolist() == [False, False]
    assert bits[:, 0, 0, 0].tolist() == [True, True]


def test_isaac_x_major_scanner_maps_obstacles_to_the_correct_world_location():
    from extension.parallelism.terrain import query_height_semantic_valid
    axis = torch.arange(5) * .1
    xx, yy = torch.meshgrid(axis, axis, indexing="ij")
    height = torch.zeros_like(xx)
    height[3, 1] = .8
    semantic = torch.zeros(1, 5, 5)
    semantic[0, 3, 1] = 2
    hits = torch.stack((xx, yy, height), -1).reshape(1, 25, 3)
    terrain = rewards.parallelism_terrain_from_scan(hits, semantic, None, resolution=.1)
    query = query_height_semantic_valid(terrain, torch.tensor([[[.3, .1], [.1, .3]]]))
    assert query.valid.tolist() == [[True, True]]
    assert query.semantic.tolist() == [[2, 0]]
    torch.testing.assert_close(query.height, torch.tensor([[.8, 0.]]))


def test_invalid_scanner_cells_are_unknown_not_collision():
    """Out-of-range/invalid scan cells must not become body collision events."""
    wheel = OfficialCollisionShapeSpec(
        "wheel", None, "foot", (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0, 0.0), "cylinder", radius_m=0.1, height_m=0.05,
    )
    cfg = replace(ParallelismCfg(), official_collision_shapes=(wheel,), cylinder_angles=8)
    terrain = ParallelismTerrain(
        height_w=torch.zeros(1, 3, 3),
        semantic_id=torch.zeros(1, 3, 3, dtype=torch.long),
        valid_mask=torch.zeros(1, 3, 3, dtype=torch.bool),
        origin_w=torch.tensor([[-0.1, -0.1, 0.0]]),
        yaw_w=torch.zeros(1),
        resolution=0.1,
    )
    geometry = SimpleNamespace(
        foot_pos_w=torch.tensor([[[[[0.0, 0.0, 0.0]]]]]),
        foot_rot_w=torch.eye(3).reshape(1, 1, 1, 1, 3, 3),
    )
    valid, bits = official_collision_mask(terrain, geometry, cfg)
    assert bool(valid.all())
    assert not bool(bits.any())


def test_support_wheel_does_not_exempt_semantic_two_flat_top():
    """The support exemption is for ground/small support, never large-obstacle tops."""
    wheel = OfficialCollisionShapeSpec(
        "wheel", None, "foot", (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0, 0.0), "cylinder", radius_m=0.1, height_m=0.05,
    )
    cfg = replace(
        ParallelismCfg(),
        official_collision_shapes=(wheel,),
        contact_tolerant_collision_shape_names=(),
        contact_tolerant_support_shape_names=("wheel",),
        contact_tolerant_support_semantic_ids=(1,),
        cylinder_angles=8,
    )
    terrain = ParallelismTerrain(
        height_w=torch.full((1, 5, 5), 0.10),
        semantic_id=torch.full((1, 5, 5), 2, dtype=torch.long),
        valid_mask=torch.ones(1, 5, 5, dtype=torch.bool),
        origin_w=torch.tensor([[-0.2, -0.2, 0.0]]),
        yaw_w=torch.zeros(1),
        resolution=0.1,
    )
    geometry = SimpleNamespace(
        foot_pos_w=torch.tensor([[[[[0.0, 0.0, 0.10]]]]]),
        foot_rot_w=torch.eye(3).reshape(1, 1, 1, 1, 3, 3),
    )
    valid, bits = official_collision_mask(terrain, geometry, cfg)
    assert not bool(valid.all())
    assert bool(bits.any())
