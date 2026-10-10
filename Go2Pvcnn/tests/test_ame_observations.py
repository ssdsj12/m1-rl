from types import SimpleNamespace
from pathlib import Path

import pytest
import torch
import torch.nn.functional as F

from ame_baseline.ame_observations import _quat_apply_inverse, downsampled_ame_scan


def test_training_path_avoids_deprecated_quaternion_api():
    project_root = Path(__file__).parents[1]
    sources = (
        project_root / "ame_baseline" / "ame_observations.py",
        project_root / "go2_pvcnn" / "mdp" / "rewards.py",
        project_root / "go2_pvcnn" / "mdp" / "rewards_new.py",
    )
    for source in sources:
        assert "quat_rotate_inverse" not in source.read_text(), source


def test_inverse_quaternion_rotation_matches_wxyz_convention():
    half_sqrt_two = 2**-0.5
    quat = torch.tensor([[half_sqrt_two, 0.0, 0.0, half_sqrt_two]])
    vec = torch.tensor([[1.0, 0.0, 0.0]])
    out = _quat_apply_inverse(quat, vec)
    assert torch.allclose(out, torch.tensor([[0.0, -1.0, 0.0]]), atol=1e-6)


class _FakeCfg:
    name = "scanner"


class _FakeEnv:
    def __init__(self, num_rays=4):
        side = int(num_rays**0.5) if num_rays == 4 else 1
        hits = torch.zeros(1, num_rays, 3)
        if num_rays == 4:
            hits[0, :, 0] = torch.tensor([-1.0, 1.0, -1.0, 1.0])
            hits[0, :, 1] = torch.tensor([-1.0, -1.0, 1.0, 1.0])
        semantic = torch.tensor([[[0, 1], [2, 0]]]) if num_rays == 4 else torch.zeros(1, 1, num_rays, dtype=torch.long)
        self.scene = SimpleNamespace(
            sensors={
                "scanner": SimpleNamespace(
                    data=SimpleNamespace(
                        ray_hits_w=hits,
                        pos_w=torch.zeros(1, 3),
                        quat_w=torch.tensor([[1.0, 0.0, 0.0, 0.0]]),
                        semantic_map=semantic,
                    )
                )
            }
        )


def test_downsampled_ame_scan_has_xyz_and_one_hot_channels():
    out = downsampled_ame_scan(_FakeEnv(), _FakeCfg(), target_size=2)
    assert out.shape == (1, 6, 2, 2)
    assert torch.equal(out[:, 3:].sum(dim=1), torch.ones(1, 2, 2))
    assert torch.allclose(out[:, :3].mean(), torch.tensor(0.0))


def test_downsampled_ame_scan_rejects_non_square_scan():
    with pytest.raises(ValueError, match="perfect square"):
        downsampled_ame_scan(_FakeEnv(num_rays=3), _FakeCfg(), target_size=2)


def _scan_env(hits, semantic, quat=None):
    sensor = SimpleNamespace(
        data=SimpleNamespace(
            ray_hits_w=hits.reshape(1, -1, 3),
            pos_w=torch.tensor([[0.0, 0.0, 0.6]], dtype=hits.dtype),
            quat_w=torch.tensor([[1.0, 0.0, 0.0, 0.0]]) if quat is None else quat,
            semantic_map=semantic.unsqueeze(0),
        ),
        cfg=SimpleNamespace(ray_alignment="base"),
    )
    return SimpleNamespace(scene=SimpleNamespace(sensors={"scanner": sensor}))


@pytest.mark.parametrize("height", [0.03, 0.06, 0.10])
@pytest.mark.parametrize("center_x", [0.05, 0.101, 0.215, 0.309, 0.417, 0.501, 0.55])
def test_narrow_shifted_obstacles_keep_real_height_in_every_small_cell(height, center_x):
    grid = torch.linspace(-0.75, 0.75, 151)
    x, y = torch.meshgrid(grid, grid, indexing="ij")
    small = ((x - center_x).abs() <= 0.05) & ((y - 0.215).abs() <= 0.09)
    hits = torch.stack((x, y, torch.where(small, height, 0.0)), dim=-1)
    out = downsampled_ame_scan(_scan_env(hits, small.long()), _FakeCfg())
    cells = out[0, 4].bool()
    assert out.shape == (1, 6, 16, 16)
    assert cells.any()
    assert torch.allclose(out[0, 2][cells], torch.full_like(out[0, 2][cells], height - 0.6), atol=1e-6)
    # Finite terrain-only bins retain the former average geometry exactly.
    old_xyz = F.adaptive_avg_pool2d(
        (hits - torch.tensor([0.0, 0.0, 0.6])).permute(2, 0, 1).unsqueeze(0), 16
    )
    assert torch.equal(out[0, :3, ~cells], old_xyz[0, :, ~cells])


