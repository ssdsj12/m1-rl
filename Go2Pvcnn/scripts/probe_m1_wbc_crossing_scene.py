#!/usr/bin/env python3
"""Read live M1 geometry; optional two-step production-PD measurement check."""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(PACKAGE / 'rsl_rl'))

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--env-spacing', type=float, default=8.0)
parser.add_argument('--verify-wheel-bottom', action='store_true',
                    help='Run exactly two neutral-PD wrapper steps; NOT a crossing test')
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if not args.device.startswith('cuda:') or not args.env_spacing >= 4.0:
    parser.error('use one CUDA device and env spacing >= 4 m')

# Deterministic actual semantic geometry, without the side large obstacles.
os.environ['M1_OBSTACLE_STAGE'] = 'small_only'
launcher = AppLauncher(args)
env = None
failure = None
try:
    import numpy as np
    import torch
    import omni.usd
    from pxr import Usd, UsdGeom
    from isaaclab.envs import ManagerBasedRLEnv

    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices
    from extension.parallelism.m1_kinematics import (
        M1_WHEEL_RADIUS_M, M1_WHEEL_THICKNESS_M)
    from extension.semantic_course import SEMANTIC_COURSE_SMALL_ROOT
    from ame_baseline.m1_wbc_swing import single_wheel_swing_reference

    cfg = M1AmeCrossLargeComplexEnvCfg()
    cfg.scene.num_envs = 1
    cfg.scene.env_spacing = args.env_spacing
    cfg.scene.terrain.terrain_generator.sub_terrains = {
        'flat': __import__('isaaclab.terrains', fromlist=['MeshPlaneTerrainCfg']).MeshPlaneTerrainCfg(
            proportion=1.0)
    }
    cfg.scene.terrain.terrain_generator.num_rows = 1
    cfg.scene.terrain.terrain_generator.num_cols = 1
    cfg.scene.terrain.max_init_terrain_level = 0
    cfg.sim.device = args.device
    cfg.sim.dt = 0.001
    cfg.decimation = 1
    cfg.seed = 7
    cfg.events.push_robot = None
    cfg.events.reset_base.params['pose_range'] = {
        'x': (0.0, 0.0), 'y': (0.0, 0.0), 'yaw': (0.0, 0.0)}
    cfg.events.reset_robot_joints.params['velocity_range'] = (0.0, 0.0)

    env = ManagerBasedRLEnv(cfg=cfg)
    env.reset()
    robot = env.scene['robot']
    wheel_names = tuple(M1_SUPPORT_BODY_NAMES)
    wheel_ids = tuple(resolve_named_indices(tuple(robot.body_names), wheel_names))
    if len(wheel_ids) != 4 or robot.is_fixed_base:
        raise RuntimeError('expected a floating M1 with four named wheel bodies')
    wheel_positions = robot.data.body_com_pos_w[0, list(wheel_ids)].detach().cpu().numpy()
    jacobians = env.scene['robot'].root_physx_view.get_jacobians()
    jacobians = torch.as_tensor(jacobians).detach().cpu().numpy()
    jac_shape = tuple(jacobians.shape)
    if not np.isfinite(wheel_positions).all() or not np.isfinite(jacobians).all():
        raise RuntimeError('nonfinite measured wheel or Jacobian data')

    stage = omni.usd.get_context().get_stage()
    bbox = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    obstacles = []
    root_prefix = SEMANTIC_COURSE_SMALL_ROOT.rstrip('/') + '/'
    for prim in stage.Traverse():
        path = prim.GetPath().pathString
        if not path.startswith(root_prefix) or not prim.IsA(UsdGeom.Gprim):
            continue
        aligned = bbox.ComputeWorldBound(prim).ComputeAlignedRange()
        low = np.asarray(aligned.GetMin(), dtype=np.float64)
        high = np.asarray(aligned.GetMax(), dtype=np.float64)
        if not np.isfinite(low).all() or not np.isfinite(high).all() or np.any(high <= low):
            raise RuntimeError('invalid world-space semantic obstacle bounds: ' + path)
        obstacles.append(dict(path=path, min_xyz=low.tolist(), max_xyz=high.tolist(),
                              center_xyz=((low+high)*0.5).tolist(), size_xyz=(high-low).tolist()))
    obstacles.sort(key=lambda item: (item['center_xyz'][0], item['center_xyz'][1]))
    if len(obstacles) != 6:
        raise RuntimeError(f'expected exactly six small-stage obstacle shapes, found {len(obstacles)}')
    positive_track = wheel_positions[wheel_positions[:, 1] > 0.0, 1]
    negative_track = wheel_positions[wheel_positions[:, 1] < 0.0, 1]
    if (len(positive_track) != 2 or len(negative_track) != 2
            or np.ptp(positive_track) > 0.002 or np.ptp(negative_track) > 0.002):
        raise RuntimeError('front/rear wheel centers do not form two lateral tracks: '
            + json.dumps(wheel_positions[:, 1].tolist()))
    track_centers = [float(np.mean(negative_track)), float(np.mean(positive_track))]
    lateral_overlap_by_obstacle = []
    for obstacle in obstacles:
        obstacle_y = obstacle['center_xyz'][1]
        obstacle_half_width = obstacle['size_xyz'][1]*0.5
        nearest = sorted(track_centers, key=lambda y: abs(obstacle_y-y))
        overlap = (M1_WHEEL_THICKNESS_M*0.5 + obstacle_half_width
                   - abs(obstacle_y-nearest[0]))
        opposite_clearance = (abs(obstacle_y-nearest[1])
                              - M1_WHEEL_THICKNESS_M*0.5-obstacle_half_width)
        if overlap <= 0.0 or opposite_clearance <= 0.0:
            raise RuntimeError('obstacle must overlap exactly one measured wheel track: '
                + json.dumps(dict(path=obstacle['path'], overlap_m=overlap,
                                  opposite_track_clearance_m=opposite_clearance)))
        lateral_overlap_by_obstacle.append(dict(path=obstacle['path'],
            target_track_y_m=nearest[0], wheel_envelope_overlap_m=overlap,
            opposite_track_clearance_m=opposite_clearance))

    swing_clearance_by_obstacle = []
    approach_distance = 0.25
    exit_distance = 0.20
    requested_clearance = 0.05
    assumed_forward_speed = 0.30
    for obstacle, lane in zip(obstacles, lateral_overlap_by_obstacle):
        front_x = float(obstacle['min_xyz'][0])
        far_x = float(obstacle['max_xyz'][0])
        obstacle_top_z = float(obstacle['max_xyz'][2])
        track_y = float(lane['target_track_y_m'])
        target_ids = np.flatnonzero(np.abs(wheel_positions[:, 1] - track_y) < 0.002)
        if len(target_ids) != 2:
            raise RuntimeError('target track does not identify exactly two measured wheels: '
                + json.dumps(dict(path=obstacle['path'], wheel_ids=target_ids.tolist())))
        target_id = int(target_ids[np.argmax(wheel_positions[target_ids, 0])])
        # Geometry-only planning starts each isolated obstacle trial just
        # before its approach ramp; it does not pretend the earlier course
        # obstacles have already been crossed by a physical controller.
        start = wheel_positions[target_id].copy()
        start[0] = front_x - M1_WHEEL_RADIUS_M - approach_distance - 0.02
        landing = start.copy()
        landing[0] = far_x + M1_WHEEL_RADIUS_M + exit_distance + 0.02
        duration = max(3.0, float(landing[0] - start[0]) / assumed_forward_speed)
        samples = [single_wheel_swing_reference(
            start=start, landing=landing, progress=float(progress), duration=duration,
            obstacle_front_x=front_x, obstacle_far_x=far_x,
            obstacle_top_z=obstacle_top_z, wheel_radius=M1_WHEEL_RADIUS_M,
            clearance=requested_clearance, approach_distance=approach_distance,
            exit_distance=exit_distance)
            for progress in np.linspace(0.0, 1.0, 501)]
        overlapping = [sample for sample in samples
            if sample['position'][0] + M1_WHEEL_RADIUS_M >= front_x
            and sample['position'][0] - M1_WHEEL_RADIUS_M <= far_x]
        if not overlapping:
            raise RuntimeError('swing reference does not traverse obstacle envelope: '
                + obstacle['path'])
        predicted_clearance = min(
            float(sample['position'][2] - M1_WHEEL_RADIUS_M - obstacle_top_z)
            for sample in overlapping)
        landing_margin = float(landing[0] - far_x - M1_WHEEL_RADIUS_M)
        max_vertical_acceleration = max(
            abs(float(sample['acceleration'][2])) for sample in samples)
        if predicted_clearance < requested_clearance - 1e-6:
            raise RuntimeError('swing reference violates wheel-envelope obstacle clearance: '
                + json.dumps(dict(path=obstacle['path'],
                    predicted_clearance_m=predicted_clearance)))
        if landing_margin < 0.04 or max_vertical_acceleration > 3.0 + 1e-6:
            raise RuntimeError('swing reference violates far-side landing or lift-acceleration gate: '
                + json.dumps(dict(path=obstacle['path'], landing_margin_m=landing_margin,
                    max_vertical_acceleration_mps2=max_vertical_acceleration)))
        swing_clearance_by_obstacle.append(dict(
            path=obstacle['path'], target_wheel=wheel_names[target_id],
            obstacle_front_x_m=front_x, obstacle_far_x_m=far_x,
            start_xyz_m=start.tolist(), landing_xyz_m=landing.tolist(),
            duration_s=duration, requested_clearance_m=requested_clearance,
            predicted_wheel_clearance_m=predicted_clearance,
            wheel_envelope_overlap_m=float(lane['wheel_envelope_overlap_m']),
            landing_margin_m=landing_margin,
            max_vertical_acceleration_mps2=max_vertical_acceleration))

    report = dict(scope='crossing_scene_and_swing_geometry_only_not_actuated', env_id=0,
        env_count=env.num_envs, device=args.device,
        obstacle_count=len(obstacles), obstacles=obstacles,
        lateral_overlap_by_obstacle=lateral_overlap_by_obstacle,
        swing_clearance_by_obstacle=swing_clearance_by_obstacle,
        swing_approach_distance_m=approach_distance,
        swing_exit_distance_m=exit_distance,
        swing_assumed_forward_speed_mps=assumed_forward_speed,
        wheel_names=list(wheel_names), wheel_radius_m=float(M1_WHEEL_RADIUS_M),
        wheel_thickness_m=float(M1_WHEEL_THICKNESS_M),
        wheel_com_world_xyz=wheel_positions.tolist(),
        root_world_xyz=robot.data.root_pos_w[0].detach().cpu().tolist(),
        native_jacobian_shape=jac_shape)
    print('M1_WBC_CROSSING_SCENE ' + json.dumps(report), flush=True)
    if args.verify_wheel_bottom:
        from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
        wrapper = AmeRslRlEnvWrapper(env)
        bottom_frames = []
        original_update = wrapper._m1_strict_crossing.update

        def capture_update(**kwargs):
            measured = kwargs['wheel_bottom_z_w']
            if measured.shape != (1, 4) or not torch.isfinite(measured).all():
                raise RuntimeError('invalid runtime measured wheel bottom')
            bottom_frames.append(measured.detach().cpu().tolist())
            return original_update(**kwargs)

        wrapper._m1_strict_crossing.update = capture_update
        print('M1_MEASURED_BOTTOM_STAGE wrapper_ready', flush=True)
        for tick in range(2):
            wrapper.step(torch.zeros((1,16),device=args.device))
            print('M1_MEASURED_BOTTOM_STAGE step=' + str(tick), flush=True)
        if len(bottom_frames) != 2:
            raise RuntimeError('strict tracker did not receive two measured-bottom frames')
        if wrapper._m1_strict_crossing.crossing_count.any():
            raise RuntimeError('neutral support probe falsely counted a crossing')
        print('M1_MEASURED_BOTTOM_RUNTIME ' + json.dumps(dict(
            scope='two_neutral_pd_steps_not_lift_or_crossing',
            frames=bottom_frames,
            cached_mesh_shape=list(wrapper._m1_wheel_vertices_b.shape),
            strict_crossings=wrapper._m1_strict_crossing.crossing_count.tolist(),
        )), flush=True)
except BaseException as exc:
    failure = exc
    print('M1_WBC_CROSSING_SCENE_ERROR ' + repr(exc), file=sys.stderr, flush=True)
    traceback.print_exc()
finally:
    if env is not None:
        try:
            env.close()
        except BaseException as exc:
            print('M1_WBC_CROSSING_SCENE_ENV_CLOSE_ERROR ' + repr(exc),
                  file=sys.stderr, flush=True)
            if failure is None:
                failure = exc
    try:
        launcher.app.close()
    except BaseException as exc:
        print('M1_WBC_CROSSING_SCENE_APP_CLOSE_ERROR ' + repr(exc),
              file=sys.stderr, flush=True)
        if failure is None:
            failure = exc
if failure is not None:
    raise SystemExit(1)
