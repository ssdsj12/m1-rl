import math
import pytest


def test_reference_flat_counts_are_scaled_only_on_small():
    from ame_baseline.m1_mixed_course import flat_counts
    assert tuple(flat_counts(i)[0] for i in range(10)) == (15,45,60,75,90,105,120,135,150,165)
    assert tuple(flat_counts(i)[1] for i in range(10)) == (0,1,1,1,1,1,1,1,2,3)
    for invalid in (-1,10,1.5,True):
        with pytest.raises(ValueError):
            flat_counts(invalid)


@pytest.mark.parametrize('seed', range(20))
def test_maximum_layout_retains_exact_count_and_m1_clearance(seed):
    from ame_baseline.m1_mixed_course import structured_positions
    out = structured_positions(165,3,seed=seed)
    assert len(out['small']) == 165
    assert len(out['large']) == 3
    assert out == structured_positions(165,3,seed=seed)
    objects = [(xy, diameter/math.sqrt(2)) for kind,diameter in [('small',.05),('large',.45)] for xy in out[kind]]
    for i,((x,y),r) in enumerate(objects):
        assert abs(x)+r <= 3.5+1e-8
        assert abs(y)+r <= 3.5+1e-8
        # No shape, including its bounding circle, intrudes into reset square.
        assert math.hypot(max(abs(x)-.85,0),max(abs(y)-.85,0)) >= r-1e-8
        for (ox,oy),other_r in objects[:i]:
            assert math.hypot(x-ox,y-oy) >= r+other_r+.45-1e-8


def test_layout_varies_by_seed_without_reducing_density():
    from ame_baseline.m1_mixed_course import structured_positions
    assert set(structured_positions(15,1,seed=3)['small']) != set(structured_positions(15,1,seed=9)['small'])


def test_impossible_layout_fails_and_zero_count_is_empty():
    from ame_baseline.m1_mixed_course import structured_positions
    assert structured_positions(0,0,seed=0) == {'small':(), 'large':()}
    with pytest.raises(ValueError, match='capacity|fit|space'):
        structured_positions(165,3,seed=0,tile_size=(2.,2.))
    for invalid in (-1,2.5,True):
        with pytest.raises(ValueError):
            structured_positions(invalid,0,seed=0)


def test_structured_strategy_survives_course_curriculum_and_spawns_full_count(monkeypatch):
    from test_semantic_course_curriculum_layout import _install_fake_isaaclab
    _install_fake_isaaclab(monkeypatch)
    from extension.semantic_course import SemanticCourseLayoutCfg,build_course_anchors
    from extension.semantic_curriculum import SemanticObstacleCurriculumCfg,SemanticObstacleCount
    assert 'placement_strategy' in SemanticCourseLayoutCfg.__dataclass_fields__
    cfg=SemanticObstacleCurriculumCfg(plane_counts=(SemanticObstacleCount(165,3),),
        center_safety_half_extent_m=(.85,),min_spacing_clearance_m=(.45,),tile_margin_m=(.5,))
    anchors=build_course_anchors([[[0.,0.,0.]]],tile_size=(8.,8.),terrain_names=('flat',),
        semantic_curriculum_cfg=cfg,layout_cfg=SemanticCourseLayoutCfg(placement_strategy='m1_structured',small_shape_pool=('cuboid','cylinder')),
        scale_profile_overrides={'small':(.05,.10),'large':(.45,.55)})
    assert len(anchors)==168
    assert sum(x.semantic_class=='small' for x in anchors)==165
    assert len({x.prim_path for x in anchors})==168


def test_training_entry_selects_mixed_profile_before_env_creation():
    from pathlib import Path
    text=(Path(__file__).parents[1]/'scripts/train_m1_cross_large_complex_ame.py').read_text()
    assert 'configure_mixed_terrain(env_cfg)' in text
    assert text.index('configure_mixed_terrain(env_cfg)')<text.index('env = gym.make(')


def test_wrapper_consumes_registry_for_teacher_and_strict_metrics():
    from pathlib import Path
    text=(Path(__file__).parents[1]/'ame_baseline/ame_env_wrapper.py').read_text()
    assert 'CourseRegistry(' in text
    assert 'EncounterCrossingTracker(' in text
    assert 'obstacle_world_xy=course["centers_top"]' in text
    assert 'course["valid"] &= ~done[:, None]' in text
    assert 'mixed-course strict geometry failed' in text


def test_bounded_runtime_probe_checks_geometry_and_does_not_train():
    import ast
    from pathlib import Path
    path=Path(__file__).parents[1]/'scripts/probe_m1_mixed_course.py'
    assert path.is_file()
    text=path.read_text();ast.parse(text)
    assert 'configure_mixed_terrain(cfg)' in text
    assert 'ComputeWorldBound' in text
    assert 'range(2)' in text
    assert 'M1_MIXED_COURSE_RESULT' in text
    assert '.learn(' not in text
    assert 'from extension.semantic_course import terrain_column_names_from_generator' in text
    assert 'M1_MIXED_COURSE_ERROR' in text
    assert 'cfg.curriculum.terrain_levels=None' in text
    assert 'semantic_scan_top_error' in text
