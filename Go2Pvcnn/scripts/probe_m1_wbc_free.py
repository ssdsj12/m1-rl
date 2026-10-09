#!/usr/bin/env python3
"""Bounded suspended-M1 dynamics/actuation oracle; never trains."""
import argparse
import json
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(PACKAGE/'rsl_rl'))
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument('--dt', type=float, choices=(.001, .0005), default=.001)
parser.add_argument('--kinematic_bias', action='store_true')
parser.add_argument('--qp_control', action='store_true')
parser.add_argument('--pd_oracle', action='store_true')
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.qp_control and args.pd_oracle:
    parser.error('PD-source oracle and zero-PD QP execution are separate modes')
launcher = AppLauncher(args)
env = None
try:
    import torch
    from isaaclab.envs import ManagerBasedRLEnv
    from isaaclab.terrains import MeshPlaneTerrainCfg
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_wbc_dynamics import generalized_snapshot, free_dynamics_residual
    if args.qp_control:
        import numpy as np
        from ame_baseline.m1_wbc_qp import solve_wbc
        from ame_baseline.m1_wbc_limits import diagnostic_speed_limits, effort_step_bounds
        from ame_baseline.m1_wbc_joint_bounds import joint_step_bounds
        from ame_baseline.m1_ame_contract import M1_WHEEL_SPEED_LIMIT_RAD_S
        from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES
    if args.kinematic_bias:
        import numpy as np
        from ame_baseline.m1_wbc_kinematics import kinematic_bias
        from ame_baseline.m1_mass_predictor import load_usd_model
        from go2_pvcnn.assets.m1 import M1_USD_PATH
        from isaaclab.utils.math import matrix_from_quat
        kinematic_model = load_usd_model(M1_USD_PATH)

    cfg = M1AmeCrossLargeComplexEnvCfg()
    cfg.scene.num_envs = 8
    cfg.scene.env_spacing = 8.
    cfg.scene.terrain.terrain_generator.sub_terrains = {'flat': MeshPlaneTerrainCfg(proportion=1.)}
    cfg.scene.terrain.terrain_generator.num_rows = 1
    cfg.scene.terrain.terrain_generator.num_cols = 8
    cfg.scene.terrain.max_init_terrain_level = 0
    cfg.sim.device = str(args.device)
    cfg.sim.dt = args.dt
    cfg.decimation = 1
    cfg.seed = 2
    cfg.events.push_robot = None
    if not args.pd_oracle:
        for actuator in cfg.scene.robot.actuators.values():
            actuator.stiffness = 0.
            actuator.damping = 0.
    env = ManagerBasedRLEnv(cfg=cfg)
    env.reset()
    robot = env.scene['robot']
    view = robot.root_physx_view
    device = robot.data.joint_pos.device
    with torch.inference_mode():
        root = robot.data.default_root_state.clone()
        root[:, :3] += env.scene.env_origins
        root[:, 2] = 2.
        root[:, 7:] = 0.
        root[:, 10] = torch.linspace(-.1, .1, 8, device=device)
        joint_velocity = torch.linspace(-.15, .15, 8, device=device)[:, None].expand(-1, 16).clone()
        robot.write_root_state_to_sim(root)
        robot.write_joint_state_to_sim(robot.data.default_joint_pos.clone(), joint_velocity)
        zero = torch.zeros_like(robot.data.joint_pos)
        if args.pd_oracle:
            robot.set_joint_position_target(robot.data.default_joint_pos.clone())
            robot.set_joint_velocity_target(zero)
        robot.set_joint_effort_target(zero)
        robot.write_data_to_sim()
        env.sim.step(render=False)
        env.scene.update(args.dt)
        stiffness = view.get_dof_stiffnesses().clone()
        damping = view.get_dof_dampings().clone()
        if not args.pd_oracle and (stiffness.abs().max() != 0 or damping.abs().max() != 0):
            raise RuntimeError('native implicit drive remains enabled')
        if not torch.equal(view.get_dof_actuation_forces(),zero):
            raise RuntimeError('explicit zero initialization readback rejected')
        effort_history=[dict(command=np.zeros(16),step=0,episode=0,owner='explicit_total')
                        for _ in range(8)] if args.qp_control else None
        print('M1_FREE_CONFIG '+json.dumps(dict(dt=args.dt, stiffness=stiffness.tolist(),
            damping=damping.tolist(), friction=view.get_dof_friction_coefficients().tolist(),
            joint_names=robot.joint_names, scope='suspended_model_oracle_not_crossing')),flush=True)
        records = []
        for sign in (0., 1., -1.):
            step = len(records)
            snap = generalized_snapshot(view, robot.joint_names, robot.joint_names,
                torch.zeros(8, device=device, dtype=torch.long), step)
            before = torch.cat((robot.data.root_com_vel_w, robot.data.joint_vel), dim=1).clone()
            if args.kinematic_bias:
                body_before = robot.data.body_com_vel_w.clone()
                body_jac = view.get_jacobians().clone()
                rotation = matrix_from_quat(robot.data.body_link_quat_w).cpu().numpy()
                angular = body_before[:,:,3:].cpu().numpy()
                qd = robot.data.joint_vel.cpu().numpy()
                kinematic = [kinematic_bias(kinematic_model, robot.joint_names,
                    robot.body_names, rotation[row], angular[row], qd[row]) for row in range(8)]
                body_bias = torch.as_tensor(np.array([np.concatenate(
                    (b['com_linear'],b['angular']),axis=1) for b in kinematic]),
                    dtype=before.dtype,device=device)
            effort = torch.full_like(zero, sign*10*args.dt)
            if args.pd_oracle:
                effort=zero.clone()
            if args.qp_control:
                commands=[];qp_records=[]
                for row in range(8):
                    speed=diagnostic_speed_limits(names=robot.joint_names,
                        leg_names=M1_PLANNER_JOINT_NAMES,wheel_names=M1_WHEEL_JOINT_NAMES,
                        native_limits=np.minimum(view.get_dof_max_velocities()[row].cpu().numpy(),
                                                 robot.data.joint_vel_limits[row].cpu().numpy()),
                        leg_cap=.5,wheel_cap=M1_WHEEL_SPEED_LIMIT_RAD_S)
                    joint=joint_step_bounds(position=robot.data.joint_pos[row].cpu().numpy(),
                        velocity=robot.data.joint_vel[row].cpu().numpy(),
                        position_limits=view.get_dof_limits()[row].cpu().numpy(),
                        velocity_limits=speed,dt=args.dt)
                    limits=np.minimum(view.get_dof_max_forces()[row].cpu().numpy(),
                                      robot.data.joint_effort_limits[row].cpu().numpy())
                    torque=effort_step_bounds(previous=effort_history[row],limits=limits,
                        rate=np.full(16,20.),dt=args.dt,step=step+1,episode=0)
                    solution=solve_wbc(mass=snap['mass'][row].double().cpu().numpy(),
                        bias=snap['bias'][row].double().cpu().numpy(),
                        jac=np.empty((0,3,22)),frames=np.empty((0,3,3)),
                        mu=np.empty(0),normal_min=np.empty(0),normal_max=np.empty(0),
                        accel_lower=np.r_[-np.full(3,20.),-np.full(3,10.),joint['lower']],
                        accel_upper=np.r_[np.full(3,20.),np.full(3,10.),joint['upper']],
                        effort_lower=torque['lower'],effort_upper=torque['upper'],
                        contact_matrix=np.empty((0,22)),contact_rhs=np.empty(0),
                        tasks=((np.eye(22)[6:],np.full(16,sign*.1),np.ones(16)),))
                    qp_records.append(dict(row=row,valid=solution['valid'],reason=solution['reason'],
                        stages=solution['stages'],max_violation=solution.get('max_violation')))
                    if not solution['valid']:
                        print('M1_FREE_QP '+json.dumps(dict(step=step,rows=qp_records)),flush=True)
                        raise RuntimeError('free WBC rejected; no command applied')
                    if np.max(np.abs(solution['effort']-effort_history[row]['command']))>20*args.dt+1e-6:
                        raise RuntimeError('total command slew rejected before write')
                    commands.append(solution['effort'])
                effort=torch.as_tensor(np.array(commands),dtype=zero.dtype,device=device)
                print('M1_FREE_QP '+json.dumps(dict(step=step,rows=qp_records,
                    max_rate=[float(np.max(np.abs(commands[r]-effort_history[r]['command']))/args.dt)
                              for r in range(8)],scope='actual_free_execution_not_stance')),flush=True)
            if (effort.abs() > robot.data.joint_effort_limits).any():
                raise RuntimeError('authored effort limit exceeded')
            robot.set_joint_effort_target(effort)
            robot.write_data_to_sim()
            applied = view.get_dof_actuation_forces().clone()
            projected_before = view.get_dof_projected_joint_forces().clone() if args.pd_oracle else None
            cached_before = robot.data.applied_torque.clone() if args.pd_oracle else None
            if not torch.allclose(applied, effort, atol=1e-7, rtol=0):
                raise RuntimeError('applied force differs from sole-owner request')
            if args.qp_control:
                effort_history=[dict(command=applied[row].cpu().double().numpy().copy(),
                    step=step+1,episode=0,owner='explicit_total') for row in range(8)]
            env.sim.step(render=False)
            env.scene.update(args.dt)
            after = torch.cat((robot.data.root_com_vel_w, robot.data.joint_vel), dim=1).clone()
            if args.kinematic_bias:
                measured_body_acceleration = (robot.data.body_com_vel_w-body_before)/args.dt
                predicted_body_acceleration = torch.einsum('blij,bj->bli',body_jac,
                    (after-before)/args.dt)+body_bias
                kinematic_error = measured_body_acceleration-predicted_body_acceleration
                print('M1_KINEMATIC_SAMPLE '+json.dumps(dict(sign=sign,
                    linear_error=kinematic_error[:,:,:3].abs().amax(dim=(1,2)).tolist(),
                    angular_error=kinematic_error[:,:,3:].abs().amax(dim=(1,2)).tolist(),
                    bias_max=body_bias.abs().amax(dim=(1,2)).tolist(),
                    error_without_bias=(measured_body_acceleration-(predicted_body_acceleration-body_bias)).abs().amax(dim=(1,2)).tolist(),
                    tolerance=.02,body_names=robot.body_names)),flush=True)
                if not torch.isfinite(kinematic_error).all() or kinematic_error.abs().max() > .02:
                    raise RuntimeError('native kinematic acceleration oracle rejected')
            oracle_effort=effort
            if args.pd_oracle:
                oracle_effort=view.get_dof_projected_joint_forces().clone()
                projected_before_residual=free_dynamics_residual(
                    snap['mass'],snap['bias'],before,after,projected_before,args.dt)
                projected_after_residual=free_dynamics_residual(
                    snap['mass'],snap['bias'],before,after,oracle_effort,args.dt)
                projected_mid=(projected_before+oracle_effort)*.5
                projected_mid_residual=free_dynamics_residual(
                    snap['mass'],snap['bias'],before,after,projected_mid,args.dt)
                direct_residual=free_dynamics_residual(snap['mass'],snap['bias'],before,after,effort,args.dt)
                cached_residual=free_dynamics_residual(snap['mass'],snap['bias'],before,after,robot.data.applied_torque,args.dt)
                print('M1_PD_ORACLE '+json.dumps(dict(step=step,
                    projected_before=projected_before.tolist(),projected=oracle_effort.tolist(),
                    projected_mid=projected_mid.tolist(),direct=applied.tolist(),
                    cached_before=cached_before.tolist(),
                    cached_applied=robot.data.applied_torque.tolist(),
                    projected_before_residual_max=projected_before_residual.abs().amax(-1).tolist(),
                    projected_after_residual_max=projected_after_residual.abs().amax(-1).tolist(),
                    projected_mid_residual_max=projected_mid_residual.abs().amax(-1).tolist(),
                    direct_residual_max=direct_residual.abs().amax(-1).tolist(),
                    cached_residual_max=cached_residual.abs().amax(-1).tolist(),
                    scope='suspended_source_calibration_not_handoff')),flush=True)
            residual = free_dynamics_residual(snap['mass'], snap['bias'], before, after, oracle_effort, args.dt)
            contacts = env.scene['contact_forces'].data.net_forces_w.norm(dim=-1).amax(-1)
            record = dict(sign=sign, residual=residual.tolist(),
                max_residual=residual.abs().amax(-1).tolist(),
                max_base_force_n=residual[:,:3].abs().amax(-1).tolist(),
                max_base_moment_nm=residual[:,3:6].abs().amax(-1).tolist(),
                max_joint_torque_nm=residual[:,6:].abs().amax(-1).tolist(),
                contact=contacts.tolist(), coriolis=snap['coriolis'].tolist(),
                before=before.tolist(), after=after.tolist(), requested=effort.tolist(),
                applied=applied.tolist(), root_height=robot.data.root_pos_w[:, 2].tolist())
            records.append(record)
            print('M1_FREE_SAMPLE '+json.dumps(record),flush=True)
            if (contacts > 1e-6).any() or not torch.isfinite(after).all():
                raise RuntimeError('free-body oracle contacted terrain or became nonfinite')
            if (robot.data.joint_vel.abs() > robot.data.joint_vel_limits).any():
                raise RuntimeError('authored joint velocity limit exceeded')
        if args.pd_oracle:
            passed = all(max(r['max_base_force_n']) <= .05
                and max(r['max_base_moment_nm']) <= .02
                and max(r['max_joint_torque_nm']) <= .02 for r in records)
            tolerance=dict(base_force_n=.05,base_moment_nm=.02,joint_torque_nm=.02)
        else:
            passed = all(max(r['max_residual']) <= .02 for r in records)
            tolerance=.02
        print('M1_FREE_RESULT '+json.dumps(dict(passed=passed, samples=len(records),
            scope='dynamics_only_not_crossing', tolerance=tolerance,
            residual_units='base_linear_N_base_angular_Nm_joint_Nm')),flush=True)
        if not passed:
            raise RuntimeError('free-body dynamics residual rejected')
except BaseException:
    import traceback
    traceback.print_exc()
    raise
finally:
    if env is not None:
        env.close()
    launcher.app.close()
