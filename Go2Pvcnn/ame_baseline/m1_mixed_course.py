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
    cfg.scene.terrain.terrain_generator.size = (16., 16.)
    # Fresh PPO must learn supported locomotion before high terrain rows.
    # Existing success-gated terrain curriculum still advances difficulty.
    cfg.scene.terrain.max_init_terrain_level = 0
    cfg.semantic_obstacle_curriculum = SemanticObstacleCurriculumCfg(
        plane_terrain_names=('flat',),
        plane_counts=tuple(SemanticObstacleCount(*flat_counts(i)) for i in range(10)),
        non_plane_counts=tuple(SemanticObstacleCount(max(8,a),b) for a,b in zip(REFERENCE_NONPLANE_SMALL,REFERENCE_NONPLANE_LARGE)),
        terrain_obstacle_count_overrides={},center_safety_half_extent_m=(.85,),
        min_spacing_clearance_m=(.45,),tile_margin_m=(.5,),
    )
    cfg.scene.terrain.semantic_obstacle_curriculum = cfg.semantic_obstacle_curriculum
    cfg.scene.terrain.semantic_course_layout_cfg = SemanticCourseLayoutCfg(
        placement_strategy='m1_dense_forward',small_shape_pool=('cuboid','cylinder'),
        center_safety_half_extent_m=.85,min_spacing_clearance_m=.45,tile_margin_m=.5,
    )
    cfg.scene.terrain.semantic_course_scale_profile_overrides={'small':(.05,.10),'large':(.45,.55)}
    cfg.scene.terrain.semantic_course_grounding_cfg=SemanticCourseGroundingCfg(embed_depth_m=0.)
    cfg.curriculum.terrain_levels=copy.deepcopy(TeacherElevationTrajectoryMpcSemanticCurriculumCfg().terrain_levels)
    cfg.commands.base_velocity.ranges.lin_vel_x=(.18,.45)
    cfg.commands.base_velocity.ranges.lin_vel_y=(0.,0.)
    cfg.commands.base_velocity.ranges.ang_vel_z=(0.,0.)
    cfg.commands.base_velocity.limit_ranges.lin_vel_x=(.18,.45)
    cfg.commands.base_velocity.limit_ranges.lin_vel_y=(0.,0.)
    cfg.commands.base_velocity.limit_ranges.ang_vel_z=(0.,0.)
    cfg.events.reset_base.params['pose_range']={'x':(0.,0.),'y':(0.,0.),'yaw':(0.,0.)}


def progressive_row(row):
    """Flat-column counts/height; row0 is genuinely free of obstacle colliders."""
    row = _integer(row, 'row')
    if row < 4:
        return ((0,0.,0),(2,.03,0),(4,.06,0),(8,.10,0))[row]
    small, large = flat_counts(row)
    return small, .10, large


def configure_flat_first_terrain(cfg):
    """Prebuild learning stages; a measured reset gate selects active tiles."""
    from dataclasses import replace
    from extension.semantic_curriculum import SemanticObstacleCount
    from isaaclab.managers import CurriculumTermCfg, TerminationTermCfg
    from .m1_learning_curriculum import curriculum_reset, track_velocity_and_accumulate
    configure_mixed_terrain(cfg)
    cfg.m1_flat_first = True
    counts = cfg.semantic_obstacle_curriculum
    counts.plane_counts = tuple(SemanticObstacleCount(progressive_row(i)[0],progressive_row(i)[2]) for i in range(10))
    counts.non_plane_counts = tuple(SemanticObstacleCount(progressive_row(i)[0],0) if i<4 else counts.non_plane_counts[i] for i in range(10))
    cfg.scene.terrain.semantic_course_layout_cfg = replace(
        cfg.scene.terrain.semantic_course_layout_cfg, placement_strategy='m1_progressive')
    cfg.curriculum.terrain_levels = CurriculumTermCfg(func=curriculum_reset)
    cfg.curriculum.lin_vel_cmd_levels = None
    cfg.rewards.track_lin_vel_xy.func = track_velocity_and_accumulate
    cfg.commands.base_velocity.rel_standing_envs = 0.
    cfg.terminations.course_boundary = TerminationTermCfg(func=flat_first_course_boundary, time_out=True)


