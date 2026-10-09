#!/usr/bin/env python3
"""Bounded PREPARE with opt-in vertical lift; never trains or claims crossing."""
import argparse
import json
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(PACKAGE / 'rsl_rl'))
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument('--num_steps', type=int, default=32)
parser.add_argument('--batched_prepare', action='store_true',
    help='Exercise shared per-environment PREPARE with unchanged production PD; no lift')
parser.add_argument('--pd_unload_steps',type=int,default=0,
    help='After verified batched PREPARE, bounded measured PD-only unload; no WBC/lift')
parser.add_argument('--pd_unload_world_height',action='store_true',
    help='Compensate measured root Z/tilt in selected-leg world height only')
parser.add_argument('--transfer_speed', type=float, default=.02)
parser.add_argument('--max_root_shift', type=float, default=.06)
parser.add_argument('--lift_steps', type=int, default=0)
parser.add_argument('--roll_steps', type=int, default=0)
parser.add_argument('--roll_speed', type=float, choices=(0., .02, .1), default=.1)
parser.add_argument('--roll_ramp', action='store_true')
parser.add_argument('--roll_continuous_ramp', action='store_true')
parser.add_argument('--roll_substep_audit', action='store_true')
parser.add_argument('--roll_lifted_only', action='store_true')
parser.add_argument('--roll_explicit_torque', type=float, choices=(0.,3.), default=0.)
parser.add_argument('--selected_leg', type=int, choices=(0,1,2,3), default=None)
parser.add_argument('--physics_refinement', type=int, choices=(1,2), default=1)
parser.add_argument('--roll_wheel_damping', type=float, choices=(5.,20.), default=5.)
parser.add_argument('--roll_load_feedback', action='store_true')
parser.add_argument('--roll_com_trajectory', action='store_true')
parser.add_argument('--vertical_speed', type=float, choices=(.08, .12), default=.08)
parser.add_argument('--lift_height', type=float, choices=(.16, .18), default=.18)
parser.add_argument('--land_steps', type=int, default=0)
parser.add_argument('--settle_steps', type=int, default=0)
parser.add_argument('--land_search_depth', type=float, choices=(0., .005), default=0.)
parser.add_argument('--lift_pose_feedback', action='store_true')
parser.add_argument('--lift_support_transfer', action='store_true')
parser.add_argument('--lift_force_feedback', action='store_true')
parser.add_argument('--dynamics_audit', action='store_true')
parser.add_argument('--wbc_snapshot', action='store_true')
parser.add_argument('--prepare_load_floor', action='store_true')
parser.add_argument('--prepare_wheel_hold_only', action='store_true',
    help='Bounded anchor feedback during PREPARE; stop before any UNLOAD/handoff')
parser.add_argument('--phase_wheel_hold',action='store_true')
parser.add_argument('--prepare_support_floor', type=float, choices=(35.,40.), default=35.)
parser.add_argument('--rear_lift_reserve', action='store_true')
parser.add_argument('--standing_effort_steps', type=int, default=0)
parser.add_argument('--standing_roll', action='store_true')
parser.add_argument('--standing_contact_substeps',action='store_true')
parser.add_argument('--standing_wheel_damping', type=float, choices=(5.,20.), default=5.)
parser.add_argument('--standing_velocity_iterations', type=int, choices=(0,4), default=0)
parser.add_argument('--diagnostic_wheel_prism', action='store_true')
parser.add_argument('--diagnostic_source_sdf', action='store_true')
parser.add_argument('--diagnostic_sdf_resolution',type=int,choices=(128,256),default=128)
parser.add_argument('--diagnostic_sdf_rest_offset',type=float,choices=(0.,.001),default=0.)
parser.add_argument('--diagnostic_sdf_clean_pairs',action='store_true')
parser.add_argument('--diagnostic_fixed_physics', action='store_true')
parser.add_argument('--diagnostic_wheel_profile', choices=('cylinder','shoulder','shoulder_split'), default='cylinder')
parser.add_argument('--standing_effort_gain', type=int, choices=(0, 1), default=1)
parser.add_argument('--phase_effort', action='store_true')
parser.add_argument('--unload_steps', type=int, default=0)
parser.add_argument('--unload_feedback', action='store_true')
parser.add_argument('--unload_com', action='store_true')
parser.add_argument('--unload_target_force', type=float, choices=(0., 5.), default=5.)
parser.add_argument('--unload_min_speed', type=float, choices=(0., .003), default=0.)
parser.add_argument('--unload_world_pose', action='store_true')
parser.add_argument('--unload_vertical_only', action='store_true')
parser.add_argument('--unload_height_only',action='store_true')
parser.add_argument('--unload_height_settled',action='store_true')
parser.add_argument('--unload_substep_audit',action='store_true')
parser.add_argument('--unload_friction_audit',action='store_true')
parser.add_argument('--unload_com_ramp',action='store_true')
parser.add_argument('--anticipatory_prepare',action='store_true')
parser.add_argument('--lift_attitude_feedback',action='store_true')
parser.add_argument('--lift_handoff',action='store_true')
parser.add_argument('--unload_support_feedback',action='store_true')
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.pd_unload_steps and (not args.batched_prepare or not 1<=args.pd_unload_steps<=100):
    raise ValueError('PD UNLOAD requires batched PREPARE and1..100steps/2seconds')
if args.pd_unload_world_height and not args.pd_unload_steps:
    raise ValueError('selected world-height correction requires PD UNLOAD')
if args.batched_prepare and (args.phase_effort or args.lift_steps or args.unload_steps
        or args.standing_effort_steps or args.anticipatory_prepare
        or args.diagnostic_fixed_physics or args.diagnostic_source_sdf or args.diagnostic_wheel_prism
        or args.physics_refinement!=1
        or not args.prepare_load_floor or args.max_root_shift!=.08
        or args.transfer_speed!=.04 or args.prepare_support_floor!=35.):
    raise ValueError('batched PREPARE requires production PD/geometry, load floor35N, .08m bound, .04m/s and no later phase')
if args.lift_handoff and (not args.anticipatory_prepare or not args.roll_steps or not args.land_steps):
    raise ValueError('lift handoff requires complete anticipatory diagnostic cycle')
if args.diagnostic_sdf_clean_pairs and not args.diagnostic_source_sdf:
    raise ValueError('pair cleanup requires explicit source SDF diagnostic')
if args.roll_continuous_ramp and (not args.roll_ramp or not args.phase_wheel_hold
        or args.roll_speed!=.1):
    raise ValueError('continuous ramp requires held wheels, roll ramp and .1m/s cap')
if args.unload_support_feedback and not args.anticipatory_prepare:
    raise ValueError('unload support correction requires anticipatory prepared reference')
if args.lift_attitude_feedback and (not args.anticipatory_prepare or not args.unload_height_only
        or args.lift_pose_feedback or args.lift_support_transfer):
    raise ValueError('attitude correction requires isolated anticipatory world-height cycle')
if args.anticipatory_prepare and (not args.phase_wheel_hold or not args.unload_com_ramp
        or args.max_root_shift!=.08 or args.transfer_speed!=.04):
    raise ValueError('anticipatory reference requires bounded full held-wheel cycle, .08m shift and .04m/s speed')
if args.unload_height_settled and not args.unload_height_only:
    raise ValueError('settled height activation requires height-only correction')
if args.unload_height_only and (not args.unload_world_pose or args.unload_vertical_only):
    raise ValueError('height-only requires world pose and excludes vertical-only')
if args.phase_wheel_hold and (args.prepare_wheel_hold_only or not args.phase_effort
        or not args.unload_world_pose or not args.land_steps or args.roll_explicit_torque
        or args.roll_lifted_only or args.roll_wheel_damping!=5.):
    raise ValueError('phase holding requires separate complete world-frame cycle and baseline wheel drive')
if args.prepare_wheel_hold_only and (not args.phase_effort or args.standing_effort_steps):
    raise ValueError('prepare wheel holding requires phase effort and no standing diagnostic')
if args.standing_contact_substeps and not args.standing_roll:
    raise ValueError('standing contact observer requires standing rolling diagnostic')
if args.diagnostic_source_sdf:
    from ame_baseline.m1_sdf_probe import allowed_sdf_cycle
    if not allowed_sdf_cycle(args.standing_roll,args.lift_steps,args.land_steps,
                             args.diagnostic_fixed_physics,args.diagnostic_wheel_prism):
        raise ValueError('source SDF requires fixed-physics standing or complete lift/land cycle')
if args.roll_explicit_torque and (not args.roll_steps or args.roll_lifted_only or args.roll_wheel_damping!=5.):
    raise ValueError('explicit wheel effort requires separate bounded support-wheel test')
if args.roll_lifted_only and not args.roll_steps:
    raise ValueError('lifted-wheel drive comparison requires the bounded rolling window')
if args.roll_wheel_damping != 5. and not (args.roll_steps and args.diagnostic_fixed_physics):
    raise ValueError('rolling drive comparison requires bounded fixed-physics cycle')
if args.rear_lift_reserve and not (args.prepare_load_floor and args.unload_com):
    raise ValueError('rear-lift reserve requires PREPARE and coordinated UNLOAD')
if args.roll_load_feedback and not args.roll_steps:
    raise ValueError('moving load feedback requires the bounded rolling cycle')
if args.roll_com_trajectory and not args.roll_load_feedback:
    raise ValueError('COM trajectory requires moving load feedback')
if args.diagnostic_wheel_prism:
    from ame_baseline.m1_wheel_collision_probe import allowed_cycle
    if not allowed_cycle(args.diagnostic_wheel_profile,args.standing_roll,args.lift_steps,args.land_steps):
        raise ValueError('diagnostic geometry requires standing roll or complete lift/land cycle')
if not 1 <= args.num_steps <= 200:
    raise ValueError('PREPARE diagnostic budget must be 1..200 steps (4 seconds)')
if not 0 <= args.lift_steps <= 200:
    raise ValueError('LIFT diagnostic budget must be 0..200 steps')
if not 0 <= args.roll_steps <= 20 or (args.roll_steps and (not args.lift_steps or not args.land_steps or not args.unload_world_pose or args.lift_support_transfer or args.lift_pose_feedback)):
    raise ValueError('rolling probe requires continuous world frame and at most20steps')
if not 0 <= args.land_steps <= 200 or args.lift_steps+args.roll_steps+args.land_steps > 200:
    raise ValueError('LIFT and LAND share at most200steps/4seconds')
if args.land_steps and (not args.lift_steps or not args.unload_world_pose or not args.phase_effort):
    raise ValueError('LAND requires preceding LIFT and continuous world-frame effort control')
if not 0<=args.settle_steps<=100 or (args.settle_steps and not args.land_steps):
    raise ValueError('SETTLE requires LAND and at most100steps/2seconds')
if not 0 <= args.standing_effort_steps <= 180 or (args.standing_effort_steps and args.lift_steps):
    raise ValueError('standing effort diagnostic is 0..180 steps and cannot lift')
if args.standing_roll:
    from ame_baseline.m1_rolling_speed import standing_window
    standing_start,standing_duration=standing_window(args.standing_effort_steps)
elif args.standing_effort_steps>100:
    raise ValueError('extended standing budget requires rolling control')
if args.standing_wheel_damping!=5. and not args.standing_roll:
    raise ValueError('wheel damping comparison is isolated to standing rolling control')
if args.lift_pose_feedback and args.lift_support_transfer:
    raise ValueError('test support transfer separately from pose feedback')
if args.lift_force_feedback and not args.lift_support_transfer:
    raise ValueError('force feedback requires lift support transfer')
if args.phase_effort and (args.standing_effort_steps or not args.prepare_load_floor):
    raise ValueError('phase effort requires load-feasible PREPARE and separate standing test')
if not 0 <= args.unload_steps <= 100 or (args.unload_steps and not args.phase_effort):
    raise ValueError('unload diagnostic needs phase effort and 0..100 steps')
if args.unload_feedback and not args.unload_steps:
    raise ValueError('unload feedback requires bounded unload stage')
if args.unload_com and not args.unload_feedback:
    raise ValueError('coordinated COM requires unload feedback')
if args.unload_com_ramp and not args.unload_com:
    raise ValueError('unload COM ramp requires coordinated unload')
if args.unload_world_pose and not args.unload_com:
    raise ValueError('selected world pose requires coordinated unload')
if args.unload_world_pose and (args.lift_pose_feedback or args.lift_support_transfer):
    raise ValueError('world-frame handoff must be tested separately from other lift pose controllers')
if args.unload_vertical_only and not args.unload_world_pose:
    raise ValueError('vertical-only mode requires selected world pose')
