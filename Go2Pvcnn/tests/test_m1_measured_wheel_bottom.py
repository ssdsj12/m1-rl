import math
from pathlib import Path
import pytest
import torch
from ame_baseline import m1_crossing_clearance as clearance
from ame_baseline.m1_strict_crossing import StrictCrossingTracker


def test_mesh_bottom_preserves_offset_tilt_and_translation():
    fn = getattr(clearance, 'wheel_bottom_from_vertices', None)
    assert callable(fn), 'measured wheel bottom must come from oriented collision geometry'
    vertices = torch.tensor([[[0., -.02, -.09], [0., .03, .09]]]).expand(4, -1, -1)
    positions = torch.tensor([[[0., 0., .25]]]).expand(2, 4, 3)
    quats = torch.tensor([[[1., 0., 0., 0.]],
                          [[math.sqrt(.5), math.sqrt(.5), 0., 0.]]]).expand(2, 4, 4)
    bottom = fn(positions, quats, vertices)
    torch.testing.assert_close(bottom[0], torch.full((4,), .16))
    torch.testing.assert_close(bottom[1], torch.full((4,), .23))
    with pytest.raises(ValueError):
        fn(positions, torch.zeros_like(quats), vertices)


def test_tracker_cannot_replace_measured_low_bottom_with_center_minus_radius():
    tracker = StrictCrossingTracker(1, 'cpu', obstacle_count=1)
    wheels = torch.tensor([[[.55, .215, .231], [.2,-.215,.096],
                            [-.2,.215,.096],[-.2,-.215,.096]]])
    kwargs = dict(wheel_pos_w=wheels,
        obstacle_centers_top_w=torch.tensor([[[.55,.215,.10]]]),
        support_safe=torch.tensor([True]),touchdown_safe=torch.tensor([False]),
        collision=torch.tensor([False]),wheel_horizontal_radius=.12,
        wheel_lateral_half_width=.03,wheel_vertical_radius=.096,
        obstacle_half_extents=(.025,.025),required_clearance=.03)
    # Fixed radius reports35mm, but the actual tilted geometry has only29mm.
    result = tracker.update(**kwargs, wheel_bottom_z_w=torch.tensor([[.129,0.,0.,0.]]))
    assert not result['clearance_latched'].item()
    result = tracker.update(**kwargs, wheel_bottom_z_w=torch.tensor([[.131,0.,0.,0.]]))
    assert result['clearance_latched'].item()


def test_invalid_bottom_input_is_rejected_not_replaced():
    tracker = StrictCrossingTracker(1, 'cpu', obstacle_count=1)
    with pytest.raises(ValueError, match='bottom'):
        tracker.update(wheel_pos_w=torch.zeros(1,4,3),
            obstacle_centers_top_w=torch.zeros(1,1,3),support_safe=torch.tensor([True]),
            touchdown_safe=torch.tensor([False]),collision=torch.tensor([False]),
            wheel_horizontal_radius=.12,wheel_lateral_half_width=.03,
            wheel_vertical_radius=.096,obstacle_half_extents=(.025,.025),
            wheel_bottom_z_w=torch.full((1,4),float('nan')))


def test_runtime_passes_measured_mesh_bottom_to_tracker():
    source = (Path(__file__).parents[1]/'ame_baseline/ame_env_wrapper.py').read_text()
    assert 'wheel_bottom_from_vertices(' in source
    assert 'load_wheel_collision_vertices(' in source
    assert 'wheel_bottom_z_w=wheel_bottom_z_w' in source


def test_extreme_vertex_reduction_preserves_all_direction_support():
    import itertools
    reduce = getattr(clearance, 'wheel_extreme_vertices', None)
    assert callable(reduce), 'dense USD meshes must not expand per training environment'
    corners = torch.tensor(list(itertools.product((-1.,1.),repeat=3)),dtype=torch.float64)
    generator=torch.Generator().manual_seed(12)
    interior=torch.rand(1000,3,generator=generator,dtype=torch.float64)*1.9-.95
    dense=torch.cat((corners,interior,corners))
    reduced=torch.tensor(reduce(dense.tolist()),dtype=torch.float64)
    assert reduced.shape == (8,3)
    directions=torch.randn(99,3,generator=generator,dtype=torch.float64)
    torch.testing.assert_close((directions@dense.T).amin(-1),
                               (directions@reduced.T).amin(-1))
