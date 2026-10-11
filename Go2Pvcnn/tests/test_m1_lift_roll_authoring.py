"""Explicit candidate selection; legacy progressive authoring stays unchanged."""
from dataclasses import replace

import pytest


def setup_course(monkeypatch):
    from test_semantic_course_curriculum_layout import _install_fake_isaaclab
    _install_fake_isaaclab(monkeypatch)
    from extension.semantic_course import SemanticCourseLayoutCfg, build_course_anchors
    from extension.semantic_curriculum import SemanticObstacleCurriculumCfg, SemanticObstacleCount
    cfg = SemanticObstacleCurriculumCfg(
        plane_counts=tuple(SemanticObstacleCount(n,large) for n,large in ((0,0),(4,0),(6,0),(8,0),(90,1))),
        min_spacing_clearance_m=(.45,))
    kwargs = dict(terrain_origins=[[[16.*r,16.*c,0.] for c in range(2)] for r in range(5)],
        tile_size=(16.,16.), terrain_names=('flat',), semantic_curriculum_cfg=cfg,
        layout_cfg=SemanticCourseLayoutCfg(placement_strategy='m1_progressive',small_shape_pool=('cuboid','cylinder')),
        scale_profile_overrides={'small':(.05,.10),'large':(.45,.55)})
    return build_course_anchors, kwargs


def test_explicit_candidate_authors_exact_manifest_roles_and_legacy_rows(monkeypatch):
    from ame_baseline.m1_lift_roll_layout import candidate_blocks
    build,kwargs = setup_course(monkeypatch)
    baseline = build(**kwargs)
    kwargs['layout_cfg'] = replace(kwargs['layout_cfg'],placement_strategy='m1_lift_roll')
    actual = build(**kwargs)
    assert [a for a in actual if a.row in (0,4)] == [a for a in baseline if a.row in (0,4)]
    assert len({a.prim_path for a in actual}) == len(actual)
    for row in (1,2,3):
        manifest = candidate_blocks(row,fill_gap=.20)
        for col in (0,1):
            anchors = [a for a in actual if (a.row,a.col)==(row,col)]
            assert len(anchors)==len(manifest)
            for i,(anchor,block) in enumerate(zip(anchors,manifest)):
                assert anchor.slot_index==i
                assert anchor.semantic_class=='small'
                assert anchor.shape_kind=='cuboid'
                assert anchor.shape_params=={'size':(block.length,block.width,block.height)}
                assert anchor.local_xy==(block.x,block.y)
                assert anchor.world_xy==pytest.approx((row*16+block.x,col*16+block.y))
                assert anchor.ground_offset==pytest.approx(block.height/2)
                assert anchor.required_crossing is block.required_crossing
    from extension.semantic_course import ground_course_anchors, SemanticCourseGroundingCfg
    from ame_baseline.m1_course_registry import CourseRegistry
    import torch
    records = ground_course_anchors(actual,terrain_height_at_xy=lambda x,y:0.,
        grounding_cfg=SemanticCourseGroundingCfg(embed_depth_m=0.))
    registry = CourseRegistry(records,rows=5,cols=2,device='cpu')
    tables = registry.for_envs(torch.tensor([1,2,3]),torch.zeros(3,dtype=torch.long))
    assert tables['valid'].sum(-1).tolist()==[4,6,8]
    assert tables['landing_valid'].sum(-1).tolist()==[74,76,78]


@pytest.mark.parametrize('bad', ['tile','fixed','counts'])
def test_candidate_rejects_incompatible_authoring_inputs(monkeypatch,bad):
    build,kwargs = setup_course(monkeypatch)
    cfg = replace(kwargs['layout_cfg'],placement_strategy='m1_lift_roll')
    if bad=='tile':kwargs['tile_size']=(8.,8.)
    if bad=='fixed':cfg=replace(cfg,fixed_small_obstacle_local_xy=((1.,1.),))
    if bad=='counts':
        from extension.semantic_curriculum import SemanticObstacleCount
        kwargs['semantic_curriculum_cfg'].plane_counts=(SemanticObstacleCount(0,0),)*5
    kwargs['layout_cfg']=cfg
    with pytest.raises(ValueError,match='lift-roll'):
        build(**kwargs)