def progressive_positions(small_count, large_count, *, row, **kwargs):
    if row >= 4:
        return dense_forward_positions(small_count, large_count, **kwargs)
    expected = progressive_row(row)
    if (small_count,large_count) != (expected[0],0):
        raise ValueError('progressive stage count mismatch')
    pitch = 1.8 if row < 3 else .9
    return {'small':tuple((.9+pitch*i,.215 if i%2==0 else -.215) for i in range(small_count)), 'large':()}


def record_curriculum_strict_events(env, events, done):
    """Lifetime per-env counters; terminal reset poses cannot create events."""
    if not getattr(env.cfg, 'm1_flat_first', False):
        return
    import torch
    if not hasattr(env, '_m1_curriculum_attempts'):
        env._m1_curriculum_attempts = torch.zeros(env.num_envs,dtype=torch.long,device=env.device)
        env._m1_curriculum_successes = torch.zeros_like(env._m1_curriculum_attempts)
    env._m1_curriculum_attempts += (events['attempt_started'] & ~done).long()
    # Curriculum promotion requires the extra stable recovery frames, not
    # merely the first safe touchdown. Existing crossing metrics stay separate.
    env._m1_curriculum_successes += (events['recovery_complete'] & ~done).long()


def outside_course_tile(root_xy, wheel_xy, centers_xy, tile_size, radius):
    """End a rollout before the body or tire envelope leaves its indexed tile."""
    half = root_xy.new_tensor(tile_size) / 2.
    body_out = ((root_xy-centers_xy).abs() > half-.75).any(-1)
    wheel_out = ((wheel_xy-centers_xy[:,None]).abs()+radius > half-.05).any(-1).any(-1)
    return body_out | wheel_out


def flat_first_course_boundary(env):
    from .m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    from extension.parallelism.m1_kinematics import M1_WHEEL_HORIZONTAL_ENVELOPE_M
    from extension.parallelism.rl_adapter import resolve_named_indices
    robot=env.scene['robot']
    terrain=env.scene.terrain
    ids=list(resolve_named_indices(robot.body_names,M1_SUPPORT_BODY_NAMES))
    centers=terrain.terrain_origins[terrain.terrain_levels,terrain.terrain_types,:2]
    return outside_course_tile(robot.data.root_pos_w[:,:2],robot.data.body_pos_w[:,ids,:2],
        centers,terrain.cfg.terrain_generator.size,float(M1_WHEEL_HORIZONTAL_ENVELOPE_M))


def dense_forward_positions(small_count, large_count, *, seed, tile_size=(16.,8.),
                            small_diameter=.05, large_diameter=.45,
                            gap=.45, safety=.85, margin=.5):
    """Eight alternating wheel-track blocks in every tile, then peripheral clutter.

    .9m pitch gives .356m between nominal front/rear encounters for the .544m
    M1 axle spacing. This geometric check is not a learned single-leg guarantee.
    """
    if small_count < 8 or tile_size[0]/2-margin < 7.2+small_diameter/math.sqrt(2):
        raise ValueError('dense forward layout needs eight obstacles and16m tile length')
    return structured_positions(small_count,large_count,seed=seed,tile_size=tile_size,
        small_diameter=small_diameter,large_diameter=large_diameter,gap=gap,
        safety=safety,margin=margin,reserve_front=True)


def structured_positions(
    small_count: int, large_count: int, *, seed: int,
    tile_size=(8.,8.), small_diameter=.05, large_diameter=.45,
    gap=.45, safety=.85, margin=.5, reserve_front=False,
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
    front = tuple((.9+.9*i,.215 if i%2==0 else -.215) for i in range(8)) if reserve_front else ()
    placed.extend((xy,small_diameter/math.sqrt(2)) for xy in front)

    def valid(xy, radius):
        x,y = xy
        if reserve_front and x > .5 and abs(y) < .8:
            return False
        if abs(x)+radius > sx/2-margin+1e-10 or abs(y)+radius > sy/2-margin+1e-10:
            return False
        if math.hypot(max(abs(x)-safety,0),max(abs(y)-safety,0)) < radius-1e-10:
            return False
        return all(math.dist(xy,other)+1e-10 >= radius+r+gap for other,r in placed)

    for kind,count,diameter in (('large',large_count,large_diameter),('small',small_count,small_diameter)):
        if kind == 'small':
            count -= len(front)
        if not count:
            if kind == 'small':
                result[kind] = front
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
        result[kind] = (front if kind == 'small' else ()) + tuple(chosen)
    return result
