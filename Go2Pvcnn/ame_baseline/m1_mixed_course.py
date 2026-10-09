"""M1-only mixed-course counts and footprint-safe deterministic placement.

This is geometry, not a certificate of dynamic support or physical crossing.
The pinned reference default train defines ten difficulty rows. Only flat
small counts are scaled; all other obstacle counts remain reference values.
"""
from __future__ import annotations

import math
import random

REFERENCE_FLAT_SMALL = (10,30,40,50,60,70,80,90,100,110)
REFERENCE_FLAT_LARGE = (0,1,1,1,1,1,1,1,2,3)
REFERENCE_NONPLANE_SMALL = (0,0,1,1,2,2,3,3,4,4)
REFERENCE_NONPLANE_LARGE = (0,0,0,0,0,0,1,1,1,1)


def _integer(value, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def flat_counts(row: int) -> tuple[int, int]:
    row = _integer(row, 'row')
    if row >= len(REFERENCE_FLAT_SMALL):
        raise ValueError('row must be in [0,10)')
    return (REFERENCE_FLAT_SMALL[row] * 3 // 2, REFERENCE_FLAT_LARGE[row])


def configure_mixed_terrain(cfg):
    """Apply only the approved terrain/course profile, after M1 post-init.

    The shared M1 config remains usable for explicit fixed-course diagnostics;
    production train selects this profile before creating the environment.
    """
    import copy
    from extension.semantic_course import SemanticCourseLayoutCfg, SemanticCourseGroundingCfg
    from extension.semantic_curriculum import SemanticObstacleCount, SemanticObstacleCurriculumCfg
    from go2_pvcnn.tasks.teacher_elevation_trajectory_mpc_semantic_env_cfg import (
        SEMANTIC_TERRAIN_CFG, TeacherElevationTrajectoryMpcSemanticCurriculumCfg,
    )
    if cfg.robot_name != 'm1' or cfg.action_dim != 16:
        raise ValueError('mixed M1 terrain requires M1 with16actions')
    cfg.m1_course_profile = 'mixed'
    cfg.scene.terrain.terrain_generator = copy.deepcopy(SEMANTIC_TERRAIN_CFG)
    cfg.semantic_obstacle_curriculum = SemanticObstacleCurriculumCfg(
        plane_terrain_names=('flat',),
        plane_counts=tuple(SemanticObstacleCount(*flat_counts(i)) for i in range(10)),
        non_plane_counts=tuple(SemanticObstacleCount(a,b) for a,b in zip(REFERENCE_NONPLANE_SMALL,REFERENCE_NONPLANE_LARGE)),
        terrain_obstacle_count_overrides={},center_safety_half_extent_m=(.85,),
        min_spacing_clearance_m=(.45,),tile_margin_m=(.5,),
    )
    cfg.scene.terrain.semantic_obstacle_curriculum = cfg.semantic_obstacle_curriculum
    cfg.scene.terrain.semantic_course_layout_cfg = SemanticCourseLayoutCfg(
        placement_strategy='m1_structured',small_shape_pool=('cuboid','cylinder'),
        center_safety_half_extent_m=.85,min_spacing_clearance_m=.45,tile_margin_m=.5,
    )
    cfg.scene.terrain.semantic_course_scale_profile_overrides={'small':(.05,.10),'large':(.45,.55)}
    cfg.scene.terrain.semantic_course_grounding_cfg=SemanticCourseGroundingCfg(embed_depth_m=0.)
    cfg.curriculum.terrain_levels=copy.deepcopy(TeacherElevationTrajectoryMpcSemanticCurriculumCfg().terrain_levels)
    cfg.commands.base_velocity.ranges.lin_vel_x=(.18,.45)
    cfg.commands.base_velocity.ranges.lin_vel_y=(-.04,.04)
    cfg.commands.base_velocity.ranges.ang_vel_z=(-.15,.15)
    cfg.events.reset_base.params['pose_range']={'x':(-.2,.2),'y':(-.2,.2),'yaw':(-math.pi,math.pi)}


def structured_positions(
    small_count: int, large_count: int, *, seed: int,
    tile_size=(8.,8.), small_diameter=.05, large_diameter=.45,
    gap=.45, safety=.85, margin=.5,
) -> dict[str, tuple[tuple[float, float], ...]]:
    """Place exact counts without weakening spacing when random packing jams.

    Conservative circumscribed circles cover both cuboids and cylinders. A
    staggered lattice avoids sequential-random-packing saturation. Large objects
    use peripheral candidates first; small positions are seeded samples of the
    remaining lattice. Impossible inputs fail explicitly, never truncate counts.
    """
    small_count = _integer(small_count, 'small_count')
    large_count = _integer(large_count, 'large_count')
    seed = _integer(seed, 'seed')
    if len(tile_size) != 2:
        raise ValueError('tile_size must have two dimensions')
    sx, sy = map(float, tile_size)
    values = (sx,sy,small_diameter,large_diameter,gap,safety,margin)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('layout dimensions must be finite')
    if min(sx,sy,small_diameter,large_diameter) <= 0 or min(gap,safety,margin) < 0:
        raise ValueError('invalid layout dimensions')
    rng = random.Random(seed)
    placed: list[tuple[tuple[float,float],float]] = []
    result = {'small': (), 'large': ()}

    def valid(xy, radius):
        x,y = xy
        if abs(x)+radius > sx/2-margin+1e-10 or abs(y)+radius > sy/2-margin+1e-10:
            return False
        if math.hypot(max(abs(x)-safety,0),max(abs(y)-safety,0)) < radius-1e-10:
            return False
        return all(math.dist(xy,other)+1e-10 >= radius+r+gap for other,r in placed)

    for kind,count,diameter in (('large',large_count,large_diameter),('small',small_count,small_diameter)):
        if not count:
            continue
        radius = diameter / math.sqrt(2)
        xlim,ylim = sx/2-margin-radius,sy/2-margin-radius
        if min(xlim,ylim) < 0:
            raise ValueError(f'no space for {kind} objects in tile {tile_size}')
        pitch = diameter*math.sqrt(2)+gap
        ypitch = pitch*math.sqrt(3)/2
        rows = math.floor(2*ylim/ypitch)+1
        # Center the lattice, avoiding an asymmetric usable-border remainder.
        candidates = []
        for row in range(rows):
            y = (row-(rows-1)/2)*ypitch
            columns = math.floor(2*xlim/pitch)+1
            for col in range(columns):
                x = (col-(columns-1)/2)*pitch + (row%2-.5)*pitch/2
                if abs(x) <= xlim+1e-10:
                    candidates.append((x,y))
        rng.shuffle(candidates)
        if kind == 'large':
            corners = [(x,y) for x in (-xlim,xlim) for y in (-ylim,ylim)]
            rng.shuffle(corners)
            candidates = corners + sorted(candidates, key=lambda p: -max(abs(p[0]),abs(p[1])))
        chosen = []
        for xy in candidates:
            if valid(xy,radius):
                chosen.append(xy)
                placed.append((xy,radius))
                if len(chosen) == count:
                    break
        if len(chosen) != count:
            raise ValueError(f'{kind} layout capacity {len(chosen)} < requested {count}; '
                             f'tile={tile_size}, gap={gap}, safety={safety}, margin={margin}')
        result[kind] = tuple(chosen)
    return result
