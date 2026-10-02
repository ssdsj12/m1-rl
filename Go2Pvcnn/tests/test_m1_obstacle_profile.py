from pathlib import Path
import math
import sys
import types
import ast

if "isaaclab.terrains" not in sys.modules:
    isaaclab = sys.modules.setdefault("isaaclab", types.ModuleType("isaaclab"))
    terrains = types.ModuleType("isaaclab.terrains")
    terrains.TerrainImporter = object
    sys.modules["isaaclab.terrains"] = terrains

from extension.semantic_course import SemanticCourseLayoutCfg, build_course_anchors
from extension.semantic_curriculum import SemanticObstacleCount, SemanticObstacleCurriculumCfg


def test_actual_m1_fixed_course_preserves_spacing():
    source = (Path(__file__).resolve().parents[1] / 'ame_baseline/m1_ame_env_cfg.py').read_text()
    constants = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith('M1_FIXED_'):
                    constants[target.id] = ast.literal_eval(node.value)
    small = constants['M1_FIXED_SMALL_OBSTACLE_LOCAL_XY']
    large = constants['M1_FIXED_LARGE_OBSTACLE_LOCAL_XY']
    assert len(small) == 6
    # The first block is intentionally inside the 1.5 m semantic scanner so
    # the teacher can pre-lift; the six-block course then continues at 0.55 m
    # spacing along +X with alternating left/right foot-track targets.
    assert all(0.55 <= x <= 3.30 for x, _ in small)
    assert [y for _, y in small] == [0.20, -0.20, 0.20, -0.20, 0.20, -0.20]
    assert small[0][0] == 0.55
    curriculum = SemanticObstacleCurriculumCfg(
        plane_counts=(SemanticObstacleCount(small=6, large=2),),
        non_plane_counts=(SemanticObstacleCount(small=6, large=2),),
        center_safety_half_extent_m=(0.45,), min_spacing_clearance_m=(0.45,),
        tile_margin_m=(0.50,),
    )
    anchors = build_course_anchors(
        [[(0., 0., 0.)]], tile_size=(8., 8.),
        semantic_curriculum_cfg=curriculum,
        layout_cfg=SemanticCourseLayoutCfg(fixed_small_obstacle_local_xy=small,
                                          fixed_large_obstacle_local_xy=large),
        scale_profile_overrides={'small': (.08, .10), 'large': (.45, .55)},
    )
    assert len(anchors) == 8


def test_m1_profile_builds_ten_centimetre_obstacles_with_foothold_spacing():
    curriculum = SemanticObstacleCurriculumCfg(
        plane_terrain_names=("flat",),
        plane_counts=(SemanticObstacleCount(small=10, large=0),),
        non_plane_counts=(SemanticObstacleCount(small=10, large=0),),
        center_safety_half_extent_m=(0.45,),
        min_spacing_clearance_m=(0.80,),
        tile_margin_m=(0.50,),
    )
    anchors = build_course_anchors(
        [[(0.0, 0.0, 0.0)]],
        tile_size=(8.0, 8.0),
        terrain_names=("flat",),
        semantic_curriculum_cfg=curriculum,
        layout_cfg=SemanticCourseLayoutCfg(
            center_safety_half_extent_m=0.45,
            min_spacing_clearance_m=0.80,
        ),
        scale_profile_overrides={"small": (0.05, 0.10)},
    )
    assert len(anchors) == 10
    assert all(math.isclose(anchor.target_height, 0.10) for anchor in anchors)
    assert all(math.hypot(*anchor.local_xy) > 0.45 for anchor in anchors)
    for left_index, left in enumerate(anchors):
        for right in anchors[left_index + 1 :]:
            assert math.dist(left.local_xy, right.local_xy) >= 0.90


def test_m1_config_declares_m1_obstacle_profile_and_collision_reward():
    root = Path(__file__).resolve().parents[1]
    source = (root / "ame_baseline" / "m1_ame_env_cfg.py").read_text(encoding="utf-8")
    assert "semantic_course_scale_profile_overrides" in source
    assert '"small": (0.05, 0.10)' in source
    assert "m1_obstacle_collision_penalty" in source
    assert "stage_small, stage_large = 6, 0" in source


def test_m1_layout_policy_requires_foothold_clearance():
    root = Path(__file__).resolve().parents[1]
    source = (root / "ame_baseline" / "m1_ame_env_cfg.py").read_text(encoding="utf-8")
    assert "center_safety_half_extent_m = (0.45,)" in source
    assert "min_spacing_clearance_m = (0.45,)" in source


def test_m1_teacher_has_runtime_course_obstacle_trigger():
    root = Path(__file__).resolve().parents[1]
    source = (root / "ame_baseline" / "ame_env_wrapper.py").read_text(encoding="utf-8")
    assert "_m1_fixed_obstacle_proximity_from_foot_xy" in source
    assert "reference[\"collision_leg_mask\"] = collision_mask | proximity_mask | fixed_mask" in source
    assert "M1_FIXED_SMALL_OBSTACLE_LOCAL_XY" in source
    assert "M1_TEACHER_STRICT_SEQUENCE" in source


def test_generic_course_keeps_legacy_small_obstacle_height():
    from extension.semantic_course import SMALL_OBSTACLE_HEIGHT
    assert SMALL_OBSTACLE_HEIGHT == 0.16
