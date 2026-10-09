import ast
from pathlib import Path
import pytest
from test_semantic_course_curriculum_layout import _install_fake_isaaclab


def test_all_fixed_m1_small_shapes_have_ten_cm_geometric_height(monkeypatch):
    _install_fake_isaaclab(monkeypatch)
    from extension.semantic_course import SemanticCourseLayoutCfg, build_course_anchors, bottom_to_center_offset
    from extension.semantic_curriculum import SemanticObstacleCount, SemanticObstacleCurriculumCfg
    assert 'small_shape_pool' in SemanticCourseLayoutCfg.__dataclass_fields__
    layout = SemanticCourseLayoutCfg(small_shape_pool=('cuboid', 'cylinder'),
        fixed_small_obstacle_local_xy=tuple((.55*(i+1), .215 if i%2==0 else -.215) for i in range(6)),
        center_safety_half_extent_m=.45, min_spacing_clearance_m=.45)
    curriculum = SemanticObstacleCurriculumCfg(plane_counts=(SemanticObstacleCount(6,0),),
        center_safety_half_extent_m=(.45,), min_spacing_clearance_m=(.45,), tile_margin_m=(.50,))
    anchors = build_course_anchors(terrain_origins=[[[0.,0.,0.]]], tile_size=(8.,8.),
        layout_cfg=layout, scale_profile_overrides={'small':(.05,.10)},
        semantic_curriculum_cfg=curriculum, terrain_names=('flat',))
    assert len(anchors)==6
    for a in anchors:
        assert a.shape_kind in ('cuboid','cylinder')
        assert 2*bottom_to_center_offset(a.shape_kind,a.shape_params)==pytest.approx(.10)


def test_m1_course_wires_height_preserving_shapes_and_no_ground_embed():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_ame_env_cfg.py'
    tree = ast.parse(path.read_text())
    layouts = [n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='SemanticCourseLayoutCfg']
    assert any(k.arg=='small_shape_pool' and ast.literal_eval(k.value)==('cuboid','cylinder') for n in layouts for k in n.keywords)
    ground = [n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='SemanticCourseGroundingCfg']
    assert any(k.arg=='embed_depth_m' and ast.literal_eval(k.value)==0.0 for n in ground for k in n.keywords)