def test_obstacle_cell_gathers_coherent_xyz_from_highest_world_z_winning_class():
    # Pitch makes local-Z ordering disagree with world-Z ordering.
    quat = torch.tensor([[torch.cos(torch.tensor(0.3)), 0.0, torch.sin(torch.tensor(0.3)), 0.0]])
    hits = torch.tensor([[[-1.0, 0.1, 0.10], [1.0, 0.2, 0.06]], [[0.0, 0.3, 0.50], [0.5, 0.4, 0.0]]])
    semantic = torch.tensor([[1, 1], [0, 0]])
    out = downsampled_ame_scan(_scan_env(hits, semantic, quat), _FakeCfg(), target_size=1)
    expected = _quat_apply_inverse(quat, hits[0, 0].unsqueeze(0) - torch.tensor([[0.0, 0.0, 0.6]]))
    assert torch.allclose(out[0, :3, 0, 0], expected[0], atol=1e-6)
    assert torch.equal(out[0, 3:, 0, 0], torch.tensor([0.0, 1.0, 0.0]))


def test_large_priority_selects_highest_large_hit_even_below_small_and_ground():
    hits = torch.tensor([[[0.1, 0.2, -0.4], [0.3, 0.4, -0.2]], [[0.5, 0.6, 0.1], [0.7, 0.8, 0.5]]])
    semantic = torch.tensor([[2, 2], [1, 0]])
    out = downsampled_ame_scan(_scan_env(hits, semantic), _FakeCfg(), target_size=1)
    assert torch.allclose(out[0, :3, 0, 0], torch.tensor([0.3, 0.4, -0.8]))
    assert torch.equal(out[0, 3:, 0, 0], torch.tensor([0.0, 0.0, 1.0]))


def test_nonfinite_hits_cannot_win_obstacle_class_or_contaminate_geometry():
    hits = torch.tensor([[[float("nan"), 0.2, 0.9], [0.3, 0.4, float("inf")]], [[0.5, 0.6, 0.03], [0.7, 0.8, 0.0]]])
    semantic = torch.tensor([[2, 2], [1, 0]])
    out = downsampled_ame_scan(_scan_env(hits, semantic), _FakeCfg(), target_size=1)
    assert torch.allclose(out[0, :3, 0, 0], torch.tensor([0.5, 0.6, -0.57]))
    assert torch.equal(out[0, 3:, 0, 0], torch.tensor([0.0, 1.0, 0.0]))


def test_partial_invalid_terrain_averages_only_real_hits():
    hits = torch.tensor([[[float("nan"), 0.0, 0.0], [0.3, 0.4, 0.0]], [[0.5, 0.6, 0.0], [float("inf"), 0.8, 0.0]]])
    out = downsampled_ame_scan(_scan_env(hits, torch.zeros(2, 2, dtype=torch.long)), _FakeCfg(), target_size=1)
    assert torch.allclose(out[0, :3, 0, 0], torch.tensor([0.4, 0.5, -0.6]))
    assert torch.equal(out[0, 3:, 0, 0], torch.tensor([1.0, 0.0, 0.0]))


def test_all_invalid_cell_remains_unknown_with_finite_zero_geometry():
    hits = torch.full((2, 2, 3), float("inf"))
    out = downsampled_ame_scan(_scan_env(hits, torch.full((2, 2), 2)), _FakeCfg(), target_size=1)
    assert torch.equal(out, torch.zeros(1, 6, 1, 1))


def test_pooling_preserves_all_rows_across_environment_chunk_boundary():
    heights = torch.arange(257, dtype=torch.float32) / 1000.0
    env = _scan_env(torch.zeros(2, 2, 3), torch.tensor([[1, 0], [0, 0]]))
    data = env.scene.sensors["scanner"].data
    data.ray_hits_w = data.ray_hits_w.repeat(257, 1, 1)
    data.ray_hits_w[:, 0, 0] = 0.2
    data.ray_hits_w[:, 0, 1] = -0.215
    data.ray_hits_w[:, 0, 2] = heights
    data.pos_w = data.pos_w.repeat(257, 1)
    data.quat_w = data.quat_w.repeat(257, 1)
    data.semantic_map = data.semantic_map.repeat(257, 1, 1)
    out = downsampled_ame_scan(env, _FakeCfg(), target_size=1)
    assert out.shape == (257, 6, 1, 1)
    assert torch.allclose(out[:, 2, 0, 0], heights - 0.6)
    assert torch.equal(out[:, 0, 0, 0], torch.full((257,), 0.2))
    assert torch.equal(out[:, 1, 0, 0], torch.full((257,), -0.215))
    assert torch.equal(out[:, 4, 0, 0], torch.ones(257))


@pytest.mark.parametrize("field", ["pos_w", "quat_w"])
def test_invalid_sensor_pose_marks_entire_scan_unknown(field):
    env = _scan_env(torch.zeros(2, 2, 3), torch.tensor([[1, 0], [2, 0]]))
    getattr(env.scene.sensors["scanner"].data, field)[0, 0] = float("nan")
    out = downsampled_ame_scan(env, _FakeCfg(), target_size=1)
    assert torch.equal(out, torch.zeros(1, 6, 1, 1))
