"""Fill is physical geometry, but not a mandatory single-wheel target."""
from dataclasses import replace
from types import SimpleNamespace

import pytest
import torch

from ame_baseline.m1_course_registry import CourseRegistry
from ame_baseline.m1_required_crossing import progressive_required_wheels


def obstacle(slot=0, y=.215, role=True):
    return SimpleNamespace(row=1, col=0, slot_index=slot, semantic_class='small',
        shape_kind='cuboid', shape_params={'size': (.10, .18, .03)},
        world_center=(0., y, .015), required_crossing=role)


def course(objects):
    return CourseRegistry(objects, rows=5, cols=1, device='cpu').for_envs(
        torch.tensor([1]), torch.tensor([0]))


def test_offtrack_fill_is_not_a_required_target_but_remains_landing_geometry():
    c = course([obstacle(), obstacle(1, 1., False)])
    assert c['valid'].sum().item() == 1
    assert c['landing_valid'].sum().item() == 2
    assert progressive_required_wheels(c, torch.zeros(1)).tolist() == [[[True, False, True, False]]]
    wheels = torch.tensor([[[0., 1., .12], [-1., -.215, .12],
                            [-1.659, .215, .12], [-1.659, -.215, .12]]])
    offset = (wheels[:, :, None, :2] - c['landing_centers_top'][:, None, :, :2]).abs() - c['landing_half_extents'][:, None]
    distance = torch.linalg.vector_norm(offset.clamp_min(0), dim=-1)
    landing_free = ~((distance < .119208) & c['landing_valid'][:, None]).any(-1).any(-1)
    assert landing_free.tolist() == [False]


def test_legacy_missing_or_none_roles_remain_targets():
    a, b = obstacle(role=None), obstacle(1, -.215)
    del b.required_crossing
    c = course([a, b])
    assert c['valid'].sum().item() == 2
    assert c['landing_valid'].sum().item() == 2


@pytest.mark.parametrize('bad', [0, 1, 'fill', [], {}])
def test_invalid_roles_fail_closed(bad):
    with pytest.raises(ValueError, match='required_crossing'):
        course([obstacle(role=bad)])


def test_fill_only_tile_has_no_phantom_target():
    c = course([obstacle(0, 1., False)])
    assert not c['valid'].any()
    assert c['landing_valid'].sum().item() == 1


@pytest.mark.parametrize('world_query', [False, True])
def test_both_grounding_paths_preserve_roles_and_physical_shape(monkeypatch, world_query):
    from test_semantic_course_curriculum_layout import _install_fake_isaaclab
    _install_fake_isaaclab(monkeypatch)
    import extension.semantic_course as sc
    anchor = sc.CourseAnchor(row=1, col=0, stage=sc.SemanticCourseStage.S1,
        semantic_class='small', slot_index=0, shape_kind='cuboid',
        shape_params={'size': (.10, .18, .03)}, target_diameter=.18,
        target_height=.03, ground_offset=.015, local_xy=(0., .215),
        world_xy=(16., .215), prim_path='/World/small/0', required_crossing=True)
    fill = replace(anchor, slot_index=1, local_xy=(0., 1.), world_xy=(16., 1.),
                   prim_path='/World/small/1', required_crossing=False)
    legacy = replace(anchor, slot_index=2, required_crossing=None)
    anchors = [anchor, fill, legacy]
    if world_query:
        monkeypatch.setattr(sc, '_sample_terrain_heights_world',
                            lambda xy_points, **kwargs: [0.] * len(xy_points))
        objects = sc._ground_with_runtime_terrain_sampler(anchors, device='cpu')
    else:
        objects = sc.ground_course_anchors(anchors, terrain_height_at_xy=lambda x, y: 0.)
    assert [o.required_crossing for o in objects] == [True, False, None]
    assert all(o.semantic_class == 'small' for o in objects)
    assert all(o.shape_params == anchor.shape_params for o in objects)
    assert [o.world_center[:2] for o in objects] == [a.world_xy for a in anchors]