launcher = AppLauncher(args)
env = None
try:
    import torch
    from isaaclab.envs import ManagerBasedRLEnv
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_ame_contract import M1_LEG_ACTION_SCALE_RAD
    from ame_baseline.m1_support_observer import observe_support
    from ame_baseline.m1_prepare_gate import PrepareGate
    from ame_baseline.m1_load_transfer import transfer_target
    from ame_baseline.m1_single_lift import lift_target
    from extension.parallelism.m1_kinematics import (
        M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES, M1_WHEEL_RADIUS_M, m1_fk)
    from extension.parallelism.rl_adapter import resolve_named_indices
    from extension.convention import extract_roll_pitch_batch, extract_yaw_batch

    cfg = M1AmeCrossLargeComplexEnvCfg()
    if args.diagnostic_source_sdf:
        from ame_baseline.m1_sdf_probe import spawn_source_sdf
        from functools import partial
        cfg.scene.robot.spawn.func=partial(spawn_source_sdf,resolution=args.diagnostic_sdf_resolution,
                                          rest_offset=args.diagnostic_sdf_rest_offset,
                                          clean_pairs=args.diagnostic_sdf_clean_pairs)
    if args.diagnostic_fixed_physics:
        from ame_baseline.m1_wheel_collision_probe import fix_diagnostic_physics
        fix_diagnostic_physics(cfg)
    if args.diagnostic_wheel_prism:
        from ame_baseline.m1_wheel_collision_probe import spawn_diagnostic_wheels
        from functools import partial
        cfg.scene.robot.spawn.func=partial(spawn_diagnostic_wheels,profile=args.diagnostic_wheel_profile)
    from ame_baseline.m1_rolling_speed import solver_comparison
    cfg.scene.robot.spawn.articulation_props.solver_velocity_iteration_count=solver_comparison(args.standing_roll,args.standing_velocity_iterations)
    if args.standing_roll:
        cfg.scene.robot.actuators['wheels'].damping=args.standing_wheel_damping
    # A disabled terrain curriculum does not remove rough sub-terrains.
    # The approved first gate is a flat course, not a random complex tile.
    from isaaclab.terrains import MeshPlaneTerrainCfg
    cfg.scene.terrain.terrain_generator.sub_terrains = {'flat': MeshPlaneTerrainCfg(proportion=1.)}
    cfg.scene.terrain.terrain_generator.num_rows = 1
    cfg.scene.terrain.terrain_generator.num_cols = 8
    cfg.scene.terrain.max_init_terrain_level = 0
    cfg.scene.num_envs = 8
    cfg.scene.env_spacing = 8.
    cfg.sim.device = str(args.device)
    from ame_baseline.m1_rolling_speed import refine_timestep
    refine_timestep(cfg,args.physics_refinement)
    print('M1_TIMESTEP '+json.dumps(dict(dt=cfg.sim.dt,decimation=cfg.decimation,
        control_dt=cfg.sim.dt*cfg.decimation,render_interval=cfg.sim.render_interval)),flush=True)
    cfg.seed = 2
    cfg.events.push_robot = None
    cfg.events.reset_base.params['pose_range'] = {'x': (0., 0.), 'y': (0., 0.), 'yaw': (0., 0.)}
    cfg.events.reset_robot_joints.params['velocity_range'] = (0., 0.)
    cfg.commands.base_velocity.ranges.lin_vel_x = (0., 0.)
    cfg.commands.base_velocity.ranges.lin_vel_y = (0., 0.)
    cfg.commands.base_velocity.ranges.ang_vel_z = (0., 0.)
    env = ManagerBasedRLEnv(cfg=cfg)
    env.reset()
    from omni.physx import get_physx_cooking_interface
    cooking=get_physx_cooking_interface()
    wheel_mesh='/World/envs/env_0/Robot/FBL_FOOT_LINK/collisions/FBL_FOOT_LINK/mesh'
    hull_count=cooking.get_nb_convex_mesh_data(wheel_mesh)
    if args.diagnostic_source_sdf:
        from omni.physx import get_physxunittests_interface
        stats=get_physxunittests_interface().get_physics_stats()
        print('M1_SDF_PHYSICS_STATS '+json.dumps(stats),flush=True)
        if hull_count or stats.get('numTriMeshShapes',0)<32:
            raise RuntimeError('source SDF triangle shapes not verified; reject convex fallback')
    hulls=[]
    for hull_index in range(hull_count):
        hull=cooking.get_convex_mesh_data(wheel_mesh,hull_index)
        hulls.append(dict(num_vertices=hull['num_vertices'],num_polygons=hull['num_polygons'],
            vertices=[list(v) for v in hull['vertices']],indices=list(hull['indices']),
            polygons=[dict(num_vertices=p['num_vertices'],index_base=p['index_base'],plane=list(p['plane'])) for p in hull['polygons']]))
    print('M1_COOKED_WHEEL '+json.dumps(dict(path=wheel_mesh,hulls=hulls)),flush=True)
    if args.diagnostic_wheel_profile=='shoulder_split':
        extra_path=wheel_mesh+'_shoulder'
        extra_hulls=[cooking.get_convex_mesh_data(extra_path,i)
                     for i in range(cooking.get_nb_convex_mesh_data(extra_path))]
        print('M1_COOKED_SHOULDER '+json.dumps(dict(path=extra_path,
            hulls=[dict(num_vertices=h['num_vertices'],num_polygons=h['num_polygons'])
                   for h in extra_hulls])),flush=True)
        if len(extra_hulls)!=1:
            raise RuntimeError('split shoulder must produce one additional cooked hull')
    from pxr import PhysxSchema
    print('M1_SOLVER_VELOCITY_ITERATIONS '+str(PhysxSchema.PhysxArticulationAPI(env.sim.stage.GetPrimAtPath('/World/envs/env_0/Robot/BASE_LINK')).GetSolverVelocityIterationCountAttr().Get()),flush=True)
    robot, sensor = env.scene['robot'], env.scene['contact_forces']
    if args.diagnostic_source_sdf:
        collision_api=PhysxSchema.PhysxCollisionAPI(env.sim.stage.GetPrimAtPath(wheel_mesh))
        print('M1_SDF_OFFSETS '+json.dumps(dict(
            authored_rest=collision_api.GetRestOffsetAttr().Get(),
            authored_contact=collision_api.GetContactOffsetAttr().Get(),
            native_rest=robot.root_physx_view.get_rest_offsets().tolist(),
            native_contact=robot.root_physx_view.get_contact_offsets().tolist())),flush=True)
        if args.diagnostic_sdf_rest_offset:
            native_rest=robot.root_physx_view.get_rest_offsets()
            matches=torch.isclose(native_rest,torch.full_like(native_rest,args.diagnostic_sdf_rest_offset))
            if int(matches.sum())!=32:
                raise RuntimeError('SDF rest margin not applied to all32wheel shapes; reject invalid comparison')
    print('M1_PHYSICAL_INVARIANTS '+json.dumps(dict(
        masses=robot.root_physx_view.get_masses().tolist(),
        inertias=robot.root_physx_view.get_inertias().tolist(),
        materials=robot.root_physx_view.get_material_properties().tolist())),flush=True)
    contact_audit=None
    roll_contact_audits={}
    roll_transient_views={}
    if args.roll_substep_audit:
        for name in ('FBL_FOOT_LINK','FAR_FOOT_LINK','RBL_FOOT_LINK','RAR_FOOT_LINK'):
            roll_transient_views[name]=sensor._physics_sim_view.create_rigid_contact_view(
                '/World/envs/env_7/Robot/'+name,
                filter_patterns=['/World/ground/terrain/mesh'],max_contact_data_count=128)
    if args.roll_steps:
        for name in ('FBL_FOOT_LINK','FAR_FOOT_LINK','RBL_FOOT_LINK'):
            roll_contact_audits[name]=sensor._physics_sim_view.create_rigid_contact_view(
                '/World/envs/env_3/Robot/'+name,
                filter_patterns=['/World/ground/terrain/mesh'],max_contact_data_count=128)
    if args.standing_roll:
        contact_audit=sensor._physics_sim_view.create_rigid_contact_view(
            '/World/envs/env_0/Robot/FBL_FOOT_LINK',
            filter_patterns=['/World/ground/terrain/mesh'],max_contact_data_count=128)
        from pxr import UsdPhysics
        print('M1_STATIC_COLLIDERS '+json.dumps([str(p.GetPath()) for p in env.sim.stage.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI) and '/Robot/' not in str(p.GetPath())]),flush=True)
    asset_ids = list(resolve_named_indices(tuple(robot.joint_names), M1_ASSET_JOINT_NAMES))
    planner_ids = list(resolve_named_indices(tuple(robot.joint_names), M1_PLANNER_JOINT_NAMES))
    planner_cols = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    wheel_cols = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES))
    wheel_joint_ids = list(resolve_named_indices(tuple(robot.joint_names), M1_WHEEL_JOINT_NAMES))
    wheel_names = tuple(n.replace('_JOINT', '_LINK') for n in M1_WHEEL_JOINT_NAMES)
    wheel_ids = list(resolve_named_indices(tuple(robot.body_names), wheel_names))
    wheel_sensor_ids = list(resolve_named_indices(tuple(sensor.body_names), wheel_names))
    unload_friction_views={}
    if args.unload_friction_audit:
        if not args.unload_substep_audit:
            raise ValueError('friction audit requires unload substep observer')
        for row in (0,1):
            for name in wheel_names:
                unload_friction_views[(row,name)]=sensor._physics_sim_view.create_rigid_contact_view(
                    f'/World/envs/env_{row}/Robot/{name}',
                    filter_patterns=['/World/ground/terrain/mesh'],max_contact_data_count=128)
    nonsupport_ids = [i for i, name in enumerate(sensor.body_names) if name not in wheel_names]
    device = robot.data.root_pos_w.device
    wbc_contact_views = {name:sensor._physics_sim_view.create_rigid_contact_view(
        f'/World/envs/env_0/Robot/{name}',
        filter_patterns=['/World/ground/terrain/mesh'],max_contact_data_count=128)
        for name in wheel_names} if args.wbc_snapshot else {}
    wbc_material_views = {name:sensor._physics_sim_view.create_rigid_body_view(
        robot.root_physx_view.link_paths[0][wheel_ids[index]])
        for index,name in enumerate(wheel_names)} if args.wbc_snapshot else {}
    standing_contact_view=None
    if args.standing_contact_substeps:
        standing_contact_view=sensor._physics_sim_view.create_rigid_contact_view(
            '/World/envs/env_6/Robot/RAR_FOOT_LINK',
            filter_patterns=['/World/ground/terrain/mesh'],max_contact_data_count=128)

    def observed_standing_step(action,phase,control_step):
        from ame_baseline.m1_substeps import observe_substeps
        from ame_baseline.m1_contact_snapshot import pair_records
        def read_contact():
            nf,cp,cn,sep,nc,ns=standing_contact_view.get_contact_data(dt=cfg.sim.dt)
            native=sensor.contact_physx_view.get_net_contact_forces(dt=cfg.sim.dt).reshape(8,-1,3)
            return dict(native_force=native[6,wheel_sensor_ids].tolist(),
                cached_force=sensor.data.net_forces_w[6,wheel_sensor_ids].tolist(),
                pair_net=standing_contact_view.get_net_contact_forces(dt=cfg.sim.dt).tolist(),
                pairs=pair_records(nf.flatten().tolist(),cp.tolist(),sep.flatten().tolist(),
                                   nc.flatten().tolist(),ns.flatten().tolist()),
                wheel_center=robot.data.body_pos_w[6,wheel_ids].tolist(),
                wheel_quat_wxyz=robot.data.body_quat_w[6,wheel_ids].tolist(),
                wheel_velocity=robot.data.body_lin_vel_w[6,wheel_ids].tolist())
        result,records=observe_substeps(env.scene,lambda:env.step(action),read_contact)
        print('M1_STANDING_CONTACT_SUBSTEPS '+json.dumps(dict(phase=phase,step=control_step,
            physics_dt=cfg.sim.dt,env=6,pair_body='RAR_FOOT_LINK',records=records)),flush=True)
        return result
    print('M1_WHEEL_BACKEND '+json.dumps(dict(
        names=M1_WHEEL_JOINT_NAMES,
        friction=robot.data.joint_friction_coeff[:,wheel_joint_ids].tolist(),
        position_limits=robot.root_physx_view.get_dof_limits()[:,wheel_joint_ids].tolist(),
        position=robot.data.joint_pos[:,wheel_joint_ids].tolist(),
        physx_stiffness=robot.root_physx_view.get_dof_stiffnesses()[:,wheel_joint_ids].tolist(),
        physx_damping=robot.root_physx_view.get_dof_dampings()[:,wheel_joint_ids].tolist(),
        physx_max_velocity=robot.root_physx_view.get_dof_max_velocities()[:,wheel_joint_ids].tolist(),
        armature=robot.data.joint_armature[:,wheel_joint_ids].tolist(),
        effort_limit=robot.data.joint_effort_limits[:,wheel_joint_ids].tolist(),
        stiffness=robot.data.joint_stiffness[:,wheel_joint_ids].tolist(),
        damping=robot.data.joint_damping[:,wheel_joint_ids].tolist())),flush=True)
    from ame_baseline.m1_rolling_speed import selected_legs
    selected = torch.tensor(selected_legs(args.selected_leg),device=device,dtype=torch.long)
    prepare_reserve=torch.full((8,),args.prepare_support_floor,device=device)
    if args.rear_lift_reserve:
        prepare_reserve=torch.where(selected>=2,torch.full_like(prepare_reserve,40.),prepare_reserve)
    print('M1_PREPARE_RESERVE '+json.dumps(prepare_reserve.tolist()),flush=True)
    zero = torch.zeros(8, dtype=torch.long, device=device)
    action = torch.zeros(8, 16, device=device)
    samples = []
    lift_samples = []
    stopped = None
    phase_effort_samples = []
    if args.phase_effort:
        from ame_baseline.m1_dynamics import point_linear_jacobian
        from ame_baseline.m1_support_effort import vertical_support_solution
        from ame_baseline.m1_effort_guard import guarded_effort, position_pd_effort
        phase_effort = torch.zeros_like(robot.data.joint_pos)
        phase_leg_mask = torch.zeros(16, dtype=torch.bool, device=device)
        phase_leg_mask[planner_ids] = True

        def apply_phase_effort(next_joint, support_mask, phase, step):
            global phase_effort
            jac = point_linear_jacobian(robot.root_physx_view.get_jacobians(),
                robot.data.body_com_pos_w, robot.data.body_pos_w)[:, wheel_ids]
            solution = vertical_support_solution(jac,
                robot.root_physx_view.get_gravity_compensation_forces(), support_mask,
                robot.data.joint_effort_limits, min_force=30.)
            next_q = robot.data.joint_pos_target.clone()
            next_q[:, planner_ids] = next_joint
            pd = position_pd_effort(next_q, robot.data.joint_pos,
                torch.zeros_like(next_q), robot.data.joint_vel,
                robot.data.joint_stiffness, robot.data.joint_damping)
            result = guarded_effort(target=solution['effort'], previous=phase_effort,
                pd_effort=pd, limits=robot.data.joint_effort_limits,
                leg_mask=phase_leg_mask, enabled=solution['valid'],
                reset=torch.zeros(8, device=device, dtype=torch.bool), dt=env.step_dt)
            # IsaacLab net_forces_w contains NORMAL contact only, not friction.
            # This proxy must never be interpreted as complete inverse dynamics.
            measured_contact = sensor.data.net_forces_w[:, wheel_sensor_ids]
            gravity = robot.root_physx_view.get_gravity_compensation_forces()
            contact_effort_proxy = gravity - torch.einsum('bkcd,bkc->bd', jac, measured_contact)
            phase_effort_samples.append(dict(phase=phase, step=step,
                pd_effort=pd.tolist(), previous_effort=phase_effort.tolist(),
                desired_effort=solution['effort'].tolist(),
                normal_contact_effort_proxy=contact_effort_proxy[:, 6:].tolist(),
                contact_proxy_scope='normal_only_no_tangential_force_or_contact_moment',
                measured_base_residual=contact_effort_proxy[:, :6].tolist(),
                joint_velocity=robot.data.joint_vel.tolist(),
                joint_names=robot.joint_names,
                effort_error=(torch.where(phase_leg_mask[None], solution['effort'], 0.)-phase_effort).abs().amax(-1).tolist(),
                allocation_valid=solution['valid'].tolist(), valid=result['valid'].tolist(),
                normal_force=solution['normal_force'].tolist(), effort=result['effort'].tolist()))
            if not result['valid'].all():
                robot.set_joint_effort_target(torch.zeros_like(phase_effort))
                robot.write_data_to_sim()
                return False
            phase_effort = result['effort']
            robot.set_joint_effort_target(phase_effort)
            return True
    with torch.inference_mode():
        for step in range(32):
            if standing_contact_view is not None and step>=24:
                _, _, terminated, truncated, _ = observed_standing_step(action,'warmup',step)
            else:
                _, _, terminated, truncated, _ = env.step(action)
            if (terminated | truncated).any():
                stopped = 'warmup_reset'
                break
        entry_root = robot.data.root_pos_w.clone()
        roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
        entry_rpy = torch.stack((roll, pitch, extract_yaw_batch(robot.data.root_quat_w)), dim=-1)
        anchor = robot.data.body_pos_w[:, wheel_ids].clone()
        previous_root = entry_root.clone()
        previous_joint = robot.data.joint_pos[:, planner_ids].clone()
        entry_snapshot=dict(root=entry_root.tolist(),rpy=entry_rpy.tolist(),
            joint_names=list(robot.joint_names),joint_position=robot.data.joint_pos.tolist())
        anticipatory_goal=None
        reference_ready=torch.ones(8,device=device,dtype=torch.bool)
        if args.anticipatory_prepare and stopped is None:
            from ame_baseline.m1_anticipatory_support import entry_plan,fixed_reference_step
            from ame_baseline.m1_mass_predictor import load_usd_model
            from go2_pvcnn.assets.m1 import M1_USD_PATH
            threads=torch.get_num_threads()
            try:
                torch.set_num_threads(2)
                plan=entry_plan(model=load_usd_model(M1_USD_PATH),
                    root=entry_root.cpu().double(),rpy=entry_rpy.cpu().double(),
                    anchors=anchor.cpu().double(),selected=selected.cpu(),
                    wheel_q=robot.data.joint_pos[:,wheel_joint_ids].cpu().double(),height=args.lift_height,
                    translation_only=True)
            finally:
                torch.set_num_threads(threads)
            anticipatory_goal=plan['root'].to(entry_root)
            # This first runtime path executes translations only, never silently
            # discards a selected attitude change from the broader static search.
            attitude_ok=(plan['rpy']-entry_rpy.cpu().double()).abs().amax(-1)<=1e-7
            print('M1_ANTICIPATORY_ENTRY '+json.dumps(dict(valid=plan['valid'].tolist(),
                attitude_supported=attitude_ok.tolist(),root=plan['root'].tolist(),
                rpy=plan['rpy'].tolist(),scope='sampled_static_not_physical_success')),flush=True)
            if not (plan['valid']&attitude_ok).all():stopped='anticipatory_entry_rejected'
            reference_ready.zero_()
        total_weight = robot.root_physx_view.get_masses().sum(-1).to(device) * 9.81
        entry_fk_error = (m1_fk(entry_root, entry_rpy, previous_joint).foot_pos_w - anchor).norm(dim=-1)
        if args.standing_effort_steps and stopped is None:
            from ame_baseline.m1_dynamics import point_linear_jacobian
            from ame_baseline.m1_support_effort import vertical_support_solution
            from ame_baseline.m1_effort_guard import guarded_effort
            leg_mask = torch.zeros(16, dtype=torch.bool, device=device)
            leg_mask[planner_ids] = True
            effort = torch.zeros_like(robot.data.joint_pos)
            standing_samples = []
            for effort_step in range(args.standing_effort_steps):
                from ame_baseline.m1_rolling_speed import window_speed
                standing_speed=window_speed(effort_step,standing_start,standing_duration,env.step_dt,.1) if args.standing_roll else 0.
                action[:,wheel_cols]=standing_speed
                obs = observe_support(robot, sensor, selected)
                jac = point_linear_jacobian(robot.root_physx_view.get_jacobians(),
                    robot.data.body_com_pos_w, robot.data.body_pos_w)[:, wheel_ids]
                solution = vertical_support_solution(jac,
                    robot.root_physx_view.get_gravity_compensation_forces(),
                    torch.ones((8, 4), device=device, dtype=torch.bool), robot.data.joint_effort_limits)
                pd = (robot.data.joint_stiffness * (robot.data.joint_pos_target-robot.data.joint_pos)
                      + robot.data.joint_damping * (robot.data.joint_vel_target-robot.data.joint_vel))
                contact_ok = (obs['force'] > 10.).all(-1)
                contact_ok &= (sensor.data.net_forces_w[:, nonsupport_ids].norm(dim=-1).amax(-1) <= 10.)
                pose_ok = (obs['tilt'].abs() <= .15).all(-1) & (obs['tilt_rate'].abs() <= .20).all(-1)
                proposal = guarded_effort(target=solution['effort'] * args.standing_effort_gain, previous=effort,
                    pd_effort=pd, limits=robot.data.joint_effort_limits, leg_mask=leg_mask,
                    enabled=solution['valid'] & contact_ok & pose_ok,
                    reset=torch.zeros(8, device=device, dtype=torch.bool), dt=env.step_dt)
                standing_samples.append(dict(step=effort_step, root=robot.data.root_pos_w.tolist(),
                    requested_speed=standing_speed,
                    wheel_velocity_target=robot.data.joint_vel_target[:,wheel_joint_ids].tolist(),
                    wheel_velocity_actual=robot.data.joint_vel[:,wheel_joint_ids].tolist(),
                    wheel_joint_position=robot.data.joint_pos[:,wheel_joint_ids].tolist(),
                    wheel_center=robot.data.body_pos_w[:,wheel_ids].tolist(),
                    wheel_estimated_torque=robot.data.computed_torque[:,wheel_joint_ids].tolist(),
                    force=obs['force'].tolist(), tilt=obs['tilt'].tolist(),
                    leg_tracking_error=(robot.data.joint_pos_target[:, planner_ids]-robot.data.joint_pos[:, planner_ids]).abs().amax(-1).tolist(),
                    valid=proposal['valid'].tolist(), effort=proposal['effort'].tolist()))
                if contact_audit is not None and effort_step in (60,80,100,120,140,160):
                    nf,cp,cn,sep,nc,ns=contact_audit.get_contact_data(dt=cfg.sim.dt)
                    ff,fp,fc,fs=contact_audit.get_friction_data(dt=cfg.sim.dt)
                    def contact_rows(counts,starts,arrays):
                        rows=[]
                        for count,start in zip(counts.flatten().tolist(),starts.flatten().tolist()):
                            rows.append([v[start:start+count].tolist() for v in arrays])
                        return rows
                    print('M1_CONTACT_PATCH '+json.dumps(dict(step=effort_step,
                        net=contact_audit.get_net_contact_forces(dt=cfg.sim.dt).tolist(),
                        counts=nc.tolist(),normal=contact_rows(nc,ns,(nf,cp,cn,sep)),
                        friction=contact_rows(fc,fs,(ff,fp)))),flush=True)
                if not proposal['valid'].all():
                    stopped = 'standing_effort_guard_rejected'
                    break
                effort = proposal['effort']
                robot.set_joint_effort_target(effort)
                if standing_contact_view is not None:
                    _, _, terminated, truncated, _ = observed_standing_step(action,'standing',effort_step)
                else:
                    _, _, terminated, truncated, _ = env.step(action)
                if (terminated | truncated).any():
                    stopped = 'standing_effort_episode_reset'
                    break
            robot.set_joint_effort_target(torch.zeros_like(effort))
            robot.write_data_to_sim()
            print('M1_STANDING_EFFORT ' + json.dumps(dict(samples=standing_samples,
                stopped=stopped, final_root=robot.data.root_pos_w.tolist(),
                gain=args.standing_effort_gain,
                standing_roll=args.standing_roll,
                cleared=bool((robot.data.joint_effort_target == 0).all()))), flush=True)
            stopped = stopped or 'standing_only_complete'
        if args.wbc_snapshot:
            from ame_baseline.m1_wbc_dynamics import generalized_snapshot, mass_from_links
            from ame_baseline.m1_wbc_materials import conservative_friction
            from isaaclab.utils.math import matrix_from_quat
            from pxr import Usd, UsdPhysics, UsdShade, PhysxSchema
            import omni.usd
            stage = omni.usd.get_context().get_stage()
            def bound_material(prim):
                material,_ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial(materialPurpose='physics')
                if not material:
                    raise RuntimeError('missing bound physics material: '+str(prim.GetPath()))
                mode = PhysxSchema.PhysxMaterialAPI(material.GetPrim()).GetFrictionCombineModeAttr().Get()
                mode_source='bound_material'
                if mode is None and not material.GetPrim().HasAPI(PhysxSchema.PhysxMaterialAPI):
                    definition=Usd.SchemaRegistry().FindAppliedAPIPrimDefinition('PhysxMaterialAPI')
                    if not definition:
                        raise RuntimeError('installed material schema fallback unavailable')
                    mode=definition.GetAttributeFallbackValue('physxMaterial:frictionCombineMode')
                    mode_source='installed_PhysxMaterialAPI_default_no_applied_API'
                physics = UsdPhysics.MaterialAPI(material.GetPrim())
                return dict(path=str(material.GetPath()),mode=mode,mode_source=mode_source,
                    coefficients=[physics.GetStaticFrictionAttr().Get(),
                        physics.GetDynamicFrictionAttr().Get(),physics.GetRestitutionAttr().Get()])
            ground_material = bound_material(stage.GetPrimAtPath('/World/ground/terrain/mesh'))
            material_records=[]
            for index,name in enumerate(wheel_names):
                link_path=robot.root_physx_view.link_paths[0][wheel_ids[index]]
                authored=[bound_material(prim) for prim in Usd.PrimRange(
                    stage.GetPrimAtPath(link_path),Usd.TraverseInstanceProxies())
                    if prim.HasAPI(UsdPhysics.CollisionAPI)]
                if not authored:
                    raise RuntimeError('wheel collision material binding not found')
                live=wbc_material_views[name].get_material_properties().tolist()
                if len(live)!=1 or not live[0]:
                    raise RuntimeError('expected one nonempty native wheel material view')
                # Shape/material ordering need not coincide: take conservative
                # bound across every possible pairing, with no default mu.
                expanded=[row for row in live[0] for material in authored]
                modes=[material['mode'] for row in live[0] for material in authored]
                print('M1_WBC_MATERIAL_INPUT '+json.dumps(dict(wheel=name,
                    live_coefficients=live,authored=authored,ground=ground_material)),flush=True)
                mu=conservative_friction(expanded,modes,ground_material['coefficients'],ground_material['mode'])
                material_records.append(dict(wheel=name,live_coefficients=live[0],
                    authored_materials=authored,conservative_mu=mu))
            print('M1_WBC_MATERIALS '+json.dumps(dict(ground=ground_material,
                wheels=material_records,scope='env0_live_wheel_coefficients_all_pair_mode_bound',
                ground_source='bound_USD_unrandomized_terrain')),flush=True)
            native = generalized_snapshot(robot.root_physx_view, robot.joint_names,
                robot.joint_names, zero, 32)
            native_jac = robot.root_physx_view.get_jacobians().clone()
            native_masses = robot.root_physx_view.get_masses().to(device)
            gravity_oracle = (native_jac[:, :, 2]*native_masses[:, :, None]).sum(1)*9.81
            translation_oracle = native_masses.sum(1)[:, None, None]*torch.eye(3, device=device)
            inertia_local = robot.root_physx_view.get_inertias().to(device).reshape(8, -1, 3, 3)
            com_rotation = matrix_from_quat(robot.data.body_com_quat_w)
            com_inertia_world = com_rotation @ inertia_local @ com_rotation.transpose(-1, -2)
            armature = robot.root_physx_view.get_dof_armatures().to(device)
            com_frame_mass = mass_from_links(native_jac, native_masses, com_inertia_world, armature)
            # Installed backend verified against full native M: inertia is about
            # COM but expressed in actor axes, despite API docstring. Keep both.
            link_rotation = matrix_from_quat(robot.data.body_link_quat_w)
            inertia_world = link_rotation @ inertia_local @ link_rotation.transpose(-1, -2)
            mass_oracle = mass_from_links(native_jac, native_masses, inertia_world, armature)
            generalized_velocity = torch.cat((robot.data.root_com_vel_w, robot.data.joint_vel), dim=1)
            link_velocity_oracle = (native_jac @ generalized_velocity[:, None, :, None]).squeeze(-1)
            measured_velocity = robot.data.body_com_vel_w
            native_energy = .5*torch.einsum('bi,bij,bj->b', generalized_velocity, native['mass'], generalized_velocity)
            measured_energy = .5*(native_masses*measured_velocity[..., :3].square().sum(-1)).sum(-1)
            measured_energy += .5*torch.einsum('bli,blij,blj->b', measured_velocity[..., 3:], inertia_world, measured_velocity[..., 3:])
            measured_energy += .5*(armature*robot.data.joint_vel.square()).sum(-1)
            print('M1_WBC_NATIVE '+json.dumps(dict(
                scope='read_only_static_consistency_not_control_acceptance',
                full_mass_error=(native['mass']-mass_oracle).abs().amax((1,2)).tolist(),
                com_inertia_mass_error=(native['mass']-com_frame_mass).abs().amax((1,2)).tolist(),
                full_mass_difference=(native['mass']-mass_oracle).tolist(),
                inertia_local=inertia_local.tolist(),
                com_quat_local=robot.data.body_com_quat_b.tolist(),
                link_velocity_error=(link_velocity_oracle-measured_velocity).abs().amax((1,2)).tolist(),
                energy_error=(native_energy-measured_energy).abs().tolist(),
                native_energy=native_energy.tolist(), measured_energy=measured_energy.tolist(),
                armature=armature.tolist(),
                joint_names=robot.joint_names,
                mass=native['mass'].tolist(), gravity=native['gravity'].tolist(),
                coriolis=native['coriolis'].tolist(),
                gravity_error=(native['gravity']-gravity_oracle).abs().amax(1).tolist(),
                translation_mass_error=(native['mass'][:, :3, :3]-translation_oracle).abs().amax((1,2)).tolist(),
                symmetry_error=(native['mass']-native['mass'].transpose(1,2)).abs().amax((1,2)).tolist(),
                min_eigenvalue=torch.linalg.eigvalsh(native['mass'].double()).amin(1).tolist(),
                joint_velocity=robot.data.joint_vel.tolist(),
                root_velocity=robot.data.root_vel_w.tolist())),flush=True)
            stopped = 'wbc_read_only_complete'
            from ame_baseline.m1_wbc_contacts import contact_geometry
            import numpy as np
            points, normals, owners, strengths, closure = [], [], [], [], []
            raw_contacts=[]
            for owner,name in enumerate(wheel_names):
                contact_view = wbc_contact_views[name]
                nf,cp,cn,sep,nc,ns = contact_view.get_contact_data(dt=cfg.sim.dt)
                indices = []
                for count,start in zip(nc.flatten().tolist(),ns.flatten().tolist()):
                    if start < 0 or count < 0 or start+count > len(nf):
                        raise RuntimeError('contact buffer range rejected')
                    indices.extend(range(start,start+count))
                if len(indices) != len(set(indices)):
                    raise RuntimeError('overlapping contact buffer ranges')
                summed = torch.zeros(3,device=nf.device)
                for index in indices:
                    strength = float(nf.flatten()[index])
                    if not np.isfinite(strength) or strength < 0:
                        raise RuntimeError('invalid contact normal strength')
                    raw_contacts.append(dict(owner=owner,point=cp[index].tolist(),
                        normal=cn[index].tolist(),native_separation=float(sep.flatten()[index]),
                        normal_strength=strength))
                    if strength > 0:
                        points.append(cp[index].tolist()); normals.append(cn[index].tolist())
                        strengths.append(strength); owners.append(owner)
                        summed += strength*cn[index]
                native_normal = contact_view.get_net_contact_forces(dt=cfg.sim.dt).reshape(-1,3).sum(0)
                error = float((summed-native_normal).abs().max())
                closure.append(error)
                if not np.isfinite(error) or error > 1e-3:
                    raise RuntimeError('contact force closure rejected')
            from ame_baseline.m1_wbc_motion import contact_motion
            motion=contact_motion(
                points=np.asarray([r['point'] for r in raw_contacts]).reshape(-1,3),
                normals=np.asarray([r['normal'] for r in raw_contacts]).reshape(-1,3),
                owners=np.asarray([r['owner'] for r in raw_contacts],dtype=np.int64),
                com_positions=robot.data.body_com_pos_w[0,wheel_ids].cpu().numpy(),
                com_velocity=robot.data.body_com_vel_w[0,wheel_ids].cpu().numpy(),
                surface_velocity=np.zeros((len(raw_contacts),3)))
            print('M1_WBC_CONTACT_MOTION '+json.dumps(dict(contacts=raw_contacts,
                **{key:value.tolist() for key,value in motion.items()},
                surface='fixed_ground_terrain_mesh',scope='measured_state_not_rest_counterfactual',
                zero_force_contacts_included=True)),flush=True)
            contact = contact_geometry(np.asarray(points).reshape(-1,3),
                np.asarray(normals).reshape(-1,3),np.asarray(owners,dtype=np.int64),
                native_jac[0,wheel_ids].cpu().numpy(),
                robot.data.body_com_pos_w[0,wheel_ids].cpu().numpy())
            delta = np.asarray(points).reshape(-1,3)-robot.data.body_com_pos_w[0,wheel_ids].cpu().numpy()[owners]
            velocities = robot.data.body_com_vel_w[0,wheel_ids].cpu().numpy()[owners]
            direct = velocities[:,:3]+np.cross(velocities[:,3:],delta)
            via_jac = contact['jac']@generalized_velocity[0].cpu().numpy()
            print('M1_WBC_CONTACTS '+json.dumps(dict(points=points,normals=normals,
                owners=owners,normal_strength=strengths,force_closure_error=closure,
                point_velocity_error=float(np.max(np.abs(direct-via_jac))) if len(points) else None,
                counts=[owners.count(i) for i in range(4)],
                scope='read_only_point_geometry_no_acceleration_constraint')),flush=True)
            from ame_baseline.m1_wbc_qp import solve_wbc
            backend_limits=robot.root_physx_view.get_dof_max_forces()[0].cpu().numpy()
            configured_limits=robot.data.joint_effort_limits[0].cpu().numpy()
            effort_limits=np.minimum(backend_limits,configured_limits)
            weight=float(native_masses[0].sum()*9.81)
            static_qp=solve_wbc(mass=native['mass'][0].double().cpu().numpy(),
                bias=native['gravity'][0].double().cpu().numpy(),
                jac=contact['jac'],frames=contact['frames'],
                mu=np.array([material_records[int(owner)]['conservative_mu'] for owner in owners]),
                normal_min=np.zeros(len(points)),normal_max=np.full(len(points),weight),
                accel_lower=np.zeros(22),accel_upper=np.zeros(22),
                effort_lower=-effort_limits,effort_upper=effort_limits,
                contact_matrix=contact['jac'].reshape(-1,22),contact_rhs=np.zeros(3*len(points)),
                group_ids=contact['group_ids'],group_min=np.full(4,35.),group_max=np.full(4,weight))
            static_record={key:value.tolist() if isinstance(value,np.ndarray) else value
                for key,value in static_qp.items()}
            static_record.update(scope='env0_zero_velocity_counterfactual_not_applied',
                effort_limits=effort_limits.tolist(),joint_names=robot.joint_names,
                wheel_names=wheel_names,weight=weight)
            if static_qp['valid']:
                normal=np.einsum('ki,ki->k',static_qp['force'],contact['frames'][:,:,2])
                static_record['wheel_normal']=[float(normal[contact['group_ids']==i].sum()) for i in range(4)]
            print('M1_WBC_STATIC_QP '+json.dumps(static_record),flush=True)
            from ame_baseline.m1_wbc_candidates import rest_contact_candidates
            from ame_baseline.m1_wbc_modes import contact_mode_constraints
            modes=rest_contact_candidates(np.asarray(points),contact['group_ids'])
            # Counterfactual v=0: no velocity bias or assumed smooth-wheel
            # migration. Measured geometry is held fixed for this shadow solve.
            stability_a=np.eye(22)[[1,3,4,5]]
            rolling_a=np.vstack((np.eye(22)[0],native_jac[0,wheel_ids,4].cpu().numpy()))
            rolling_b=np.r_[.05,np.full(4,.05/M1_WHEEL_RADIUS_M)]
            leg_a=np.eye(22)[[6+i for i,name in enumerate(robot.joint_names)
                if name not in M1_WHEEL_JOINT_NAMES]]
            accel_bound=np.r_[np.full(3,.05),np.full(3,.2),np.ones(16)]
            shadow_records=[]
            for attached in modes:
                mode=contact_mode_constraints(jac=contact['jac'],frames=contact['frames'],
                    bias=np.zeros((len(points),3)),attached=attached,
                    normal_max=np.full(len(points),weight),separation_accel_min=np.zeros(len(points)))
                qp_input=dict(mass=native['mass'][0].double().cpu().numpy(),
                    bias=native['gravity'][0].double().cpu().numpy(),
                    jac=contact['jac'],frames=contact['frames'],
                    mu=np.array([material_records[int(owner)]['conservative_mu'] for owner in owners]),
                    normal_min=np.zeros(len(points)),accel_lower=-accel_bound,accel_upper=accel_bound,
                    effort_lower=-effort_limits,effort_upper=effort_limits,
                    group_ids=contact['group_ids'],group_min=np.full(4,35.),group_max=np.full(4,weight),
                    tasks=((stability_a,np.zeros(4),np.ones(4)),
                           (rolling_a,rolling_b,np.ones(5)),(leg_a,np.zeros(12),np.ones(12))),**mode)
                print('M1_WBC_REPLAY_INPUT '+json.dumps(dict(attached=attached.tolist(),
                    kwargs=qp_input),default=lambda value:value.tolist()),flush=True)
                result=solve_wbc(**qp_input)
                record=dict(attached=attached.tolist(),valid=result['valid'],reason=result['reason'],
                    stages=result['stages'])
                if result['valid']:
                    normal_accel=np.einsum('ki,ki->k',contact['frames'][:,:,2],contact['jac']@result['qdd'])
                    record.update(rolling_achieved=(rolling_a@result['qdd']).tolist(),
                        rolling_error=float(np.linalg.norm(rolling_a@result['qdd']-rolling_b)),
                        stability_error=float(np.max(np.abs(stability_a@result['qdd']))),
                        released_normal_accel=normal_accel[~attached].tolist(),
                        released_force_max=float(np.max(np.abs(result['force'][~attached]))) if (~attached).any() else 0.,
                        max_violation=result['max_violation'],qdd=result['qdd'].tolist(),
                        effort=result['effort'].tolist())
                shadow_records.append(record)
            print('M1_WBC_ROLL_SHADOW '+json.dumps(dict(candidates=shadow_records,
                target=rolling_b.tolist(),scope='zero_velocity_counterfactual_not_applied',
                migration='fixed_material_modes_no_smooth_circle_assumption')),flush=True)
            from ame_baseline.m1_wbc_contact_step import contact_step_constraints
            from ame_baseline.m1_wbc_kinematics import kinematic_bias
            from ame_baseline.m1_mass_predictor import load_usd_model
            from go2_pvcnn.assets.m1 import M1_USD_PATH
            kinematic_model=load_usd_model(M1_USD_PATH)
            kin=kinematic_bias(kinematic_model,robot.joint_names,robot.body_names,
                link_rotation[0].cpu().numpy(),
                robot.data.body_com_vel_w[0,:,3:].cpu().numpy(),
                robot.data.joint_vel[0].cpu().numpy())
            live_points=np.asarray([r['point'] for r in raw_contacts]).reshape(-1,3)
            live_owners=np.asarray([r['owner'] for r in raw_contacts],dtype=np.int64)
            live_gap=np.asarray([r['native_separation'] for r in raw_contacts])
            live=contact_geometry(live_points,
                np.asarray([r['normal'] for r in raw_contacts]).reshape(-1,3),live_owners,
                native_jac[0,wheel_ids].cpu().numpy(),
                robot.data.body_com_pos_w[0,wheel_ids].cpu().numpy())
            arms=live_points-robot.data.body_com_pos_w[0,wheel_ids].cpu().numpy()[live_owners]
            omega=robot.data.body_com_vel_w[0,wheel_ids,3:].cpu().numpy()[live_owners]
            live_bias=(kin['com_linear'][wheel_ids][live_owners]
                +np.cross(kin['angular'][wheel_ids][live_owners],arms)
                +np.cross(omega,np.cross(omega,arms)))
            from ame_baseline.m1_wbc_joint_bounds import joint_step_bounds
            from ame_baseline.m1_wbc_limits import diagnostic_speed_limits
            from ame_baseline.m1_ame_contract import M1_WHEEL_SPEED_LIMIT_RAD_S
            joint_position=robot.data.joint_pos[0].cpu().numpy()
            joint_velocity=robot.data.joint_vel[0].cpu().numpy()
            native_position_limits=robot.root_physx_view.get_dof_limits()[0].cpu().numpy()
            configured_position_limits=robot.data.joint_pos_limits[0].cpu().numpy()
            position_limits=np.c_[np.maximum(native_position_limits[:,0],configured_position_limits[:,0]),
                                  np.minimum(native_position_limits[:,1],configured_position_limits[:,1])]
            velocity_limits=np.minimum(robot.root_physx_view.get_dof_max_velocities()[0].cpu().numpy(),
                                       robot.data.joint_vel_limits[0].cpu().numpy())
            raw_velocity_limits=velocity_limits.copy()
            velocity_limits=diagnostic_speed_limits(names=robot.joint_names,
                leg_names=M1_PLANNER_JOINT_NAMES,wheel_names=M1_WHEEL_JOINT_NAMES,
                native_limits=raw_velocity_limits,leg_cap=.5,wheel_cap=M1_WHEEL_SPEED_LIMIT_RAD_S)
            print('M1_WBC_EFFORT_SOURCES '+json.dumps(dict(
                actuation=robot.root_physx_view.get_dof_actuation_forces()[0].tolist(),
                projected=robot.root_physx_view.get_dof_projected_joint_forces()[0].tolist(),
                cached_applied=robot.data.applied_torque[0].tolist(),
                stiffness=robot.root_physx_view.get_dof_stiffnesses()[0].tolist(),
                damping=robot.root_physx_view.get_dof_dampings()[0].tolist(),
                scope='source_inventory_not_verified_total_effort_history',
                may_initialize_history=False)),flush=True)
            joint_bounds=joint_step_bounds(position=joint_position,velocity=joint_velocity,
                position_limits=position_limits,velocity_limits=velocity_limits,dt=cfg.sim.dt)
            print('M1_WBC_STATE_BOUNDS '+json.dumps(dict(joint_names=robot.joint_names,
                position=joint_position.tolist(),velocity=joint_velocity.tolist(),
                position_limits=position_limits.tolist(),velocity_limits=velocity_limits.tolist(),
                raw_velocity_limits=raw_velocity_limits.tolist(),leg_speed_policy=.5,
                speed_provenance='explicit_conservative_diagnostic_caps_not_manufacturer_ratings',
                acceleration={key:value.tolist() for key,value in joint_bounds.items()},
                scope='one_step_authored_joint_state_not_reference_limit')),flush=True)
            live_records=[];authored_records=[]
            for attached in rest_contact_candidates(live_points,live_owners):
                mode=contact_step_constraints(jac=live['jac'],frames=live['frames'],
                    bias=live_bias,velocity=motion['relative_velocity'],gap=live_gap,
                    attached=attached,normal_max=np.full(len(live_points),weight),dt=cfg.sim.dt)
                live_input=dict(mass=native['mass'][0].double().cpu().numpy(),
                    bias=native['bias'][0].double().cpu().numpy(),jac=live['jac'],frames=live['frames'],
                    mu=np.array([material_records[int(i)]['conservative_mu'] for i in live_owners]),
                    normal_min=np.zeros(len(live_points)),accel_lower=-accel_bound,accel_upper=accel_bound,
                    effort_lower=-effort_limits,effort_upper=effort_limits,
                    group_ids=live_owners,group_min=np.full(4,35.),group_max=np.full(4,weight),
                    tasks=((stability_a,np.zeros(4),np.ones(4)),(leg_a,np.zeros(12),np.ones(12))),**mode)
                print('M1_WBC_LIVE_REPLAY '+json.dumps(dict(attached=attached.tolist(),kwargs=live_input),
                    default=lambda value:value.tolist()),flush=True)
                result=solve_wbc(**live_input)
                record=dict(attached=attached.tolist(),valid=result['valid'],reason=result['reason'],
                    stages=result['stages'])
                if result['valid']:
                    next_velocity=motion['relative_velocity']+cfg.sim.dt*(live['jac']@result['qdd']+live_bias)
                    next_normal=np.einsum('ki,ki->k',live['frames'][:,:,2],next_velocity)
                    record.update(predicted_normal_speed=next_normal.tolist(),
                        predicted_gap=(live_gap+cfg.sim.dt*next_normal).tolist(),
                        predicted_slip=np.linalg.norm(next_velocity-next_normal[:,None]*live['frames'][:,:,2],axis=1).tolist(),
                        max_violation=result['max_violation'],effort=result['effort'].tolist(),qdd=result['qdd'].tolist())
                live_records.append(record)
                authored_input=dict(live_input,
                    accel_lower=np.r_[-accel_bound[:6],joint_bounds['lower']],
                    accel_upper=np.r_[accel_bound[:6],joint_bounds['upper']])
                print('M1_WBC_AUTHORED_REPLAY '+json.dumps(dict(attached=attached.tolist(),kwargs=authored_input),
                    default=lambda value:value.tolist()),flush=True)
                authored=solve_wbc(**authored_input)
                authored_record=dict(attached=attached.tolist(),valid=authored['valid'],
                    reason=authored['reason'],stages=authored['stages'])
                if authored['valid']:
                    next_joint_velocity=joint_velocity+cfg.sim.dt*authored['qdd'][6:]
                    next_joint_position=joint_position+cfg.sim.dt*next_joint_velocity
                    authored_record.update(max_violation=authored['max_violation'],
                        qdd=authored['qdd'].tolist(),effort=authored['effort'].tolist(),
                        predicted_joint_velocity=next_joint_velocity.tolist(),
                        predicted_joint_position=next_joint_position.tolist(),
                        max_velocity_excess=float(np.maximum(0.,np.abs(next_joint_velocity)-velocity_limits).max()),
                        max_position_excess=float(np.maximum(0.,np.maximum(position_limits[:,0]-next_joint_position,
                                                                  next_joint_position-position_limits[:,1])).max()))
                authored_records.append(authored_record)
            print('M1_WBC_AUTHORED_STEP '+json.dumps(dict(candidates=authored_records,
                scope='authored_joint_bounds_shadow_not_applied',root_box_unchanged=True)),flush=True)
            print('M1_WBC_LIVE_STEP '+json.dumps(dict(candidates=live_records,dt=cfg.sim.dt,
                point_bias=live_bias.tolist(),coriolis=native['coriolis'][0].tolist(),
                scope='measured_velocity_semiimplicit_shadow_not_applied',
                model='fixed_material_point_one_step_not_impact_certificate')),flush=True)
        dynamics = None
        if args.dynamics_audit:
            # Read-only audit: no effort targets or simulator state are changed.
            from ame_baseline.m1_dynamics import point_linear_jacobian
            view = robot.root_physx_view
            jac = view.get_jacobians().clone()
            gravity = view.get_gravity_compensation_forces().clone()
            masses = view.get_masses().to(device)
            expected_shape = (8, len(robot.body_names), 6, len(robot.joint_names)+6)
            if tuple(jac.shape) != expected_shape or tuple(gravity.shape) != (8, len(robot.joint_names)+6):
                raise RuntimeError(f'unexpected floating-base dynamics dimensions: {jac.shape}, {gravity.shape}')
            planner_dofs = [6+i for i in planner_ids]
            finite_difference = []
            for j in range(12):
                plus, minus = previous_joint.double().clone(), previous_joint.double().clone()
                plus[:, j] += 1e-4
                minus[:, j] -= 1e-4
                finite_difference.append((m1_fk(entry_root.double(), entry_rpy.double(), plus).foot_pos_w
                                          - m1_fk(entry_root.double(), entry_rpy.double(), minus).foot_pos_w)/2e-4)
            fk_jac = torch.stack(finite_difference, -1)
            wheel_jac = jac[:, wheel_ids, :3]
            offset = robot.data.body_com_pos_w - robot.data.body_pos_w
            angular = jac[:, :, 3:].transpose(-1, -2)
            com_jac = jac[:, :, :3] + torch.cross(angular, offset[:, :, None].expand_as(angular), dim=-1).transpose(-1, -2)
            origin_jac = point_linear_jacobian(jac, robot.data.body_com_pos_w, robot.data.body_pos_w)
            raw_gravity = (jac[:, :, 2] * masses[:, :, None]).sum(1)*9.81
            com_gravity = (com_jac[:, :, 2] * masses[:, :, None]).sum(1)*9.81
            wheel_sensor_ids = list(resolve_named_indices(tuple(sensor.body_names), wheel_names))
            contact = sensor.data.net_forces_w[:, wheel_sensor_ids]
            # Center-force proxy only: net contact moment/point and dynamic
            # terms are not resolved by this audit; never apply it as torque.
            static_effort = gravity - torch.einsum('blcd,blc->bd', origin_jac[:, wheel_ids], contact)
            from ame_baseline.m1_support_effort import vertical_support_solution
            allocation = vertical_support_solution(
                origin_jac[:, wheel_ids], gravity,
                torch.ones((8, 4), device=device, dtype=torch.bool),
                robot.data.joint_effort_limits)
            dynamics = dict(
                vertical_allocation={key: value.tolist() for key, value in allocation.items()},
                allocation_scope='read_only_static_vertical_no_actuator_write',
                jacobian_shape=list(jac.shape), gravity_shape=list(gravity.shape),
                static_effort_scope='wheel_center_force_proxy_not_command',
                total_mass=masses.sum(-1).tolist(), gravity_root=gravity[:, :6].tolist(),
                gravity_raw_jac_error=(gravity-raw_gravity).abs().amax(-1).tolist(),
                gravity_com_jac_error=(gravity-com_gravity).abs().amax(-1).tolist(),
                wheel_fk_jac_error=(wheel_jac[..., planner_dofs]-fk_jac).abs().flatten(1).amax(-1).tolist(),
                wheel_origin_fk_jac_error=(origin_jac[:, wheel_ids][..., planner_dofs]-fk_jac).abs().flatten(1).amax(-1).tolist(),
                root_translation_jac_error=(wheel_jac[..., :3]-torch.eye(3, device=device)).abs().flatten(1).amax(-1).tolist(),
                static_effort_leg=static_effort[:, planner_dofs].tolist(),
                estimated_effort_leg=robot.data.computed_torque[:, planner_ids].tolist(),
                static_base_residual=static_effort[:, :6].tolist(),
                gravity_leg=gravity[:, planner_dofs].tolist())
            print('M1_DYNAMICS_AUDIT ' + json.dumps(dynamics), flush=True)
        gate = PrepareGate(8, device)
        hold_speed=torch.zeros((8,4),device=device)
        if args.prepare_wheel_hold_only or args.phase_wheel_hold:
            from ame_baseline.m1_rolling_speed import anchor_hold_speed,hold_effort
            from ame_baseline.m1_ame_contract import M1_WHEEL_ACTION_SCALE_RAD_S
            if (robot.data.joint_stiffness[:,wheel_joint_ids]!=0).any():
                raise RuntimeError('wheel holding effort model requires zero stiffness')
        def write_phase_wheels(phase,step,reference,measured,forward=0.):
            from ame_baseline.m1_rolling_speed import phase_hold_speed
            command=phase_hold_speed(reference,measured,extract_yaw_batch(robot.data.root_quat_w),
                hold_speed,env.step_dt,phase,selected,forward)
            if (robot.data.joint_effort_target[:,wheel_joint_ids]!=0).any():
                raise RuntimeError('phase wheel hold requires zero feedforward')
            predicted=hold_effort(command,robot.data.joint_vel[:,wheel_joint_ids],
                robot.data.joint_damping[:,wheel_joint_ids],robot.data.joint_effort_limits[:,wheel_joint_ids],
                M1_WHEEL_ACTION_SCALE_RAD_S)
            action[:,wheel_cols]=command
            print('M1_PHASE_WHEEL_HOLD '+json.dumps(dict(phase=phase,step=step,
                speed=command.tolist(),predicted_effort=predicted.tolist())),flush=True)
            return command
        transfer_velocity=torch.zeros((8,2),device=device)
        prepare_controller=None
        prepare_outcome=None
        pd_unload_samples=[]
        pd_unload_outcome=None
        if args.batched_prepare and stopped is None:
            from ame_baseline.m1_prepare_controller import M1PrepareController
            prepare_controller=M1PrepareController(root=entry_root,rpy=entry_rpy,
                joint=previous_joint,anchors=anchor,selected=selected,episode=zero,
                obstacle=zero,total_weight=total_weight,timeout_steps=args.num_steps+1)
        for step in range(args.num_steps if stopped is None else 0):
            observed = observe_support(robot, sensor, selected)
            non_support = sensor.data.net_forces_w[:, nonsupport_ids].norm(dim=-1).amax(-1)
            if prepare_controller is not None:
                result=prepare_controller.update(observed=observed,
                    live_root=robot.data.root_pos_w,collision=non_support>10.,
                    step=torch.full_like(zero,step),dt=env.step_dt)
                proposal=dict(root=result['root'],joint=result['joint'],valid=result['accepted'],
                    reason=result['reason'],post_lift_load_ready=result['post_lift_load_ready'])
                ready=result['ready']
                if result['lift_authorized'].any():
                    raise RuntimeError('PREPARE must never authorize unmeasured UNLOAD/lift')
            elif args.anticipatory_prepare:
                proposal=fixed_reference_step(entry=entry_root,rpy=entry_rpy,anchors=anchor,
                    previous=previous_root,velocity=transfer_velocity,previous_joint=previous_joint,
                    goal=anticipatory_goal,dt=env.step_dt)
                reference_ready=proposal['post_lift_load_ready']
            else:
                proposal = transfer_target(
                    entry_root=entry_root, entry_rpy=entry_rpy, anchor_w=anchor,
                    support_w=observed['wheel_pos_w'],
                    live_root=robot.data.root_pos_w, live_com=observed['com_w'],
                    selected_leg=selected, previous_root=previous_root,
                    previous_joint=previous_joint, dt=env.step_dt, root_speed=args.transfer_speed,
                    max_root_shift=args.max_root_shift,
                    total_weight=total_weight if args.prepare_load_floor else None,
                    support_floor=prepare_reserve if args.unload_com else 30.)
            if prepare_controller is None:
                ready = gate.update(
                    episode=zero, obstacle=zero, leg=selected,
                    step=torch.full_like(zero, step), force=observed['force'],
                    tilt=observed['tilt'], tilt_rate=observed['tilt_rate'], margin=observed['margin'],
                    ik_valid=proposal['valid'] & proposal['post_lift_load_ready'], collision=non_support > 10.)
            samples.append(dict(
                step=step, pre_action=True, margin=observed['margin'].tolist(),
                force=observed['force'].tolist(), tilt=observed['tilt'].tolist(),
                tilt_rate=observed['tilt_rate'].tolist(), com_w=observed['com_w'].tolist(),
                root_w=robot.data.root_pos_w.tolist(), target_root_w=proposal['root'].tolist(),
                wheel_pos_w=observed['wheel_pos_w'].tolist(),
                valid=proposal['valid'].tolist(), reason=proposal['reason'].tolist(),
                ready=ready.tolist(), post_lift_load_ready=proposal['post_lift_load_ready'].tolist(),
                non_support_force=non_support.tolist()))
            if step % 8 == 0 or not proposal['valid'].all() or ready.all():
                print('M1_PREPARE_STEP '+json.dumps(samples[-1]),flush=True)
            # Diagnostic fail-stop, not a recovery controller. No commands after rejection.
            if not proposal['valid'].all():
                stopped = 'proposal_rejected'
                break
            if (observed['tilt'].abs() > .3).any() or (non_support > 10).any():
                stopped = 'unsafe_pose_or_contact'
                break
            if not (observed['force'] > 10).all():
                stopped = 'support_lost'
                break
            if args.phase_effort and not apply_phase_effort(proposal['joint'],
                    torch.ones((8, 4), device=device, dtype=torch.bool), 'prepare', step):
                stopped = 'prepare_effort_rejected'
                break
            action.zero_()
            action[:, planner_cols] = (proposal['joint'] - robot.data.default_joint_pos[:, asset_ids][:, planner_cols]) / M1_LEG_ACTION_SCALE_RAD
            if prepare_controller is not None:
                action,eligible=prepare_controller.position_action(robot.data.default_joint_pos[:,asset_ids])
                if not eligible.all():
                    stopped='prepare_action_rejected'
                    break
            if args.phase_wheel_hold:
                hold_speed=write_phase_wheels('prepare',step,anchor,observed['wheel_pos_w'])
            elif args.prepare_wheel_hold_only:
                if (robot.data.joint_effort_target[:,wheel_joint_ids]!=0).any():
                    raise RuntimeError('wheel holding effort model requires zero feedforward')
                hold_speed=anchor_hold_speed(anchor,observed['wheel_pos_w'],
                    extract_yaw_batch(robot.data.root_quat_w),hold_speed,env.step_dt)
                predicted=hold_effort(hold_speed,robot.data.joint_vel[:,wheel_joint_ids],
                    robot.data.joint_damping[:,wheel_joint_ids],
                    robot.data.joint_effort_limits[:,wheel_joint_ids],M1_WHEEL_ACTION_SCALE_RAD_S)
                action[:,wheel_cols]=hold_speed
                print('M1_PREPARE_WHEEL_HOLD '+json.dumps(dict(step=step,
                    speed=hold_speed.tolist(),predicted_effort=predicted.tolist(),
                    error=(anchor-observed['wheel_pos_w']).tolist())),flush=True)
            _, _, terminated, truncated, _ = env.step(action)
            transfer_velocity=proposal['velocity'] if args.anticipatory_prepare else (proposal['root'][:,:2]-previous_root[:,:2])/env.step_dt
            previous_root, previous_joint = proposal['root'], proposal['joint']
            if (terminated | truncated).any():
                stopped = 'episode_reset'
                break
        if prepare_controller is not None and stopped is None:
            # The last loop sample precedes its physics step. Observe again
            # after that step; reaching the budget is not successful PREPARE.
            final_prepare_observation=observe_support(robot,sensor,selected)
            final_non_support=sensor.data.net_forces_w[:,nonsupport_ids].norm(dim=-1).amax(-1)
            final_clock=torch.full_like(zero,args.num_steps)
            prepare_controller.update(observed=final_prepare_observation,
                live_root=robot.data.root_pos_w,collision=final_non_support>10.,
                step=final_clock,dt=env.step_dt,advance_reference=False)
            prepare_outcome=prepare_controller.finish(step=final_clock)
            stopped=('batched_prepare_complete' if prepare_outcome['ready'].all()
                     else 'batched_prepare_incomplete')
            print('M1_BATCHED_PREPARE_FINAL '+json.dumps({
                key:value.tolist() for key,value in prepare_outcome.items()}),flush=True)
        if args.pd_unload_steps and stopped=='batched_prepare_complete':
            from ame_baseline.m1_pd_unload import M1PdUnloadController,production_pd_valid,tracking_diagnostics
            pd_unload=M1PdUnloadController(prepare_controller,world_height=args.pd_unload_world_height)
            unload_entry=observe_support(robot,sensor,selected)['wheel_pos_w'].clone()
            def read_pd_unload():
                obs=observe_support(robot,sensor,selected)
                non_support=sensor.data.net_forces_w[:,nonsupport_ids].norm(dim=-1).amax(-1)
                drive_ok=production_pd_valid(
                    robot.root_physx_view.get_dof_stiffnesses().to(device)[:,asset_ids],
                    robot.root_physx_view.get_dof_dampings().to(device)[:,asset_ids],
                    robot.data.joint_effort_target[:,asset_ids])
                return obs,non_support,drive_ok
            stopped=None
            for ustep in range(args.pd_unload_steps+1):
                obs,non_support,drive_ok=read_pd_unload()
                roll,pitch=extract_roll_pitch_batch(robot.data.root_quat_w)
                live_rpy=torch.stack((roll,pitch,extract_yaw_batch(robot.data.root_quat_w)),-1)
                tracking=tracking_diagnostics(reference_root=pd_unload.root,reference_rpy=pd_unload.rpy,
                    live_root=robot.data.root_pos_w,live_rpy=live_rpy,command=pd_unload.joint,
                    actual_joint=robot.data.joint_pos[:,planner_ids],wheel=obs['wheel_pos_w'])
                result=pd_unload.update(observed=obs,step=torch.full_like(zero,ustep),
                    collision=non_support>10.,actuator_ok=drive_ok,dt=env.step_dt,
                    live_root=robot.data.root_pos_w,live_rpy=live_rpy,
                    advance_reference=False if ustep==args.pd_unload_steps else True)
                pd_unload_samples.append(dict(step=ustep,force=obs['force'].tolist(),
                    tilt=obs['tilt'].tolist(),tilt_rate=obs['tilt_rate'].tolist(),
                    margin=obs['margin'].tolist(),non_support=non_support.tolist(),
                    drive_ok=drive_ok.tolist(),height=result['height'].tolist(),
                    tracking={k:v.tolist() for k,v in tracking.items()},
                    root_measured=robot.data.root_pos_w.tolist(),
                    joint_measured=robot.data.joint_pos[:,planner_ids].tolist(),
                    joint_position_target=robot.data.joint_pos_target[:,planner_ids].tolist(),
                    projected_joint_force=robot.root_physx_view.get_dof_projected_joint_forces().tolist(),
                    measured_rise=(obs['wheel_pos_w']-unload_entry)[:,:,2].tolist(),
                    ready=result['ready'].tolist(),reason=result['reason'].tolist(),
                    failed=result['failed'].tolist(),streak=pd_unload.count.tolist()))
                if ustep%8==0 or result['failed'].any() or result['ready'].all():
                    print('M1_PD_UNLOAD_STEP '+json.dumps(pd_unload_samples[-1]),flush=True)
                if result['failed'].any() or result['ready'].all() or ustep==args.pd_unload_steps:
                    break
                action,eligible=pd_unload.position_action(robot.data.default_joint_pos[:,asset_ids])
                if not eligible.all():
                    stopped='pd_unload_action_rejected'
                    break
                _,_,terminated,truncated,_=env.step(action)
                if (terminated|truncated).any():
                    stopped='pd_unload_episode_reset'
                    break
            if stopped is None:
                pd_unload_outcome=pd_unload.finish(step=torch.full_like(zero,ustep))
                stopped=('pd_unload_complete' if pd_unload_outcome['ready'].all()
                         else 'pd_unload_incomplete')
                print('M1_PD_UNLOAD_FINAL '+json.dumps({
                    key:value.tolist() for key,value in pd_unload_outcome.items()}),flush=True)
        if args.prepare_wheel_hold_only and stopped is None:
            # End this diagnostic before any unverified phase handoff, no further physics steps.
            stopped='prepare_hold_only_complete'
        if args.dynamics_audit and stopped is None:
            # Fresh post-PREPARE evidence, never reuse the warmup Jacobian.
            post_jac = point_linear_jacobian(
                view.get_jacobians().clone(), robot.data.body_com_pos_w,
                robot.data.body_pos_w)[:, wheel_ids]
            post_gravity = view.get_gravity_compensation_forces().clone()
            post_mask = torch.arange(4, device=device)[None] != selected[:, None]
            post_allocations = {}
            for minimum in (10., 30.):
                result = vertical_support_solution(post_jac, post_gravity,
                                                   post_mask, robot.data.joint_effort_limits,
                                                   min_force=minimum)
                post_allocations[str(minimum)] = {k: v.tolist() for k, v in result.items()}
            print('M1_POST_PREPARE_ALLOCATION ' + json.dumps(dict(
                selected_leg=selected.tolist(), joint_names=robot.joint_names,
                allocations=post_allocations,
                observed_margin=observe_support(robot, sensor, selected)['margin'].tolist(),
                scope='read_only_static_not_lift_acceptance')), flush=True)
        if args.lift_steps and stopped is None:
            observed = observe_support(robot, sensor, selected)
            non_support = sensor.data.net_forces_w[:, nonsupport_ids].norm(dim=-1).amax(-1)
            ready = gate.update(
                episode=zero, obstacle=zero, leg=selected,
                step=torch.full_like(zero, args.num_steps), force=observed['force'],
                tilt=observed['tilt'], tilt_rate=observed['tilt_rate'], margin=observed['margin'],
                ik_valid=observed['valid'] & reference_ready, collision=non_support > 10.)
            if not ready.all():
                stopped = 'lift_entry_not_ready'
        unload_samples = []
        unload_height_state = torch.zeros(8, device=device)
        previous_nominal_joint = previous_joint.clone()
        selected_world_frame = None
        height_active=torch.zeros(8,device=device,dtype=torch.bool)
        if args.unload_steps and stopped is None:
            from ame_baseline.m1_unload_gate import unload_ready
            unload_count = torch.zeros(8, dtype=torch.long, device=device)
            mask = torch.arange(4, device=device)[None] != selected[:, None]
            for unload_step in range(args.unload_steps):
                obs = observe_support(robot, sensor, selected)
                non_support = sensor.data.net_forces_w[:, nonsupport_ids].norm(dim=-1).amax(-1)
                safe = (((obs['force'] > 10.) | ~mask).all(-1)
                        & (obs['tilt'].abs() <= .15).all(-1)
                        & (obs['tilt_rate'].abs() <= .20).all(-1) & (non_support <= 10.))
                if not safe.all():
                    stopped = 'unload_contact_pose_rejected'
                    break
                unload_joint = previous_joint
                unload_root = previous_root
                proposed_height = unload_height_state
                world_scale = torch.zeros(8, device=device)
                world_full = None
                effort_settled_before = (torch.tensor(phase_effort_samples[-1]['effort_error'], device=device) <= 1.) if phase_effort_samples and phase_effort_samples[-1]['phase'] == 'unload' else torch.zeros(8, device=device, dtype=torch.bool)
                load_ready_before = torch.ones(8, device=device, dtype=torch.bool)
                if args.unload_feedback:
                    from ame_baseline.m1_unload_reference import unload_height
                    from extension.parallelism.m1_kinematics import m1_ik, m1_joint_limit_mask
                    height_proposal = unload_height(unload_height_state,
                        obs['force'][torch.arange(8, device=device), selected], env.step_dt,
                        target_force=args.unload_target_force,
                        min_contact_speed=args.unload_min_speed,
                        effort_settled=effort_settled_before)
                    proposed_height = height_proposal['height']
                    if args.unload_com:
                        held = anchor.clone()
                        held[torch.arange(8, device=device), selected, 2] += unload_height_state
                        if args.anticipatory_prepare and not args.unload_support_feedback:
                            transfer=fixed_reference_step(entry=entry_root,rpy=entry_rpy,anchors=held,
                                previous=previous_root,velocity=transfer_velocity,previous_joint=previous_nominal_joint,
                                goal=anticipatory_goal,dt=env.step_dt)
                            transfer_velocity=transfer['velocity']
                        else:
                            transfer = transfer_target(entry_root=entry_root, entry_rpy=entry_rpy,
                                anchor_w=held, support_w=obs['wheel_pos_w'],
                                live_root=robot.data.root_pos_w, live_com=obs['com_w'],
                                selected_leg=selected, previous_root=previous_root,
                                previous_joint=previous_nominal_joint if args.unload_world_pose else previous_joint, dt=env.step_dt,
                                root_speed=args.transfer_speed, max_root_shift=args.max_root_shift,
                                total_weight=total_weight, support_floor=prepare_reserve)
                        if not transfer['valid'].all():
                            print('M1_UNLOAD_COM_REJECTION '+json.dumps(dict(step=unload_step,
                                reason=transfer['reason'].tolist(),
                                desired_shift=(transfer['desired_root']-entry_root).norm(dim=-1).tolist(),
                                previous_shift=(previous_root-entry_root).norm(dim=-1).tolist())),flush=True)
                            stopped = 'unload_com_rejected'
                            break
                        unload_root = transfer['root']
                        if args.unload_com_ramp and (not args.anticipatory_prepare or args.unload_support_feedback):
                            from ame_baseline.m1_com_trajectory import root_step
                            ramp=root_step(entry_root,previous_root,transfer_velocity,
                                transfer['desired_root'] if args.unload_support_feedback else unload_root,dt=env.step_dt)
                            if not ramp['valid'].all():
                                stopped='unload_com_ramp_rejected'
                                break
                            unload_root=ramp['root']
                            transfer_velocity=ramp['velocity']
                        load_ready_before = transfer['post_lift_load_ready']
                        proposed_height = torch.where(transfer['post_lift_load_ready'],
                            proposed_height, unload_height_state)
                    target = anchor.clone()
                    target[torch.arange(8, device=device), selected, 2] += proposed_height
                    q, reachable = m1_ik(unload_root, entry_rpy, target)
                    unload_joint = q.reshape(8, 12)
                    nominal_unload_joint = unload_joint.clone()
                    if args.unload_world_pose:
                        from ame_baseline.m1_selected_world import selected_world_target
                        roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
                        live_rpy = torch.stack((roll, pitch, extract_yaw_batch(robot.data.root_quat_w)), dim=-1)
                        if args.unload_height_settled:
                            height_active |= effort_settled_before & load_ready_before
                        world = selected_world_target(root=unload_root, rpy=entry_rpy,
                            live_root=robot.data.root_pos_w, live_rpy=live_rpy, target=target,
                            nominal=unload_joint, previous=previous_joint, selected=selected, dt=env.step_dt,
                            previous_frame=selected_world_frame, vertical_only=args.unload_vertical_only,
                            height_only=args.unload_height_only,
                            height_mask=height_active if args.unload_height_settled else None)
                        if not world['valid'].all():
                            print('M1_WORLD_REJECTION ' + json.dumps(dict(step=unload_step,
                                valid=world['valid'].tolist(),
                                full={key: value.tolist() for key,value in world['full'].items()})), flush=True)
                            stopped = 'unload_world_pose_rejected'
                            break
                        unload_joint, world_scale = world['joint'], world['scale']
                        selected_world_frame = world['frame']
                        world_full = {key: value.tolist() for key, value in world['full'].items()}
                    if not (height_proposal['valid'] & reachable.all(-1)
                            & m1_joint_limit_mask(unload_joint)
                            & ((unload_joint-previous_joint).abs() <= .5*env.step_dt+1e-7).all(-1)).all():
                        stopped = 'unload_reference_rejected'
                        break
                if not apply_phase_effort(unload_joint, mask, 'unload', unload_step):
                    stopped = 'unload_effort_rejected'
                    break
                evidence = phase_effort_samples[-1]
                ready_now = unload_ready(force=obs['force'], selected=selected,
                    tilt=obs['tilt'], rate=obs['tilt_rate'],
                    effort_error=torch.tensor(evidence['effort_error'], device=device),
                    allocation_valid=torch.tensor(evidence['allocation_valid'], device=device))
                if args.unload_support_feedback:
                    ready_now &= load_ready_before & (transfer_velocity.norm(dim=-1)<=.001)
                unload_count = torch.where(ready_now, unload_count+1, 0)
                unload_samples.append(dict(step=unload_step, force=obs['force'].tolist(),
                    transfer_velocity=transfer_velocity.tolist() if args.unload_com_ramp else None,
                    height_active=height_active.tolist() if args.unload_height_settled else None,
                    world_pose_scale=world_scale.tolist(),
                    world_full_candidate=world_full,
                    wheel_delta_w=(obs['wheel_pos_w']-anchor).tolist(),
                    root_measured=robot.data.root_pos_w.tolist(),
                    joint_tracking_error=(previous_joint-robot.data.joint_pos[:, planner_ids]).tolist(),
                    effort_settled_before=effort_settled_before.tolist(),
                    load_ready_before=load_ready_before.tolist(),
                    root_command=unload_root.tolist(), margin=obs['margin'].tolist(),
                    height=unload_height_state.tolist(), proposed_height=proposed_height.tolist(),
                    ready=ready_now.tolist(), streak=unload_count.tolist(),
                    effort_error=evidence['effort_error']))
                if (unload_count >= 5).all():
                    break
                # Only opt-in measured feedback may shorten the selected leg;
                # other wheel anchors and prepared root reference stay fixed.
                action.zero_()
                action[:, planner_cols] = (unload_joint-robot.data.default_joint_pos[:, planner_ids]) / M1_LEG_ACTION_SCALE_RAD
                if args.phase_wheel_hold:
                    hold_speed=write_phase_wheels('unload',unload_step,anchor,obs['wheel_pos_w'])
                if args.unload_substep_audit:
                    from ame_baseline.m1_substeps import observe_substeps
                    def read_unload_substep():
                        native=sensor.contact_physx_view.get_net_contact_forces(dt=cfg.sim.dt).reshape(8,-1,3)
                        body_mass=robot.root_physx_view.get_masses().to(robot.data.body_com_lin_vel_w.device)
                        com_velocity=(body_mass[:,:,None]*robot.data.body_com_lin_vel_w).sum(1)/body_mass.sum(1)[:,None]
                        record=dict(force=native[:,wheel_sensor_ids,2].tolist(),
                            wheel_normal_force_xyz=native[:,wheel_sensor_ids].tolist(),
                            com_velocity=com_velocity.tolist(),
                            root_angular_velocity=robot.data.root_ang_vel_w.tolist(),
                            root_velocity=robot.data.root_lin_vel_w.tolist())
                        if unload_friction_views:
                            from ame_baseline.m1_contact_snapshot import friction_wrenches
                            com=(body_mass[:,:,None]*robot.data.body_com_pos_w).sum(1)/body_mass.sum(1)[:,None]
                            record['friction_about_com']=[]
                            for (row,name),view in unload_friction_views.items():
                                ff,fp,fc,fs=view.get_friction_data(dt=cfg.sim.dt)
                                pairs=friction_wrenches(ff.tolist(),fp.tolist(),fc.flatten().tolist(),
                                    fs.flatten().tolist(),com[row].tolist())
                                record['friction_about_com'].append(dict(row=row,wheel=name,pairs=pairs))
                        return record
                    step_result,records=observe_substeps(env.scene,lambda:env.step(action),read_unload_substep)
                    print('M1_UNLOAD_SUBSTEPS '+json.dumps(dict(step=unload_step,
                        wheel_names=wheel_names,selected=selected.tolist(),physics_dt=cfg.sim.dt,
                        records=records)),flush=True)
                    _,_,terminated,truncated,_=step_result
                else:
                    _, _, terminated, truncated, _ = env.step(action)
                previous_joint, unload_height_state = unload_joint, proposed_height
                if args.unload_feedback:
                    previous_nominal_joint = nominal_unload_joint
                previous_root = unload_root
                if (terminated | truncated).any():
                    stopped = 'unload_episode_reset'
                    break
            if stopped is None and not (unload_count >= 5).all():
                # The last budgeted action has executed; consume its fresh result
                # before declaring timeout. Do not execute an additional action.
                obs=observe_support(robot,sensor,selected)
                non_support=sensor.data.net_forces_w[:,nonsupport_ids].norm(dim=-1).amax(-1)
                final_jac=point_linear_jacobian(robot.root_physx_view.get_jacobians(),
                    robot.data.body_com_pos_w,robot.data.body_pos_w)[:,wheel_ids]
                final_solution=vertical_support_solution(final_jac,
                    robot.root_physx_view.get_gravity_compensation_forces(),mask,
                    robot.data.joint_effort_limits,min_force=30.)
                final_error=(torch.where(phase_leg_mask[None],final_solution['effort'],0.)-phase_effort).abs().amax(-1)
                ready_now=unload_ready(force=obs['force'],selected=selected,
                    tilt=obs['tilt'],rate=obs['tilt_rate'],effort_error=final_error,
                    allocation_valid=final_solution['valid']) & obs['valid'] & (non_support<=10.)
                if args.unload_support_feedback:
                    held=anchor.clone();held[torch.arange(8,device=device),selected,2]+=unload_height_state
                    final_transfer=transfer_target(entry_root=entry_root,entry_rpy=entry_rpy,
                        anchor_w=held,support_w=obs['wheel_pos_w'],live_root=robot.data.root_pos_w,
                        live_com=obs['com_w'],selected_leg=selected,previous_root=previous_root,
                        previous_joint=previous_nominal_joint,dt=env.step_dt,root_speed=args.transfer_speed,
                        max_root_shift=args.max_root_shift,total_weight=total_weight,support_floor=prepare_reserve)
                    ready_now &= final_transfer['valid'] & final_transfer['post_lift_load_ready']
                    ready_now &= transfer_velocity.norm(dim=-1)<=.001
                unload_count=torch.where(ready_now,unload_count+1,0)
                print('M1_UNLOAD_FINAL_CHECK '+json.dumps(dict(executed_actions=args.unload_steps,
                    force=obs['force'].tolist(),ready=ready_now.tolist(),streak=unload_count.tolist(),
                    effort_error=final_error.tolist())),flush=True)
                if not (unload_count>=5).all():
                    stopped = 'unload_timeout'
        height = unload_height_state.clone()
        rows = torch.arange(8, device=device)
        lift_reference_root = robot.data.root_pos_w.clone()
        roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
        lift_reference_rpy = torch.stack((roll, pitch, extract_yaw_batch(robot.data.root_quat_w)), -1)
        lift_command_root, lift_command_rpy = previous_root.clone(), entry_rpy.clone()
        landing_gate = PrepareGate(8,device)
        landing_complete = False
        touchdown_seen=torch.zeros(8,device=device,dtype=torch.bool)
        roll_origin = None
        roll_initial_speed = None
        roll_progress = torch.zeros(8,device=device)
        roll_com_offset = torch.zeros_like(previous_root)
        com_velocity = torch.zeros((8,2),device=device)
        com_brake_target = None
        main_budget=args.lift_steps+args.roll_steps+args.land_steps
        from ame_baseline.m1_lift_handoff import LiftHandoffGate
        import math
        handoff_gate=LiftHandoffGate(8,device)
        previous_measured_height=torch.full_like(height,float('nan'))
        roll_start=None if args.lift_handoff else args.lift_steps
        minimum_land_steps=math.ceil((args.lift_height+args.land_search_depth)/args.vertical_speed/env.step_dt)
        active_wheel_damping=5.
        for lift_step in range(main_budget+args.settle_steps if stopped is None else 0):
            observed = observe_support(robot, sensor, selected)
            if args.lift_handoff and roll_start is None:
                measured_height=observed['wheel_pos_w'][rows,selected,2]-anchor[rows,selected,2]
                ready=handoff_gate.update(lift_step,height=measured_height,previous_height=previous_measured_height,
                    force=observed['force'],selected=selected,tilt=observed['tilt'],tilt_rate=observed['tilt_rate'],
                    margin=observed['margin'],valid=observed['valid'],
                    collision=sensor.data.net_forces_w[:,nonsupport_ids].norm(dim=-1).amax(-1)>10.,
                    target=args.lift_height,dt=env.step_dt)
                previous_measured_height=measured_height.clone()
                print('M1_LIFT_HANDOFF '+json.dumps(dict(step=lift_step,ready=ready.tolist(),streak=handoff_gate.count.tolist())),flush=True)
                if ready.all():roll_start=lift_step
                elif lift_step>=main_budget-args.roll_steps-minimum_land_steps:
                    stopped='lift_handoff_timeout'
                    break
            is_landing = roll_start is not None and lift_step >= roll_start+args.roll_steps
            is_rolling = roll_start is not None and roll_start<=lift_step<roll_start+args.roll_steps
            roll_age=lift_step-roll_start if roll_start is not None else -1
            is_settling = lift_step >= main_budget
            control_phase = 'settle' if is_settling else ('land' if is_landing else ('roll' if is_rolling else 'lift'))
            from ame_baseline.m1_rolling_speed import rolling_damping
            drive_damping=rolling_damping(control_phase,args.roll_wheel_damping)
            if drive_damping != active_wheel_damping:
                robot.write_joint_damping_to_sim(drive_damping,joint_ids=wheel_joint_ids)
                robot.actuators['wheels'].damping.fill_(drive_damping)
                active_wheel_damping=drive_damping
                print('M1_ROLL_DRIVE '+json.dumps(dict(step=lift_step,phase=control_phase,
                    damping=drive_damping,backend=robot.root_physx_view.get_dof_dampings()[:,wheel_joint_ids].tolist())),flush=True)
            commanded_roll_speed=args.roll_speed if is_rolling else 0.
            if is_rolling and args.roll_ramp:
                from ame_baseline.m1_rolling_speed import rolling_speed
                if roll_initial_speed is None:
                    roll_initial_speed=max(0.,float(hold_speed.max())) if args.roll_continuous_ramp else 0.
                commanded_roll_speed=rolling_speed(roll_age,args.roll_steps,
                    env.step_dt,args.roll_speed,initial=roll_initial_speed)
            if is_landing and not is_settling:
                touchdown_seen |= observed['force'][rows,selected]>10.
            moving_root,moving_anchor=previous_root,anchor
            if args.roll_steps and roll_age>=0:
                from ame_baseline.m1_rolling_reference import rolling_shift
                roll_position=robot.data.root_pos_w
                if args.roll_load_feedback:
                    from ame_baseline.m1_moving_load import support_center
                    roll_position=support_center(observed['wheel_pos_w'],selected)
                if roll_origin is None:roll_origin=roll_position.clone()
                transport=rolling_shift(roll_origin,roll_position,entry_rpy[:,2],roll_progress,env.step_dt)
                if not transport['valid'].all():
                    stopped='rolling_reference_rejected'
                    break
                moving_root=previous_root+transport['shift']+roll_com_offset
                moving_anchor=anchor+transport['shift'][:,None]
                selected_world_frame['root']=selected_world_frame['root']+transport['delta']
                roll_progress=transport['progress']
            if args.roll_load_feedback and is_rolling:
                from ame_baseline.m1_moving_load import moving_load_target
                load_proposal=moving_load_target(entry_root=entry_root,prepared_root=previous_root,
                    rpy=entry_rpy,anchor=anchor,shift=transport['shift'],offset=roll_com_offset,
                    height=height,support=observed['wheel_pos_w'],live_root=robot.data.root_pos_w,
                    com=observed['com_w'],selected=selected,force=observed['force'],dt=env.step_dt,
                    root_speed=args.transfer_speed,max_root_shift=args.max_root_shift)
                print('M1_MOVING_LOAD '+json.dumps(dict(step=lift_step,
                    valid=load_proposal['valid'].tolist(),reason=load_proposal['reason'].tolist(),
                    offset=load_proposal['offset'].tolist(),
                    force_target=load_proposal['support_force_target'].tolist())),flush=True)
                if not load_proposal['valid'].all():
                    stopped='rolling_load_proposal_rejected'
                    break
                moving_root=load_proposal['root']
            if args.roll_com_trajectory and roll_age>=0:
                from ame_baseline.m1_com_trajectory import com_step
                if not is_rolling and com_brake_target is None:
                    com_brake_target=roll_com_offset[:,:2].clone()
                com_target=load_proposal['offset'][:,:2] if is_rolling else com_brake_target
                com_proposal=com_step(roll_com_offset[:,:2],com_velocity,com_target,dt=env.step_dt)
                candidate_offset=torch.cat((com_proposal['position'],torch.zeros((8,1),device=device)),dim=-1)
                moving_root=previous_root+transport['shift']+candidate_offset
                full_shift=(moving_root-entry_root-transport['shift']).norm(dim=-1)
                print('M1_COM_TRAJECTORY '+json.dumps(dict(step=lift_step,
                    offset=candidate_offset.tolist(),velocity=com_proposal['velocity'].tolist(),
                    full_shift=full_shift.tolist(),valid=com_proposal['valid'].tolist())),flush=True)
                if not com_proposal['valid'].all() or (full_shift>args.max_root_shift).any():
                    stopped='com_trajectory_rejected'
                    break
            if is_settling:
                from ame_baseline.m1_settle import settle_allowed
                if not settle_allowed(observed['force'],lift_step-main_budget,args.settle_steps,
                                      selected=selected,touchdown_seen=touchdown_seen).all():
                    stopped = 'settle_contact_lost_or_missing'
                    break
            non_support = sensor.data.net_forces_w[:, nonsupport_ids].norm(dim=-1).amax(-1)
            roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
            live_rpy = torch.stack((roll, pitch, extract_yaw_batch(robot.data.root_quat_w)), -1)
            feedback = dict(reference_root=lift_reference_root, reference_rpy=lift_reference_rpy,
                            live_root=robot.data.root_pos_w, live_rpy=live_rpy,
                            previous_root=lift_command_root, previous_rpy=lift_command_rpy)
            support_mask = torch.arange(4, device=device)[None] != selected[:, None]
            touchdown = observed['force'][rows,selected] > 10.
            advance = (observed['margin'] >= .02) & ((observed['force'] >= 30.) | ~support_mask).all(-1)
            proposal = lift_target(
                root=lift_command_root if args.lift_support_transfer else moving_root,
                rpy=entry_rpy, anchor_w=moving_anchor,
                selected_leg=selected, previous_joint=previous_joint, height=height,
                force=observed['force'], tilt=observed['tilt'],
                tilt_rate=observed['tilt_rate'], margin=observed['margin'], dt=env.step_dt,
                pose_feedback=feedback if args.lift_pose_feedback else None,
                attitude_feedback=dict(live_rpy=live_rpy,previous_rpy=lift_command_rpy)
                    if args.lift_attitude_feedback else None,
                advance_mask=torch.zeros_like(touchdown) if is_settling else (~touchdown if is_landing else advance),
                target_height=-args.land_search_depth if is_landing else args.lift_height,
                vertical_speed=args.vertical_speed,
                world_feedback=dict(live_root=robot.data.root_pos_w,live_rpy=live_rpy,
                    previous_frame=selected_world_frame,vertical_only=args.unload_vertical_only,
                    height_only=args.unload_height_only,
                    height_mask=height_active if args.unload_height_settled else None)
                    if args.unload_world_pose else None)
            if args.lift_support_transfer:
                held_anchor = anchor.clone()
                held_anchor[rows, selected, 2] += height
                transfer = transfer_target(
                    entry_root=entry_root, entry_rpy=entry_rpy, anchor_w=held_anchor,
                    support_w=observed['wheel_pos_w'], live_root=robot.data.root_pos_w,
                    live_com=observed['com_w'], selected_leg=selected,
                    previous_root=lift_command_root, previous_joint=previous_joint,
                    dt=env.step_dt, root_speed=args.transfer_speed, max_root_shift=args.max_root_shift,
                    wheel_force=observed['force'] if args.lift_force_feedback else None)
                hold = ~advance
                proposal['valid'] &= ~hold | transfer['valid']
                proposal['reason'] = torch.where(hold & ~transfer['valid'], 100 + transfer['reason'], proposal['reason'])
                proposal['joint'] = torch.where(hold[:, None], transfer['joint'], proposal['joint'])
                proposal['root'] = torch.where(hold[:, None], transfer['root'], proposal['root'])
            if is_landing:
                settled = torch.tensor(phase_effort_samples[-1]['effort_error'],device=device)<=1.
                settled &= phase_effort_samples[-1]['phase'] in ('land','settle')
                landed=landing_gate.update(episode=zero,obstacle=zero,leg=selected,
                    step=torch.full_like(zero,lift_step),force=observed['force'],
                    tilt=observed['tilt'],tilt_rate=observed['tilt_rate'],margin=observed['margin'],
                    ik_valid=observed['valid'] & proposal['valid'] & settled,collision=non_support>10.)
                landing_complete=bool(landed.all())
                if args.roll_com_trajectory:
                    landing_complete &= bool((com_velocity.norm(dim=-1)<=1e-4).all())
            if is_rolling and roll_age in (0,5,10,12,14):
                for name,view in roll_contact_audits.items():
                    nf,cp,cn,sep,nc,ns=view.get_contact_data(dt=cfg.sim.dt)
                    ff,fp,fc,fs=view.get_friction_data(dt=cfg.sim.dt)
                    def patch_rows(counts,starts,arrays):
                        return [[v[start:start+count].tolist() for v in arrays]
                                for count,start in zip(counts.flatten().tolist(),starts.flatten().tolist())]
                    print('M1_ROLL_CONTACT_PATCH '+json.dumps(dict(step=lift_step,body=name,
                        center=robot.data.body_pos_w[3,robot.body_names.index(name)].tolist(),
                        normal=patch_rows(nc,ns,(nf,cp,cn,sep)),
                        friction=patch_rows(fc,fs,(ff,fp)))),flush=True)
            lift_samples.append(dict(
                phase=control_phase,landing_streak=landing_gate.count.tolist(),
                touchdown_seen=touchdown_seen.tolist(),
                roll_progress=roll_progress.tolist(),
                requested_roll_speed=commanded_roll_speed,
                wheel_joint_position=robot.data.joint_pos[:,wheel_joint_ids].tolist(),
                wheel_velocity_target=robot.data.joint_vel_target[:,wheel_joint_ids].tolist(),
                wheel_velocity_actual=robot.data.joint_vel[:,wheel_joint_ids].tolist(),
                root_velocity=robot.data.root_lin_vel_w.tolist(),
                wheel_axis_world=robot.root_physx_view.get_jacobians()[:,wheel_ids,3:6][:,:,:,torch.tensor(wheel_joint_ids,device=device)+6].diagonal(dim1=1,dim2=3).permute(0,2,1).tolist() if is_rolling else None,
                wheel_damping=robot.data.joint_damping[:,wheel_joint_ids].tolist(),
                wheel_estimated_torque=robot.data.computed_torque[:,wheel_joint_ids].tolist(),
                wheel_clipped_torque=robot.data.applied_torque[:,wheel_joint_ids].tolist(),
                step=lift_step, pre_action=True, margin=observed['margin'].tolist(),
                advance=advance.tolist(),
                force=observed['force'].tolist(), tilt=observed['tilt'].tolist(),
                tilt_rate=observed['tilt_rate'].tolist(),
                measured_rise=(observed['wheel_pos_w'][rows, selected, 2] - anchor[rows, selected, 2]).tolist(),
                target_rise=proposal['height'].tolist(),
                root_w=robot.data.root_pos_w.tolist(), com_w=observed['com_w'].tolist(),
                root_quat_w=robot.data.root_quat_w.tolist(),
                body_names=list(robot.body_names),
                body_com_w=robot.data.body_com_pos_w.tolist(),
                previous_root_command=lift_command_root.tolist(),
                next_root_command=proposal['root'].tolist(),
                desired_transfer_root=transfer['desired_root'].tolist() if args.lift_support_transfer else None,
                support_force_target=transfer['support_force_target'].tolist() if args.lift_force_feedback else None,
                joint_actual=robot.data.joint_pos[:, planner_ids].tolist(),
                joint_target=proposal['joint'].tolist(),
                applied_position_target=robot.data.joint_pos_target[:, planner_ids].tolist(),
                joint_velocity=robot.data.joint_vel[:, planner_ids].tolist(),
                estimated_torque=robot.data.computed_torque[:, planner_ids].tolist(),
                estimated_clipped_torque=robot.data.applied_torque[:, planner_ids].tolist(),
                effort_limit=robot.data.joint_effort_limits[:, planner_ids].tolist(),
                wheel_pos_w=observed['wheel_pos_w'].tolist(),
                valid=proposal['valid'].tolist(), reason=proposal['reason'].tolist(),
                non_support_force=non_support.tolist()))
            if not observed['valid'].all() or not proposal['valid'].all() or (non_support > 10.).any():
                stopped = 'lift_guard_rejected'
                break
            if landing_complete:
                break
            if is_landing:
                persistent_contact=touchdown_seen & (observed['force'][rows,selected]>1.)
                support_mask = support_mask | persistent_contact[:,None]
            if args.phase_effort and not apply_phase_effort(proposal['joint'], support_mask, control_phase, lift_step):
                stopped = 'lift_effort_rejected'
                break
            action.zero_()
            action[:, planner_cols] = (proposal['joint'] - robot.data.default_joint_pos[:, asset_ids][:, planner_cols]) / M1_LEG_ACTION_SCALE_RAD
            if is_rolling:
                # Flat-only direction/stability probe. No obstacle acceptance.
                if not advance.all():
                    stopped='rolling_support_rejected'
                    break
                from ame_baseline.m1_rolling_speed import drive_columns
                for row,leg in enumerate(selected.tolist()):
                    columns=[wheel_cols[i] for i in drive_columns(leg,args.roll_lifted_only)]
                    action[row,columns]=commanded_roll_speed
                if args.roll_explicit_torque:
                    from ame_baseline.m1_rolling_speed import rolling_torque
                    wheel_effort=rolling_torque(roll_age,args.roll_steps,env.step_dt,args.roll_explicit_torque)
                    applied_effort=phase_effort.clone()
                    applied_effort[:,wheel_joint_ids]=wheel_effort
                    applied_effort[rows,torch.tensor(wheel_joint_ids,device=device)[selected]]=0.
                    wheel_pd=-robot.data.joint_damping[:,wheel_joint_ids]*robot.data.joint_vel[:,wheel_joint_ids]
                    total_wheel=wheel_pd+applied_effort[:,wheel_joint_ids]
                    if not torch.isfinite(total_wheel).all() or (total_wheel.abs()>robot.data.joint_effort_limits[:,wheel_joint_ids]).any():
                        stopped='wheel_effort_rejected'
                        break
                    # Zero velocity target retains baseline damping, not extra forward drive.
                    action[:,wheel_cols]=0.
                    robot.set_joint_effort_target(applied_effort)
            if args.phase_wheel_hold:
                hold_speed=write_phase_wheels(control_phase,lift_step,moving_anchor,
                    observed['wheel_pos_w'],commanded_roll_speed)
            if args.roll_substep_audit and is_rolling:
                from ame_baseline.m1_substeps import observe_substeps
                def read_wheel_substep():
                    from ame_baseline.m1_contact_snapshot import pair_records
                    backend=robot.root_physx_view
                    masses=backend.get_masses().to(robot.data.body_com_lin_vel_w.device)
                    com_velocity=(masses[...,None]*robot.data.body_com_lin_vel_w).sum(1)/masses.sum(1)[:,None]
                    normal=sensor.contact_physx_view.get_net_contact_forces(dt=cfg.sim.dt).reshape(8,-1,3)
                    contacts={}
                    for name,view in roll_transient_views.items():
                        nf,cp,cn,sep,nc,ns=view.get_contact_data(dt=cfg.sim.dt)
                        contacts[name]=pair_records(nf.flatten().tolist(),cp.tolist(),sep.flatten().tolist(),nc.flatten().tolist(),ns.flatten().tolist())
                    return dict(q=backend.get_dof_positions()[3,wheel_joint_ids].tolist(),
                        row7_contacts=contacts,
                        row7_computed_torque=robot.data.computed_torque[7].tolist(),
                        row7_q=robot.data.joint_pos[7].tolist(),row7_qd=robot.data.joint_vel[7].tolist(),
                        row7_position_target=robot.data.joint_pos_target[7].tolist(),
                        row7_velocity_target=robot.data.joint_vel_target[7].tolist(),
                        com_velocity=com_velocity.tolist(),
                        root_angular_velocity=robot.data.root_ang_vel_w.tolist(),
                        wheel_normal_force_xyz=normal[:,wheel_sensor_ids].tolist(),
                        qd=backend.get_dof_velocities()[3,wheel_joint_ids].tolist(),
                        cached_q=robot.data.joint_pos[3,wheel_joint_ids].tolist(),
                        cached_qd=robot.data.joint_vel[3,wheel_joint_ids].tolist())
                start_wheels=read_wheel_substep()
                step_result,substeps=observe_substeps(env.scene,lambda:env.step(action),read_wheel_substep)
                print('M1_WHEEL_SUBSTEPS '+json.dumps(dict(step=lift_step,dt=env.physics_dt,
                    start=start_wheels,samples=substeps)),flush=True)
                _,_,terminated,truncated,_=step_result
            else:
                _, _, terminated, truncated, _ = env.step(action)
            if args.roll_explicit_torque and is_rolling:
                print('M1_EXPLICIT_WHEEL '+json.dumps(dict(step=lift_step,target=applied_effort[:,wheel_joint_ids].tolist(),
                    native=robot.root_physx_view.get_dof_actuation_forces()[:,wheel_joint_ids].tolist())),flush=True)
            previous_joint, height = proposal['joint'], proposal['height']
            if args.roll_load_feedback and is_rolling:
                roll_com_offset=proposal['root']-previous_root-transport['shift']
            if args.roll_com_trajectory and roll_age>=0:
                roll_com_offset=proposal['root']-previous_root-transport['shift']
                com_velocity=com_proposal['velocity']
            if args.unload_world_pose:
                selected_world_frame = proposal['world_frame']
            lift_command_root, lift_command_rpy = proposal['root'], proposal['rpy']
            if (terminated | truncated).any():
                stopped = 'lift_episode_reset'
                break
        if args.land_steps and stopped is None and not landing_complete:
            stopped = 'settle_timeout' if args.settle_steps else 'landing_timeout'
        final_observation = observe_support(robot,sensor,selected)
        if args.phase_effort:
            backend = robot.root_physx_view
            print('M1_BACKEND_EFFORT ' + json.dumps(dict(
                stiffness_error=(backend.get_dof_stiffnesses().to(device)-robot.data.joint_stiffness).abs().amax(-1).tolist(),
                damping_error=(backend.get_dof_dampings().to(device)-robot.data.joint_damping).abs().amax(-1).tolist(),
                actuation=backend.get_dof_actuation_forces().tolist(),
                buffer_effort=robot.data.joint_effort_target.tolist(),
                projected_joint_force=backend.get_dof_projected_joint_forces().tolist(),
                pd_estimate=position_pd_effort(robot.data.joint_pos_target, robot.data.joint_pos,
                    robot.data.joint_vel_target, robot.data.joint_vel,
                    robot.data.joint_stiffness, robot.data.joint_damping).tolist(),
                joint_names=robot.joint_names)), flush=True)
            robot.set_joint_effort_target(torch.zeros_like(phase_effort))
            robot.write_data_to_sim()
            print('M1_PHASE_EFFORT ' + json.dumps(dict(samples=phase_effort_samples,
                cleared=bool((robot.data.joint_effort_target == 0).all()))), flush=True)
        print('M1_CONTACT_PREPARE ' + json.dumps(dict(
            scope=('prepare_pd_unload_only_no_crossing' if args.pd_unload_steps else
                ('prepare_and_vertical_lift_no_crossing' if args.lift_steps and not args.prepare_wheel_hold_only else 'prepare_only_no_lift_no_crossing')), num_envs=8,
            budget=args.num_steps, dt=env.step_dt, stopped=stopped,
            batched_prepare=args.batched_prepare,
            prepare_outcome=None if prepare_outcome is None else {k:v.tolist() for k,v in prepare_outcome.items()},
            pd_unload_outcome=None if pd_unload_outcome is None else {k:v.tolist() for k,v in pd_unload_outcome.items()},
            pd_unload_samples=pd_unload_samples,
            pd_unload_world_height=args.pd_unload_world_height,
            landing_complete=landing_complete,land_budget=args.land_steps,
            settle_budget=args.settle_steps,
            final_observation={key:value.tolist() for key,value in final_observation.items()},
            final_height_reference=height.tolist(),
            entry_fk_error_m=entry_fk_error.tolist(), selected_leg=selected.tolist(),
            entry_snapshot=entry_snapshot,
            terrain='flat_only', entry_anchor_w=anchor.tolist(),
            transfer_speed=args.transfer_speed,
            max_root_shift=args.max_root_shift,
            dynamics_audit=dynamics,
            prepare_load_floor=args.prepare_load_floor,
            unload_samples=unload_samples,
            lift_pose_feedback=args.lift_pose_feedback,
            lift_attitude_feedback=args.lift_attitude_feedback,
            unload_support_feedback=args.unload_support_feedback,
            lift_support_transfer=args.lift_support_transfer,
            lift_force_feedback=args.lift_force_feedback,
            lift_budget=args.lift_steps, roll_budget=args.roll_steps, roll_speed=args.roll_speed, roll_ramp=args.roll_ramp,
            lift_handoff=args.lift_handoff,roll_start=roll_start,
            roll_continuous_ramp=args.roll_continuous_ramp, roll_initial_speed=roll_initial_speed, vertical_speed=args.vertical_speed,
            lift_height=args.lift_height, lift_samples=lift_samples, samples=samples)), flush=True)
except BaseException:
    # SimulationApp.close may exit before Python prints a pending exception.
    import traceback
    traceback.print_exc()
    sys.stderr.flush()
    raise
finally:
    if env is not None:
        try:
            if args.standing_effort_steps or args.phase_effort:
                actor = env.scene['robot']
                actor.set_joint_effort_target(torch.zeros_like(actor.data.joint_pos))
                actor.write_data_to_sim()
        finally:
            env.close()
    launcher.app.close()
