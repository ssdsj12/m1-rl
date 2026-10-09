#!/usr/bin/env python3
"""Test a same-state, measured PD-to-explicit-WBC handoff on flat M1 support."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(PACKAGE / "rsl_rl"))

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--settle_steps", type=int, default=500)
parser.add_argument("--stable_frames", type=int, default=5)
parser.add_argument("--hold_steps", type=int, default=500)
parser.add_argument("--base_priority", action="store_true",
                    help="diagnostic only: prioritize base tracking over joint damping")
parser.add_argument("--snapshot_only", action="store_true",
                    help="capture fresh native QP inputs after PD settle; do not apply WBC")
parser.add_argument("--tangent_velocity_time_constant", type=float, default=0.02,
                    help="candidate finite horizon (s) for tangential contact-velocity residuals")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if (args.settle_steps < 1 or args.stable_frames < 5 or args.hold_steps < 1
        or not math.isfinite(args.tangent_velocity_time_constant)
        or args.tangent_velocity_time_constant <= 0):
    parser.error("settle_steps/hold_steps must be positive and stable_frames >= 5")

class _SnapshotComplete(Exception):
    """Normal diagnostic termination before explicit actuation."""


launcher = AppLauncher(args)
env = None
failure = None
try:
    import numpy as np
    import torch
    from isaaclab.envs import ManagerBasedRLEnv
    from isaaclab.terrains import MeshPlaneTerrainCfg

    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    from ame_baseline.m1_wbc_contacts import contact_geometry, deduplicate_contact_points
    from ame_baseline.m1_wbc_dynamics import generalized_snapshot
    from ame_baseline.m1_wbc_execution_adapter import (
        apply_wbc_command, capture_pd_handoff, pd_handoff_acceleration_contract,
        support_damping_target)
    from ame_baseline.m1_wbc_limits import effort_step_bounds, qp_effort_interior_bounds
    from ame_baseline.m1_wbc_contact_step import (
        contact_step_constraints, normal_only_contact_step_constraints,
        project_contact_rows_to_local_frames, rolling_contact_step_constraints,
        smooth_wheel_geometry_velocity)
    from ame_baseline.m1_wbc_kinematics import kinematic_bias
    from ame_baseline.m1_wbc_motion import contact_motion
    from ame_baseline.m1_wbc_contact_diagnostics import (
        contact_acceleration_consistency, contact_diagnostics,
        generalized_acceleration_consistency, jacobian_velocity_consistency,
        wheel_contact_force_consistency, wheel_contact_force_vector_consistency)
    from ame_baseline.m1_mass_predictor import load_usd_model
    from go2_pvcnn.assets.m1 import M1_USD_PATH
    from isaaclab.utils.math import matrix_from_quat
    from ame_baseline.m1_wbc_materials import conservative_friction
    from ame_baseline.m1_wbc_qp import solve_wbc
    from extension.convention import extract_roll_pitch_batch
    from extension.parallelism.rl_adapter import resolve_named_indices

    cfg = M1AmeCrossLargeComplexEnvCfg()
    cfg.scene.num_envs = 1
    cfg.scene.env_spacing = 8.0
    cfg.scene.terrain.terrain_generator.sub_terrains = {
        "flat": MeshPlaneTerrainCfg(proportion=1.0)
    }
    cfg.scene.terrain.terrain_generator.num_rows = 1
    cfg.scene.terrain.terrain_generator.num_cols = 1
    cfg.scene.terrain.max_init_terrain_level = 0
    cfg.sim.device = str(args.device)
    cfg.sim.dt = 0.001
    cfg.decimation = 1
    cfg.seed = 7
    cfg.events.push_robot = None
    cfg.events.reset_base.params["pose_range"] = {
        "x": (0.0, 0.0), "y": (0.0, 0.0), "yaw": (0.0, 0.0)
    }
    cfg.events.reset_robot_joints.params["velocity_range"] = (0.0, 0.0)
    cfg.commands.base_velocity.ranges.lin_vel_x = (0.0, 0.0)
    cfg.commands.base_velocity.ranges.lin_vel_y = (0.0, 0.0)
    cfg.commands.base_velocity.ranges.ang_vel_z = (0.0, 0.0)
    cfg.commands.base_velocity.rel_standing_envs = 1.0

    env = ManagerBasedRLEnv(cfg=cfg)
    env.reset()
    robot = env.scene["robot"]
    device = robot.data.joint_pos.device
    native = robot.root_physx_view
    wheel_names = tuple(M1_SUPPORT_BODY_NAMES)
    wheel_ids = tuple(resolve_named_indices(tuple(robot.body_names), wheel_names))
    if len(wheel_ids) != 4 or robot.is_fixed_base:
        raise RuntimeError("expected a floating-base M1 with four named support wheels")
    kinematic_model = load_usd_model(M1_USD_PATH)
    root_body_id = tuple(robot.body_names).index(kinematic_model["root"])

    contact_views = {
        name: env.scene["contact_forces"]._physics_sim_view.create_rigid_contact_view(
            f"/World/envs/env_0/Robot/{name}",
            filter_patterns=["/World/ground/terrain/mesh"],
            max_contact_data_count=128,
        )
        for name in wheel_names
    }
    material_views = {
        name: env.scene["contact_forces"]._physics_sim_view.create_rigid_body_view(
            native.link_paths[0][wheel_ids[index]])
        for index, name in enumerate(wheel_names)
    }
    # Use the live native wheel coefficients and the USD-bound terrain
    # material. A zero-friction approximation can make an otherwise sound
    # flat-stance handoff spuriously infeasible.
    from pxr import Usd, UsdPhysics, UsdShade, PhysxSchema
    import omni.usd
    stage = omni.usd.get_context().get_stage()

    def bound_material(prim):
        material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial(
            materialPurpose="physics")
        if not material:
            raise RuntimeError("missing bound physics material: " + str(prim.GetPath()))
        mode = PhysxSchema.PhysxMaterialAPI(material.GetPrim()).GetFrictionCombineModeAttr().Get()
        if mode is None and not material.GetPrim().HasAPI(PhysxSchema.PhysxMaterialAPI):
            definition = Usd.SchemaRegistry().FindAppliedAPIPrimDefinition("PhysxMaterialAPI")
            if not definition:
                raise RuntimeError("installed material schema fallback unavailable")
            mode = definition.GetAttributeFallbackValue("physxMaterial:frictionCombineMode")
        physics = UsdPhysics.MaterialAPI(material.GetPrim())
        return dict(mode=mode, coefficients=[
            physics.GetStaticFrictionAttr().Get(),
            physics.GetDynamicFrictionAttr().Get(),
            physics.GetRestitutionAttr().Get()])

    ground_material = bound_material(stage.GetPrimAtPath("/World/ground/terrain/mesh"))
    material_mu = []
    for wheel_id in wheel_ids:
        link_path = native.link_paths[0][wheel_id]
        authored = [bound_material(prim) for prim in Usd.PrimRange(
            stage.GetPrimAtPath(link_path), Usd.TraverseInstanceProxies())
            if prim.HasAPI(UsdPhysics.CollisionAPI)]
        if not authored:
            raise RuntimeError("wheel collision material binding not found: " + str(link_path))
        live_rows = material_views[wheel_names[len(material_mu)]].get_material_properties().tolist()
        if len(live_rows) != 1 or not live_rows[0]:
            raise RuntimeError("expected one nonempty native material row: " + wheel_names[len(material_mu)])
        live = live_rows[0]
        # Native order is shape-based and may differ from authored USD order;
        # conservatively evaluate every possible wheel/terrain pair.
        pairs = [row for row in live for _ in authored]
        modes = [record["mode"] for _ in live for record in authored]
        material_mu.append(conservative_friction(
            pairs, modes, ground_material["coefficients"], ground_material["mode"]))

    contact_dedup_audit = {}

    def contacts():
        points, normals, owners, gaps = [], [], [], []
        loads = []
        for owner, name in enumerate(wheel_names):
            view = contact_views[name]
            nf, cp, cn, sep, counts, starts = view.get_contact_data(dt=cfg.sim.dt)
            nflat = torch.as_tensor(nf).reshape(-1)
            count_values = torch.as_tensor(counts).reshape(-1).tolist()
            start_values = torch.as_tensor(starts).reshape(-1).tolist()
            indices = []
            for count, start in zip(count_values, start_values):
                if start < 0 or count < 0 or start + count > len(nflat):
                    raise RuntimeError("invalid native wheel contact buffer")
                indices.extend(range(start, start + count))
            for index in indices:
                strength = float(nflat[index])
                normal = torch.as_tensor(cn[index]).detach().cpu().numpy()
                if strength <= 1.0e-3:
                    continue
                if not np.isfinite(strength) or not np.isfinite(normal).all() or normal[2] <= 0:
                    raise RuntimeError("invalid or downward native support contact")
                points.append(torch.as_tensor(cp[index]).detach().cpu().numpy())
                normals.append(normal)
                owners.append(owner)
                gaps.append(float(torch.as_tensor(sep[index]).item()))
            force = view.get_net_contact_forces(dt=cfg.sim.dt)
            loads.append(float(torch.linalg.vector_norm(torch.as_tensor(force).reshape(-1, 3)[0])))
        raw = dict(points=np.asarray(points, dtype=np.float64).reshape(-1, 3),
            normals=np.asarray(normals, dtype=np.float64).reshape(-1, 3),
            owners=np.asarray(owners, dtype=np.int64),
            gaps=np.asarray(gaps, dtype=np.float64))
        unique = deduplicate_contact_points(**raw)
        contact_dedup_audit.clear()
        contact_dedup_audit.update(raw_contact_count=len(raw['owners']),
            unique_contact_count=len(unique['owners']),
            multiplicities=unique['multiplicities'].tolist())
        return unique['points'], unique['normals'], unique['owners'], unique['gaps'], loads

    def measured_contact_force_components():
        """Read normal and raw friction buffers separately; their signs differ by contract."""
        normal_result = np.zeros((4, 3), dtype=np.float64)
        friction_result = np.zeros((4, 3), dtype=np.float64)
        for owner, name in enumerate(wheel_names):
            view = contact_views[name]
            normal_force = torch.as_tensor(view.get_net_contact_forces(
                dt=cfg.sim.dt)).reshape(-1, 3)
            if tuple(normal_force.shape) != (1, 3):
                raise RuntimeError("expected one measured wheel normal-force vector")
            friction_data = view.get_friction_data(dt=cfg.sim.dt)
            if len(friction_data) != 4:
                raise RuntimeError("invalid PhysX per-contact friction data contract")
            friction, _, counts, starts = friction_data
            friction = torch.as_tensor(friction).reshape(-1, 3)
            count_values = torch.as_tensor(counts).reshape(-1).tolist()
            start_values = torch.as_tensor(starts).reshape(-1).tolist()
            if len(count_values) != len(start_values):
                raise RuntimeError("invalid PhysX friction count/start buffers")
            friction_indices = []
            for count, start in zip(count_values, start_values):
                if start < 0 or count < 0 or start + count > len(friction):
                    raise RuntimeError("invalid PhysX friction buffer range")
                friction_indices.extend(range(start, start + count))
            measured_friction = (friction[friction_indices].sum(dim=0)
                                 if friction_indices else torch.zeros(3, device=friction.device))
            normal_result[owner] = normal_force[0].detach().cpu().numpy()
            friction_result[owner] = measured_friction.detach().cpu().numpy()
        if not np.isfinite(normal_result).all() or not np.isfinite(friction_result).all():
            raise RuntimeError("nonfinite measured wheel contact force component")
        return normal_result, friction_result

    def contact_mode_for_state(points, normals, owners, gaps, geometry, normal_max):
        com_pos = robot.data.body_com_pos_w[0, list(wheel_ids)].detach().cpu().numpy()
        body_velocity = robot.data.body_com_vel_w[0, list(wheel_ids)].detach().cpu().numpy()
        link_rotation = matrix_from_quat(robot.data.body_link_quat_w[0]).detach().cpu().numpy()
        kinematics = kinematic_bias(kinematic_model, robot.joint_names, robot.body_names,
            link_rotation, robot.data.body_com_vel_w[0, :, 3:].detach().cpu().numpy(),
            robot.data.joint_vel[0].detach().cpu().numpy())
        angular = body_velocity[owners, 3:]
        arms = points - com_pos[owners]
        point_bias = (kinematics["com_linear"][list(wheel_ids)][owners]
            + np.cross(kinematics["angular"][list(wheel_ids)][owners], arms)
            + np.cross(angular, np.cross(angular, arms)))
        motion = contact_motion(points=points, normals=normals, owners=owners,
            com_positions=com_pos, com_velocity=body_velocity,
            surface_velocity=np.zeros_like(points))
        geometry_velocity = smooth_wheel_geometry_velocity(
            center_velocity=body_velocity[owners, :3], normals=normals)
        measured = dict(jac=geometry["jac"], frames=geometry["frames"],
            bias=point_bias, velocity=motion["relative_velocity"], gap=gaps,
            attached=np.ones(len(points), dtype=bool),
            normal_max=np.full(len(points), normal_max), dt=cfg.sim.dt)
        welded = contact_step_constraints(**measured)
        normal_only = normal_only_contact_step_constraints(**measured)
        rolling = rolling_contact_step_constraints(
            jac=geometry["jac"], frames=geometry["frames"],
            com_bias=kinematics["com_linear"][list(wheel_ids)][owners],
            angular_bias=kinematics["angular"][list(wheel_ids)][owners],
            omega=angular, arm=arms, material_velocity=motion["material_velocity"],
            geometry_velocity=geometry_velocity,
            velocity=motion["relative_velocity"], gap=gaps,
            attached=np.ones(len(points), dtype=bool),
            normal_max=np.full(len(points), normal_max), dt=cfg.sim.dt,
            tangent_velocity_time_constant=args.tangent_velocity_time_constant)
        rolling["welded_contact_matrix"] = welded["contact_matrix"]
        rolling["welded_contact_rhs"] = welded["contact_rhs"]
        rolling["normal_only_contact_matrix"] = normal_only["contact_matrix"]
        rolling["normal_only_contact_rhs"] = normal_only["contact_rhs"]
        return rolling

    def log_contact_diagnostics(identity, points, normals, owners, gaps, mode):
        com_positions = robot.data.body_com_pos_w[0, list(wheel_ids)].detach().cpu().numpy()
        com_velocity = robot.data.body_com_vel_w[0, list(wheel_ids)].detach().cpu().numpy()
        native_jacobians = native.get_jacobians()[0, list(wheel_ids)].detach().cpu().numpy()
        report = contact_diagnostics(
            points=points, normals=normals, owners=owners,
            com_positions=com_positions, com_velocity=com_velocity,
            surface_velocity=np.zeros_like(points), gaps=gaps)
        report.update(identity=identity,
            tangent_velocity_time_constant_s=args.tangent_velocity_time_constant,
            contact_dedup=contact_dedup_audit.copy(),
            contact_points_world_xyz=points.tolist(),
            contact_gaps_m=np.asarray(gaps, dtype=np.float64).tolist(),
            contact_normals_world_xyz=normals.tolist(),
            contact_owner_order=owners.tolist(),
            rolling_total_bias_mps2=np.asarray(mode["total_bias"]).tolist(),
            rolling_rhs_mps2=np.asarray(mode["contact_rhs"]).tolist(),
            rolling_slip_speed_by_contact_mps=[
                row["slip_speed_mps"] for row in report["contacts"]])
        print("M1_WBC_CONTACT_DIAGNOSTICS " + json.dumps(report), flush=True)
        generalized_velocity = np.concatenate((
            robot.data.body_com_vel_w[0, root_body_id].detach().cpu().numpy(),
            robot.data.joint_vel[0].detach().cpu().numpy()))
        contact_jacobians = contact_geometry(
            points, normals, owners, native_jacobians, com_positions)["jac"]
        consistency = jacobian_velocity_consistency(
            wheel_com_jacobians=native_jacobians,
            generalized_velocity=generalized_velocity,
            wheel_com_velocity=com_velocity,
            contact_jacobians=contact_jacobians,
            material_contact_velocity=np.asarray(
                [row["material_velocity_mps"] for row in report["contacts"]]))
        consistency.update(identity=identity,
            scope="same_state_native_jacobian_vs_measured_velocity_not_crossing")
        print("M1_WBC_JACOBIAN_VELOCITY " + json.dumps(consistency), flush=True)
        return report

    action = torch.zeros((1, 16), device=device)
    stable_trace = []
    for settle_step in range(args.settle_steps):
        env.step(action)
        _, _, _, _, loads = contacts()
        roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
        root_velocity = robot.data.root_vel_w[0]
        stable = (min(loads) >= 35.0 and max(abs(float(roll[0])), abs(float(pitch[0]))) <= .15
                  and float(torch.linalg.vector_norm(root_velocity[:3])) <= .04
                  and float(torch.linalg.vector_norm(root_velocity[3:])) <= .20)
        stable_trace.append(stable)
        stable_trace = stable_trace[-args.stable_frames:]
        if len(stable_trace) == args.stable_frames and all(stable_trace):
            break
    if len(stable_trace) < args.stable_frames or not all(stable_trace):
        raise RuntimeError("native PD baseline did not reach the bounded four-wheel support gate")

    step = int(env.sim.current_time_step_index)
    identity = dict(env_id=0, episode=0, step=step, phase="PD_TO_WBC_HANDOFF",
                    leg=None, obstacle_id=None)
    handoff = capture_pd_handoff(env=env, robot=robot, view=native,
        identity=identity, expected_identity=identity, step=step,
        physics_steps=step, dt=cfg.sim.dt)
    points, normals, owners, gaps, loads = contacts()
    if len(points) == 0 or set(owners.tolist()) != set(range(4)):
        raise RuntimeError("all four wheel groups must provide measured native contacts")

    snapshot = generalized_snapshot(native, robot.joint_names, robot.joint_names,
        torch.zeros(1, dtype=torch.long, device=device), step)
    native_jac = native.get_jacobians()
    com_pos = robot.data.body_com_pos_w[0, list(wheel_ids)].detach().cpu().numpy()
    geometry = contact_geometry(points, normals, owners,
        native_jac[0, list(wheel_ids)].detach().cpu().numpy(), com_pos)
    contact_mode = contact_mode_for_state(points, normals, owners, gaps, geometry,
        float(native.get_masses()[0].sum().item() * 9.81))
    log_contact_diagnostics(identity, points, normals, owners, gaps, contact_mode)
    limits = np.minimum(native.get_dof_max_forces()[0].detach().cpu().numpy(),
                        robot.data.joint_effort_limits[0].detach().cpu().numpy())
    prior_pd = np.asarray(handoff["effort"], dtype=np.float64)
    handoff_hard_bounds = dict(
        lower=np.maximum(-limits, prior_pd - 20.0 * cfg.sim.dt),
        upper=np.minimum(limits, prior_pd + 20.0 * cfg.sim.dt))
    handoff_bounds = qp_effort_interior_bounds(bounds=handoff_hard_bounds, margin=1e-5)
    weight = float(native.get_masses()[0].sum().item() * 9.81)
    handoff_acceleration_contract = pd_handoff_acceleration_contract(
        base_priority=args.base_priority)
    if args.snapshot_only:
        rotations=matrix_from_quat(robot.data.body_link_quat_w[0]).detach().cpu().numpy()
        kin=kinematic_bias(kinematic_model,robot.joint_names,robot.body_names,rotations,
            robot.data.body_com_vel_w[0,:,3:].detach().cpu().numpy(),
            robot.data.joint_vel[0].detach().cpu().numpy())
        state=dict(scope="native_snapshot_only_no_wbc_application_or_crossing",
            identity=identity,dt=cfg.sim.dt,joint_names=list(robot.joint_names),
            wheel_names=list(wheel_names),weight=weight,loads=loads,
            mass=snapshot['mass'][0].double().cpu().numpy(),
            bias=snapshot['bias'][0].double().cpu().numpy(),
            jac=geometry['jac'],frames=geometry['frames'],group_ids=geometry['group_ids'],
            mu=np.asarray([material_mu[int(owner)] for owner in owners]),
            contact_matrix=contact_mode['contact_matrix'],contact_rhs=contact_mode['contact_rhs'],
            effort_lower=handoff_bounds['lower'],effort_upper=handoff_bounds['upper'],
            native_limits=limits,prior_effort=prior_pd,
            accel_lower=handoff_acceleration_contract['accel_lower'],
            accel_upper=handoff_acceleration_contract['accel_upper'],
            wheel_com_jac=native_jac[0,list(wheel_ids)].detach().cpu().numpy(),
            wheel_com_bias=kin['com_linear'][list(wheel_ids)],
            root_com_velocity=robot.data.body_com_vel_w[0,root_body_id].detach().cpu().numpy(),
            joint_velocity=robot.data.joint_vel[0].detach().cpu().numpy(),
            points=points,gaps=gaps,owners=owners)
        print('M1_WBC_STATE '+json.dumps(state,default=lambda value:value.tolist()),flush=True)
        raise _SnapshotComplete()
    solution = solve_wbc(
        mass=snapshot["mass"][0].double().cpu().numpy(),
        bias=snapshot["bias"][0].double().cpu().numpy(),
        jac=geometry["jac"], frames=geometry["frames"],
        mu=np.asarray([material_mu[int(owner)] for owner in owners]),
        normal_min=np.zeros(len(points)),
        normal_max=np.full(len(points), weight),
        effort_lower=handoff_bounds["lower"], effort_upper=handoff_bounds["upper"],
        contact_matrix=contact_mode["contact_matrix"],
        contact_rhs=contact_mode["contact_rhs"],
        separation_matrix=contact_mode["separation_matrix"],
        separation_lower=contact_mode["separation_lower"],
        group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
        group_max=np.full(4, weight), identity=identity,
        joint_names=tuple(robot.joint_names), **handoff_acceleration_contract)
    if not solution["valid"]:
        # Diagnostic-only counterfactual: determine whether the measured
        # stance equations are feasible at native effort capacity. This
        # result is never applied and cannot bypass the fixed handoff slew.
        static = solve_wbc(
            mass=snapshot["mass"][0].double().cpu().numpy(),
            bias=snapshot["bias"][0].double().cpu().numpy(),
            jac=geometry["jac"], frames=geometry["frames"],
            mu=np.asarray([material_mu[int(owner)] for owner in owners]),
            normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
            accel_lower=np.zeros(22), accel_upper=np.zeros(22),
            effort_lower=-limits, effort_upper=limits,
            contact_matrix=contact_mode["contact_matrix"],
            contact_rhs=contact_mode["contact_rhs"],
            separation_matrix=contact_mode["separation_matrix"],
            separation_lower=contact_mode["separation_lower"],
            group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
            group_max=np.full(4, weight), identity=identity,
            joint_names=tuple(robot.joint_names))
        raise RuntimeError("measured same-state static WBC handoff is infeasible: " + json.dumps({
            "reason": solution["reason"], "stages": solution["stages"],
            "mu_by_wheel": material_mu, "owners": owners.tolist(),
            "contact_count_by_wheel": [int(np.sum(owners == i)) for i in range(4)],
            "measured_pd_effort_nm": prior_pd.tolist(),
            "effort_lower_nm": handoff_hard_bounds["lower"].tolist(),
            "effort_upper_nm": handoff_hard_bounds["upper"].tolist(), "support_loads_n": loads,
            "weight_n": weight, "joint_names": list(robot.joint_names),
            "native_capacity_static_feasible": static["valid"],
            "native_capacity_static_reason": static["reason"],
            "native_capacity_static_stages": static["stages"],
            "native_capacity_static_effort_nm": (static["effort"].tolist()
                if static["valid"] else None)}))

    handoff_result = apply_wbc_command(env=env, robot=robot, view=native,
        solution=solution, identity=identity, expected_identity=identity,
        previous=None, step=step, physics_steps=step, dt=cfg.sim.dt,
        handoff=handoff)

    def observe_support(tick):
        _, _, _, _, loads = contacts()
        roll, pitch = extract_roll_pitch_batch(robot.data.root_quat_w)
        root_velocity = robot.data.root_vel_w[0]
        return dict(tick=tick + 1, loads_n=loads,
            root_z_m=float(robot.data.root_pos_w[0, 2]),
            roll_rad=float(roll[0]), pitch_rad=float(pitch[0]),
            linear_speed_mps=float(torch.linalg.vector_norm(root_velocity[:3])),
            angular_speed_rad_s=float(torch.linalg.vector_norm(root_velocity[3:])))

    def require_support_gate(record, speed_limit=0.04):
        if (min(record["loads_n"]) < 30.0
                or max(abs(record["roll_rad"]), abs(record["pitch_rad"])) > .15
                or record["linear_speed_mps"] > speed_limit
                or record["angular_speed_rad_s"] > .20):
            raise RuntimeError("receding-horizon WBC support gate failed: " + json.dumps(record))

    trace = []
    previous = handoff_result["record"]
    # Advance once with the accepted same-state handoff, then use feedback
    # and a fresh WBC solve on every subsequent physics tick.
    env.sim.step(render=False)
    env.scene.update(cfg.sim.dt)
    initial_sample = observe_support(0)
    require_support_gate(initial_sample, speed_limit=0.08)
    trace.append(initial_sample)
    for tick in range(args.hold_steps):
        step = int(env.sim.current_time_step_index)
        identity = dict(env_id=0, episode=0, step=step, phase="WBC_SUPPORT_HOLD",
                        leg=None, obstacle_id=None)
        points, normals, owners, gaps, loads = contacts()
        if len(points) == 0 or set(owners.tolist()) != set(range(4)):
            raise RuntimeError("closed-loop WBC lost a measured support wheel")
        snapshot = generalized_snapshot(native, robot.joint_names, robot.joint_names,
            torch.zeros(1, dtype=torch.long, device=device), step)
        native_jac = native.get_jacobians()
        com_pos = robot.data.body_com_pos_w[0, list(wheel_ids)].detach().cpu().numpy()
        geometry = contact_geometry(points, normals, owners,
            native_jac[0, list(wheel_ids)].detach().cpu().numpy(), com_pos)
        contact_mode = contact_mode_for_state(points, normals, owners, gaps, geometry, weight)
        contact_before = None
        if tick == 0:
            contact_before = log_contact_diagnostics(
                identity, points, normals, owners, gaps, contact_mode)
        step_bounds = effort_step_bounds(previous=previous, limits=limits,
            rate=np.full(16, 20.0), dt=cfg.sim.dt, step=step, episode=0)
        qp_step_bounds = qp_effort_interior_bounds(bounds=step_bounds, margin=1e-5)
        root_velocity = robot.data.root_vel_w[0].detach().cpu().numpy()
        root_com_velocity_before = robot.data.body_com_vel_w[
            0, root_body_id].detach().cpu().numpy()
        joint_velocity = robot.data.joint_vel[0].detach().cpu().numpy()
        generalized_velocity_before = np.concatenate((root_com_velocity_before, joint_velocity))
        target_qdd = support_damping_target(
            root_com_velocity=root_com_velocity_before,
            joint_velocity=joint_velocity)
        tick_acceleration_contract = pd_handoff_acceleration_contract(
            target_qdd=target_qdd, base_priority=args.base_priority)
        solution = solve_wbc(
            mass=snapshot["mass"][0].double().cpu().numpy(),
            bias=snapshot["bias"][0].double().cpu().numpy(),
            jac=geometry["jac"], frames=geometry["frames"],
            mu=np.asarray([material_mu[int(owner)] for owner in owners]),
            normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
            effort_lower=qp_step_bounds["lower"], effort_upper=qp_step_bounds["upper"],
            contact_matrix=contact_mode["contact_matrix"],
            contact_rhs=contact_mode["contact_rhs"],
            separation_matrix=contact_mode["separation_matrix"],
            separation_lower=contact_mode["separation_lower"],
            group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
            group_max=np.full(4, weight), identity=identity,
            joint_names=tuple(robot.joint_names), **tick_acceleration_contract)
        if tick == 0:
            fast_hard_bounds = effort_step_bounds(previous=previous, limits=limits,
                rate=np.full(16, 200.0), dt=cfg.sim.dt, step=step, episode=0)
            fast_bounds = qp_effort_interior_bounds(bounds=fast_hard_bounds, margin=1e-5)
            fast_solution = solve_wbc(
                mass=snapshot["mass"][0].double().cpu().numpy(),
                bias=snapshot["bias"][0].double().cpu().numpy(),
                jac=geometry["jac"], frames=geometry["frames"],
                mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                effort_lower=fast_bounds["lower"], effort_upper=fast_bounds["upper"],
                contact_matrix=contact_mode["contact_matrix"],
                contact_rhs=contact_mode["contact_rhs"],
                separation_matrix=contact_mode["separation_matrix"],
                separation_lower=contact_mode["separation_lower"],
                group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                group_max=np.full(4, weight), identity=identity,
                joint_names=tuple(robot.joint_names), **tick_acceleration_contract)
            capacity_solution = solve_wbc(
                mass=snapshot["mass"][0].double().cpu().numpy(),
                bias=snapshot["bias"][0].double().cpu().numpy(),
                jac=geometry["jac"], frames=geometry["frames"],
                mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                effort_lower=-limits, effort_upper=limits,
                contact_matrix=contact_mode["contact_matrix"],
                contact_rhs=contact_mode["contact_rhs"],
                separation_matrix=contact_mode["separation_matrix"],
                separation_lower=contact_mode["separation_lower"],
                group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                group_max=np.full(4, weight), identity=identity,
                joint_names=tuple(robot.joint_names), **tick_acceleration_contract)
            unbounded_effort_solution = solve_wbc(
                mass=snapshot["mass"][0].double().cpu().numpy(),
                bias=snapshot["bias"][0].double().cpu().numpy(),
                jac=geometry["jac"], frames=geometry["frames"],
                mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                effort_lower=qp_step_bounds["lower"], effort_upper=qp_step_bounds["upper"],
                contact_matrix=contact_mode["contact_matrix"],
                contact_rhs=contact_mode["contact_rhs"],
                separation_matrix=contact_mode["separation_matrix"],
                separation_lower=contact_mode["separation_lower"],
                group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                group_max=np.full(4, weight), identity=identity,
                joint_names=tuple(robot.joint_names), **tick_acceleration_contract)
            normal_only_capacity_solution = solve_wbc(
                mass=snapshot["mass"][0].double().cpu().numpy(),
                bias=snapshot["bias"][0].double().cpu().numpy(),
                jac=geometry["jac"], frames=geometry["frames"],
                mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                effort_lower=-limits, effort_upper=limits,
                contact_matrix=contact_mode["normal_only_contact_matrix"],
                contact_rhs=contact_mode["normal_only_contact_rhs"],
                separation_matrix=contact_mode["separation_matrix"],
                separation_lower=contact_mode["separation_lower"],
                group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                group_max=np.full(4, weight), identity=identity,
                joint_names=tuple(robot.joint_names), **tick_acceleration_contract)
            welded_capacity_solution = solve_wbc(
                mass=snapshot["mass"][0].double().cpu().numpy(),
                bias=snapshot["bias"][0].double().cpu().numpy(),
                jac=geometry["jac"], frames=geometry["frames"],
                mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                effort_lower=-limits, effort_upper=limits,
                contact_matrix=contact_mode["welded_contact_matrix"],
                contact_rhs=contact_mode["welded_contact_rhs"],
                separation_matrix=contact_mode["separation_matrix"],
                separation_lower=contact_mode["separation_lower"],
                group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                group_max=np.full(4, weight), identity=identity,
                joint_names=tuple(robot.joint_names), **tick_acceleration_contract)
            local_contact_matrix, local_contact_rhs = project_contact_rows_to_local_frames(
                jac=contact_mode["contact_matrix"].reshape(-1, 3, 22),
                frames=geometry["frames"],
                rhs=contact_mode["contact_rhs"].reshape(-1, 3))
            tangent_axis_ablation = {}
            for omitted_tangent_axis in (0, 1):
                keep_local_axes = [axis for axis in range(3)
                                   if axis != omitted_tangent_axis]
                ablated = solve_wbc(
                    mass=snapshot["mass"][0].double().cpu().numpy(),
                    bias=snapshot["bias"][0].double().cpu().numpy(),
                    jac=geometry["jac"], frames=geometry["frames"],
                    mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                    normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                    effort_lower=qp_step_bounds["lower"], effort_upper=qp_step_bounds["upper"],
                    contact_matrix=local_contact_matrix[:, keep_local_axes].reshape(-1, 22),
                    contact_rhs=local_contact_rhs[:, keep_local_axes].reshape(-1),
                    separation_matrix=contact_mode["separation_matrix"],
                    separation_lower=contact_mode["separation_lower"],
                    group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                    group_max=np.full(4, weight), identity=identity,
                    joint_names=tuple(robot.joint_names), **tick_acceleration_contract)
                tangent_axis_ablation[f"omit_local_tangent_{omitted_tangent_axis}"] = dict(
                    valid=ablated["valid"], reason=ablated["reason"],
                    qdd_base_linear=(ablated["qdd"][:3].tolist()
                                     if ablated["valid"] else None),
                    stages=ablated["stages"])
            base_task_matrix = np.zeros((6, 22), dtype=np.float64)
            base_task_matrix[:, :6] = np.eye(6)
            joint_task_matrix = np.zeros((16, 22), dtype=np.float64)
            joint_task_matrix[:, 6:] = np.eye(16)
            base_priority_solution = solve_wbc(
                mass=snapshot["mass"][0].double().cpu().numpy(),
                bias=snapshot["bias"][0].double().cpu().numpy(),
                jac=geometry["jac"], frames=geometry["frames"],
                mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                effort_lower=qp_step_bounds["lower"], effort_upper=qp_step_bounds["upper"],
                contact_matrix=contact_mode["contact_matrix"],
                contact_rhs=contact_mode["contact_rhs"],
                separation_matrix=contact_mode["separation_matrix"],
                separation_lower=contact_mode["separation_lower"],
                group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                group_max=np.full(4, weight), identity=identity,
                joint_names=tuple(robot.joint_names),
                tasks=((base_task_matrix, target_qdd[:6].copy(), np.ones(6)),
                       (joint_task_matrix, target_qdd[6:].copy(), np.ones(16))),
                accel_lower=tick_acceleration_contract["accel_lower"],
                accel_upper=tick_acceleration_contract["accel_upper"])
            forced_x_lower = tick_acceleration_contract["accel_lower"].copy()
            forced_x_upper = tick_acceleration_contract["accel_upper"].copy()
            forced_x_lower[0] = target_qdd[0]
            forced_x_upper[0] = target_qdd[0]
            other_qdd_indices = np.arange(1, 22)
            other_qdd_task = np.zeros((21, 22), dtype=np.float64)
            other_qdd_task[np.arange(21), other_qdd_indices] = 1.0
            forced_x_solution = solve_wbc(
                mass=snapshot["mass"][0].double().cpu().numpy(),
                bias=snapshot["bias"][0].double().cpu().numpy(),
                jac=geometry["jac"], frames=geometry["frames"],
                mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                effort_lower=np.full(16, -1.0e4), effort_upper=np.full(16, 1.0e4),
                contact_matrix=contact_mode["contact_matrix"],
                contact_rhs=contact_mode["contact_rhs"],
                separation_matrix=contact_mode["separation_matrix"],
                separation_lower=contact_mode["separation_lower"],
                group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                group_max=np.full(4, weight), identity=identity,
                joint_names=tuple(robot.joint_names),
                tasks=((other_qdd_task, target_qdd[other_qdd_indices].copy(),
                        np.ones(21)),),
                accel_lower=forced_x_lower, accel_upper=forced_x_upper)
            forced_x_capacity_solution = solve_wbc(
                mass=snapshot["mass"][0].double().cpu().numpy(),
                bias=snapshot["bias"][0].double().cpu().numpy(),
                jac=geometry["jac"], frames=geometry["frames"],
                mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                effort_lower=-limits, effort_upper=limits,
                contact_matrix=contact_mode["contact_matrix"],
                contact_rhs=contact_mode["contact_rhs"],
                separation_matrix=contact_mode["separation_matrix"],
                separation_lower=contact_mode["separation_lower"],
                group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                group_max=np.full(4, weight), identity=identity,
                joint_names=tuple(robot.joint_names),
                tasks=((other_qdd_task, target_qdd[other_qdd_indices].copy(),
                        np.ones(21)),),
                accel_lower=forced_x_lower, accel_upper=forced_x_upper)
            safety_indices = np.asarray([2, 3, 4, 5], dtype=np.int64)
            safety_task = np.zeros((len(safety_indices), 22), dtype=np.float64)
            safety_task[np.arange(len(safety_indices)), safety_indices] = 1.0
            x_task = np.zeros((1, 22), dtype=np.float64)
            x_task[0, 0] = 1.0
            secondary_indices = np.asarray([1, *range(6, 22)], dtype=np.int64)
            secondary_task = np.zeros((len(secondary_indices), 22), dtype=np.float64)
            secondary_task[np.arange(len(secondary_indices)), secondary_indices] = 1.0
            safe_priority_solution = solve_wbc(
                mass=snapshot["mass"][0].double().cpu().numpy(),
                bias=snapshot["bias"][0].double().cpu().numpy(),
                jac=geometry["jac"], frames=geometry["frames"],
                mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                effort_lower=qp_step_bounds["lower"], effort_upper=qp_step_bounds["upper"],
                contact_matrix=contact_mode["contact_matrix"],
                contact_rhs=contact_mode["contact_rhs"],
                separation_matrix=contact_mode["separation_matrix"],
                separation_lower=contact_mode["separation_lower"],
                group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                group_max=np.full(4, weight), identity=identity,
                joint_names=tuple(robot.joint_names),
                tasks=((safety_task, target_qdd[safety_indices].copy(),
                        np.ones(len(safety_indices))),
                       (x_task, target_qdd[:1].copy(), np.ones(1)),
                       (secondary_task, target_qdd[secondary_indices].copy(),
                        np.ones(len(secondary_indices)))),
                accel_lower=tick_acceleration_contract["accel_lower"],
                accel_upper=tick_acceleration_contract["accel_upper"])
            # Diagnostic only: preserve lateral/vertical and angular support
            # before asking for forward braking. This tests whether the
            # earlier hard-x counterfactual was exploiting unsafe y/z motion.
            support_indices = np.asarray([1, 2, 3, 4, 5], dtype=np.int64)
            support_task = np.zeros((len(support_indices), 22), dtype=np.float64)
            support_task[np.arange(len(support_indices)), support_indices] = 1.0
            joint_only_task = np.zeros((16, 22), dtype=np.float64)
            joint_only_task[:, 6:] = np.eye(16)
            support_then_x_solution = solve_wbc(
                mass=snapshot["mass"][0].double().cpu().numpy(),
                bias=snapshot["bias"][0].double().cpu().numpy(),
                jac=geometry["jac"], frames=geometry["frames"],
                mu=np.asarray([material_mu[int(owner)] for owner in owners]),
                normal_min=np.zeros(len(points)), normal_max=np.full(len(points), weight),
                effort_lower=qp_step_bounds["lower"], effort_upper=qp_step_bounds["upper"],
                contact_matrix=contact_mode["contact_matrix"],
                contact_rhs=contact_mode["contact_rhs"],
                separation_matrix=contact_mode["separation_matrix"],
                separation_lower=contact_mode["separation_lower"],
                group_ids=geometry["group_ids"], group_min=np.full(4, 35.0),
                group_max=np.full(4, weight), identity=identity,
                joint_names=tuple(robot.joint_names),
                tasks=((support_task, target_qdd[support_indices].copy(),
                        np.ones(len(support_indices))),
                       (x_task, target_qdd[:1].copy(), np.ones(1)),
                       (joint_only_task, target_qdd[6:].copy(), np.ones(16))),
                accel_lower=tick_acceleration_contract["accel_lower"],
                accel_upper=tick_acceleration_contract["accel_upper"])
            print("M1_WBC_SLEW_SHADOW " + json.dumps({
                "scope": "same_state_counterfactual_not_applied",
                "hard_rate_nm_s": 200.0,
                "rate_20_valid": solution["valid"],
                "rate_20_qdd_base_linear": (solution["qdd"][:3].tolist()
                    if solution["valid"] else None),
                "rate_200_valid": fast_solution["valid"],
                "rate_200_reason": fast_solution["reason"],
                "rate_200_qdd_base_linear": (fast_solution["qdd"][:3].tolist()
                    if fast_solution["valid"] else None),
                "rate_200_effort_nm": (fast_solution["effort"].tolist()
                    if fast_solution["valid"] else None),
                "native_capacity_valid": capacity_solution["valid"],
                "native_capacity_reason": capacity_solution["reason"],
                "native_capacity_qdd_base_linear": (capacity_solution["qdd"][:3].tolist()
                    if capacity_solution["valid"] else None),
                "native_capacity_effort_nm": (capacity_solution["effort"].tolist()
                    if capacity_solution["valid"] else None),
                "unbounded_effort_shadow_not_applied": {
                    "valid": unbounded_effort_solution["valid"],
                    "reason": unbounded_effort_solution["reason"],
                    "qdd_base_linear": (unbounded_effort_solution["qdd"][:3].tolist()
                        if unbounded_effort_solution["valid"] else None),
                    "effort_nm": (unbounded_effort_solution["effort"].tolist()
                        if unbounded_effort_solution["valid"] else None),
                    "stages": unbounded_effort_solution["stages"]},
                "base_priority_shadow_not_applied": {
                    "valid": base_priority_solution["valid"],
                    "reason": base_priority_solution["reason"],
                    "qdd_base_linear": (base_priority_solution["qdd"][:3].tolist()
                        if base_priority_solution["valid"] else None),
                    "effort_nm": (base_priority_solution["effort"].tolist()
                        if base_priority_solution["valid"] else None),
                    "stages": base_priority_solution["stages"]},
                "forced_target_x_shadow_not_applied": {
                    "target_qdd_x": float(target_qdd[0]),
                    "valid": forced_x_solution["valid"],
                    "reason": forced_x_solution["reason"],
                    "qdd_base_linear": (forced_x_solution["qdd"][:3].tolist()
                        if forced_x_solution["valid"] else None),
                    "effort_nm": (forced_x_solution["effort"].tolist()
                        if forced_x_solution["valid"] else None),
                    "stages": forced_x_solution["stages"]},
                "forced_target_x_native_effort_shadow_not_applied": {
                    "valid": forced_x_capacity_solution["valid"],
                    "reason": forced_x_capacity_solution["reason"],
                    "qdd_base_linear": (forced_x_capacity_solution["qdd"][:3].tolist()
                        if forced_x_capacity_solution["valid"] else None),
                    "effort_nm": (forced_x_capacity_solution["effort"].tolist()
                        if forced_x_capacity_solution["valid"] else None),
                    "effort_limit_ratio_max": (float(np.max(np.abs(
                        forced_x_capacity_solution["effort"]) / limits))
                        if forced_x_capacity_solution["valid"] else None),
                    "stages": forced_x_capacity_solution["stages"]},
                "safety_then_x_priority_shadow_not_applied": {
                    "valid": safe_priority_solution["valid"],
                    "reason": safe_priority_solution["reason"],
                    "qdd_base": (safe_priority_solution["qdd"][:6].tolist()
                        if safe_priority_solution["valid"] else None),
                    "effort_nm": (safe_priority_solution["effort"].tolist()
                        if safe_priority_solution["valid"] else None),
                    "stages": safe_priority_solution["stages"]},
                "support_then_x_shadow_not_applied": {
                    "valid": support_then_x_solution["valid"],
                    "reason": support_then_x_solution["reason"],
                    "qdd_base": (support_then_x_solution["qdd"][:6].tolist()
                        if support_then_x_solution["valid"] else None),
                    "effort_nm": (support_then_x_solution["effort"].tolist()
                        if support_then_x_solution["valid"] else None),
                    "stages": support_then_x_solution["stages"]},
                "welded_capacity_valid": welded_capacity_solution["valid"],
                "welded_capacity_qdd_base_linear": (
                    welded_capacity_solution["qdd"][:3].tolist()
                    if welded_capacity_solution["valid"] else None),
                "normal_only_ablation_valid": normal_only_capacity_solution["valid"],
                "normal_only_ablation_qdd_base_linear": (
                    normal_only_capacity_solution["qdd"][:3].tolist()
                    if normal_only_capacity_solution["valid"] else None),
                "target_qdd_base_linear": target_qdd[:3].tolist(),
                "rolling_tangent_axis_ablation_not_applied": tangent_axis_ablation}),
                flush=True)
        if not solution["valid"]:
            raise RuntimeError("closed-loop support WBC infeasible: " + json.dumps({
                "tick": tick, "reason": solution["reason"], "stages": solution["stages"],
                "support_loads_n": loads, "mu_by_wheel": material_mu,
                "qdd_target": target_qdd.tolist(),
                "qdd_bounds": [tick_acceleration_contract["accel_lower"].tolist(),
                               tick_acceleration_contract["accel_upper"].tolist()]}))
        command_result = apply_wbc_command(env=env, robot=robot, view=native,
            solution=solution, identity=identity, expected_identity=identity,
            previous=previous, step=step, physics_steps=step, dt=cfg.sim.dt)
        previous = command_result["record"]
        predicted_contact_acceleration = np.einsum(
            "kci,i->kc", geometry["jac"], solution["qdd"])
        predicted_contact_acceleration += contact_mode["total_bias"]
        env.sim.step(render=False)
        env.scene.update(cfg.sim.dt)
        contact_acceleration_record = None
        if tick == 0:
            next_points, next_normals, next_owners, next_gaps, next_loads = contacts()
            # The QP optimizes contact forces in world coordinates: the
            # dynamics equality uses world-frame Jacobians directly. Do not
            # rotate these forces through the contact frame a second time.
            predicted_contact_force = solution["force"]
            contact_force_record = wheel_contact_force_consistency(
                predicted_world_force=predicted_contact_force,
                contact_normals=geometry["frames"][:, :, 2],
                owners=owners,
                measured_wheel_normal_load=np.asarray(next_loads, dtype=np.float64))
            contact_force_record.update(identity=identity,
                scope="qp_normal_load_vs_next_physx_normal_sensor_not_crossing")
            print("M1_WBC_CONTACT_FORCE " + json.dumps(
                contact_force_record), flush=True)
            measured_normal_force, raw_friction_force = measured_contact_force_components()
            contact_force_vector_record = wheel_contact_force_vector_consistency(
                predicted_world_force=predicted_contact_force,
                owners=owners, measured_wheel_normal_force=measured_normal_force,
                raw_wheel_friction_force=raw_friction_force)
            contact_force_vector_record.update(identity=identity,
                scope="qp_vs_physx_normal_and_raw_friction_both_signs_reported_not_crossing")
            print("M1_WBC_CONTACT_FORCE_VECTOR " + json.dumps(
                contact_force_vector_record), flush=True)
            if (len(next_points) == len(points)
                    and np.array_equal(next_owners, owners)):
                next_positions = robot.data.body_com_pos_w[
                    0, list(wheel_ids)].detach().cpu().numpy()
                next_velocity = robot.data.body_com_vel_w[
                    0, list(wheel_ids)].detach().cpu().numpy()
                next_contact = contact_diagnostics(
                    points=next_points, normals=next_normals, owners=next_owners,
                    com_positions=next_positions, com_velocity=next_velocity,
                    surface_velocity=np.zeros_like(next_points), gaps=next_gaps)
                measured_before = np.asarray([
                    row["relative_velocity_mps"] for row in contact_before["contacts"]])
                measured_after = np.asarray([
                    row["relative_velocity_mps"] for row in next_contact["contacts"]])
                contact_acceleration_record = contact_acceleration_consistency(
                    predicted_acceleration=predicted_contact_acceleration,
                    velocity_before=measured_before,
                    velocity_after=measured_after, dt=cfg.sim.dt)
                contact_point_velocity_fd = (next_points - points) / cfg.sim.dt
                geometry_velocity_model = np.asarray([
                    row["geometry_velocity_mps"] for row in contact_before["contacts"]])
                contact_acceleration_record.update(
                    identity=identity, next_step=int(env.sim.current_time_step_index),
                    contact_owner_order=owners.tolist(),
                    gaps_before_m=np.asarray(gaps, dtype=np.float64).tolist(),
                    gaps_after_m=np.asarray(next_gaps, dtype=np.float64).tolist(),
                    contact_point_velocity_fd_mps=contact_point_velocity_fd.tolist(),
                    geometry_velocity_model_mps=geometry_velocity_model.tolist(),
                    max_geometry_velocity_error_mps=float(np.max(np.abs(
                        contact_point_velocity_fd - geometry_velocity_model))),
                    scope="first_wbc_tick_live_contact_velocity_finite_difference_not_crossing")
            else:
                contact_acceleration_record = dict(
                    identity=identity,
                    scope="diagnostic_unavailable_contact_set_changed",
                    contacts_before=len(points), contacts_after=len(next_points),
                    owner_order_before=owners.tolist(), owner_order_after=next_owners.tolist())
            print("M1_WBC_CONTACT_ACCELERATION " + json.dumps(
                contact_acceleration_record), flush=True)
        root_com_velocity_after = robot.data.body_com_vel_w[
            0, root_body_id].detach().cpu().numpy()
        qdd_root_com_fd = (root_com_velocity_after-root_com_velocity_before)/cfg.sim.dt
        generalized_velocity_after = np.concatenate((
            root_com_velocity_after,
            robot.data.joint_vel[0].detach().cpu().numpy()))
        generalized_acceleration_record = generalized_acceleration_consistency(
            predicted_acceleration=solution["qdd"],
            velocity_before=generalized_velocity_before,
            velocity_after=generalized_velocity_after, dt=cfg.sim.dt)
        generalized_acceleration_record.update(
            identity=identity,
            generalized_coordinate_order=[
                "root_com_vx", "root_com_vy", "root_com_vz",
                "root_com_wx", "root_com_wy", "root_com_wz",
                *list(robot.joint_names)],
            scope="first_wbc_tick_full_generalized_fd_not_crossing")
        print("M1_WBC_GENERALIZED_ACCELERATION " + json.dumps(
            generalized_acceleration_record), flush=True)
        sample = observe_support(tick + 1)
        sample.update(command_nm=previous["command"].tolist(),
            max_abs_qdd=float(np.max(np.abs(solution["qdd"]))),
            max_abs_base_linear_qdd=float(np.max(np.abs(solution["qdd"][:3]))),
            max_abs_base_angular_qdd=float(np.max(np.abs(solution["qdd"][3:6]))),
            max_abs_joint_qdd=float(np.max(np.abs(solution["qdd"][6:]))),
            qdd_base_linear=solution["qdd"][:3].tolist(),
            qdd_target_base_linear=target_qdd[:3].tolist(),
            qdd_root_com_fd_linear=qdd_root_com_fd[:3].tolist(),
            qdd_root_com_fd_angular=qdd_root_com_fd[3:6].tolist(),
            qdd_model_minus_root_com_fd_linear=(
                solution["qdd"][:3]-qdd_root_com_fd[:3]).tolist(),
            qdd_model_minus_root_com_fd_angular=(
                solution["qdd"][3:6]-qdd_root_com_fd[3:6]).tolist())
        trace.append(sample)
        print("M1_WBC_SUPPORT_TICK " + json.dumps(sample), flush=True)
        require_support_gate(sample, speed_limit=0.08)

    require_support_gate(trace[-1], speed_limit=0.04)

    print("M1_WBC_PD_HANDOFF " + json.dumps({
        "scope": "same_state_handoff_and_closed_loop_flat_support_not_crossing",
        "handoff_step": step,
        "joint_names": list(robot.joint_names),
        "measured_pd_effort_nm": prior_pd.tolist(),
        "handoff_qdd_rad_mps2": solution["qdd"].tolist(),
        "max_abs_handoff_base_linear_accel_mps2": float(np.max(np.abs(solution["qdd"][:3]))),
        "max_abs_handoff_base_angular_accel_rad_s2": float(np.max(np.abs(solution["qdd"][3:6]))),
        "max_abs_handoff_joint_accel_rad_s2": float(np.max(np.abs(solution["qdd"][6:]))),
        "wbc_effort_nm": solution["effort"].tolist(),
        "handoff_readback_error_nm": handoff_result["readback_error"],
        "initial_support_loads_n": loads,
        "hold_steps": len(trace) - 1,
        "control_mode": "receding_horizon_wbc_each_physics_tick",
        "max_abs_qdd": max(row.get("max_abs_qdd", 0.) for row in trace),
        "max_abs_roll_rad": max(abs(row["roll_rad"]) for row in trace),
        "max_abs_pitch_rad": max(abs(row["pitch_rad"]) for row in trace),
        "max_linear_speed_mps": max(row["linear_speed_mps"] for row in trace),
        "final_linear_speed_mps": trace[-1]["linear_speed_mps"],
        "max_angular_speed_rad_s": max(row["angular_speed_rad_s"] for row in trace),
        "final": trace[-1],
    }), flush=True)
except _SnapshotComplete:
    pass
except BaseException as exc:
    import traceback
    failure = exc
    print("M1_WBC_PD_HANDOFF_ERROR " + repr(exc), file=sys.stderr, flush=True)
    traceback.print_exc()
finally:
    if env is not None:
        try:
            env.close()
        except BaseException as exc:
            print("M1_WBC_PD_HANDOFF_ENV_CLOSE_ERROR " + repr(exc),
                  file=sys.stderr, flush=True)
            if failure is None:
                failure = exc
    try:
        launcher.app.close()
    except BaseException as exc:
        print("M1_WBC_PD_HANDOFF_APP_CLOSE_ERROR " + repr(exc),
              file=sys.stderr, flush=True)
        if failure is None:
            failure = exc
if failure is not None:
    raise SystemExit(1)
