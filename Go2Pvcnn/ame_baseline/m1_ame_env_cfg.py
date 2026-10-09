"""M1 AME environment contract with an explicit M1 obstacle curriculum."""
from __future__ import annotations
import os
from isaaclab.utils import configclass
from isaaclab.envs import mdp as isaac_mdp
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from tracking.cross_large_complex_ppo_env_cfg import CrossLargeComplexPpoRewardsCfg
from go2_pvcnn.assets.m1 import M1_CFG
from go2_pvcnn.tasks.teacher_elevation_trajectory_mpc_semantic_env_cfg import (
    TeacherElevationTrajectoryMpcSemanticTerminationsCfg,
)
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES, M1_ROOT_Z_M, M1_DEFAULT_ASSET_JOINT_POS, M1_WHEEL_RADIUS_M, M1_WHEEL_THICKNESS_M, M1_WHEEL_HORIZONTAL_ENVELOPE_M
from extension.parallelism.rl_adapter import select_named_joint_state
from extension.semantic_course import SemanticCourseLayoutCfg, SemanticCourseGroundingCfg
from extension.semantic_curriculum import SemanticObstacleCount
from .ame_env_cfg import AmeCrossLargeComplexEnvCfg, AmeObservationsCfg
from .m1_ame_terminations import nonfinite_robot_state
from . import m1_ame_rewards as m1_rewards
from . import m1_obstacle_rewards
from .m1_ame_actions import M1AmeActionsCfg
from .m1_ame_assets import spawn_m1_floating_usd
from .m1_ame_contract import (
    m1_last_leg_action, m1_last_action, m1_wheel_surface_velocity,
    M1_WHEEL_ACTION_SCALE_RAD_S, M1_WHEEL_SPEED_LIMIT_RAD_S,
    M1_TRAINING_ROOT_Z_M, M1_TRAINING_JOINT_POS,
)
from .m1_obstacle_profile import (
    M1_DEFAULT_SMALL_OBSTACLE_HEIGHT_M,
    M1_FIXED_LARGE_OBSTACLE_LOCAL_XY,
    M1_FIXED_SMALL_OBSTACLE_LOCAL_XY,
    M1_SMALL_OBSTACLE_DIAMETER_M,
)


def build_m1_policy_joint_terms(state, source_names=M1_ASSET_JOINT_NAMES):
    return select_named_joint_state(state, source_names=source_names, selected_names=M1_PLANNER_JOINT_NAMES)

def m1_joint_pos_rel(env, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")):
    robot = env.scene[asset_cfg.name]
    return select_named_joint_state(robot.data.joint_pos, source_names=tuple(robot.joint_names), selected_names=M1_PLANNER_JOINT_NAMES) - select_named_joint_state(robot.data.default_joint_pos, source_names=tuple(robot.joint_names), selected_names=M1_PLANNER_JOINT_NAMES)

def m1_joint_vel_rel(env, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")):
    robot = env.scene[asset_cfg.name]
    return select_named_joint_state(robot.data.joint_vel, source_names=tuple(robot.joint_names), selected_names=M1_PLANNER_JOINT_NAMES)

@configclass
class M1AmeObservationsCfg(AmeObservationsCfg):
    @configclass
    class PolicyStateCfg(AmeObservationsCfg.PolicyStateCfg):
        actions = ObsTerm(func=m1_last_action, noise=None)
        wheel_vel = ObsTerm(func=m1_wheel_surface_velocity, noise=None)
        joint_pos = ObsTerm(func=m1_joint_pos_rel, params={"asset_cfg": SceneEntityCfg("robot", joint_names=list(M1_PLANNER_JOINT_NAMES), preserve_order=True)}, noise=None)
        joint_vel = ObsTerm(func=m1_joint_vel_rel, params={"asset_cfg": SceneEntityCfg("robot", joint_names=list(M1_PLANNER_JOINT_NAMES), preserve_order=True)}, noise=None)
    @configclass
    class CriticStateCfg(PolicyStateCfg):
        base_lin_vel = ObsTerm(func=__import__("isaaclab.envs", fromlist=["mdp"]).mdp.base_lin_vel, noise=None)
    policy_state: PolicyStateCfg = PolicyStateCfg()
    critic_state: CriticStateCfg = CriticStateCfg()

@configclass
class M1AmeTerminationsCfg(TeacherElevationTrajectoryMpcSemanticTerminationsCfg):
    nonfinite_robot_state = DoneTerm(
        func=nonfinite_robot_state,
        params={"asset_cfg": SceneEntityCfg("robot")},
    )


@configclass
class M1AmeRewardsCfg(CrossLargeComplexPpoRewardsCfg):
    # Rolling over a step need not include 0.5s of flight. Shape only actual
    # semantic1-local progress/lift; all existing collision terms stay active.
    feet_air_time = None
    air_time_variance = None
    small_obstacle_progress = RewTerm(
        func=m1_obstacle_rewards.m1_small_obstacle_progress, weight=1.0,
        params={"command_name": "base_velocity"},
    )
    small_obstacle_climb = RewTerm(
        # Strong pre-contact shaping encourages an actual early swing. This
        # remains distinct from strict success, which still requires 5 cm
        # wheel-bottom clearance and stable post-obstacle touchdown.
        func=m1_obstacle_rewards.m1_small_obstacle_climb, weight=1.5,
        params={"command_name": "base_velocity"},
    )
    small_obstacle_corridor = RewTerm(
        # Do not let the policy solve a small centerline crossing by taking a
        # large lateral detour; the large-obstacle branch remains available
        # for genuine side-step avoidance.
        func=m1_obstacle_rewards.m1_small_obstacle_corridor_penalty,
        weight=-1.0,
        params={"command_name": "base_velocity"},
    )
    joint_vel = RewTerm(func=m1_rewards.m1_joint_vel_l2, weight=-0.001)
    # Stronger upright shaping plus an explicit one-step reset penalty keep
    # falling from being rewarded by a shorter episode.
    flat_orientation_l2 = RewTerm(func=isaac_mdp.flat_orientation_l2, weight=-4.0)
    failure_termination = RewTerm(func=m1_rewards.m1_failure_termination_penalty, weight=-20.0)
    joint_acc = RewTerm(func=m1_rewards.m1_joint_acc_l2, weight=-2.5e-7)
    joint_torques = RewTerm(func=m1_rewards.m1_joint_torques_l2, weight=-2e-4)
    action_rate = RewTerm(func=m1_rewards.m1_action_rate_l2, weight=-0.1)
    energy = RewTerm(func=m1_rewards.m1_energy, weight=-2e-5)
    dof_pos_limits = RewTerm(
        func=m1_rewards.m1_joint_pos_limits, weight=-10.0,
        params={"asset_cfg": SceneEntityCfg("robot", joint_names=list(M1_PLANNER_JOINT_NAMES), preserve_order=True)},
    )
    joint_pos = RewTerm(
        func=m1_rewards.m1_joint_position_penalty, weight=-0.7,
        params={"asset_cfg": SceneEntityCfg("robot", joint_names=list(M1_PLANNER_JOINT_NAMES), preserve_order=True),
                "stand_still_scale": 5.0, "velocity_threshold": 0.3},
    )
    parallelism_geometry_collision = RewTerm(
        func=m1_obstacle_rewards.m1_obstacle_collision_penalty, weight=-10.0,
        params={"asset_cfg": SceneEntityCfg("robot"), "scanner_cfg": SceneEntityCfg("semantic_height_scanner")},
    )
    non_support_obstacle_contact = RewTerm(
        func=m1_obstacle_rewards.m1_non_support_obstacle_contact, weight=-8.0,
        params={"sensor_cfg": SceneEntityCfg("contact_forces"), "command_name": "base_velocity"},
    )
    feet_slide = RewTerm(
        func=m1_rewards.m1_wheel_rolling_residual_l2, weight=-0.1,
        params={"asset_cfg": SceneEntityCfg("robot", body_names=list(m1_rewards.M1_SUPPORT_BODY_NAMES), preserve_order=True),
                "sensor_cfg": SceneEntityCfg("contact_forces", body_names=list(m1_rewards.M1_SUPPORT_BODY_NAMES), preserve_order=True)},
    )


@configclass
class M1AmeCrossLargeComplexEnvCfg(AmeCrossLargeComplexEnvCfg):
    robot_name: str = "m1"
    action_dim: int = 16
    asset_joint_names: tuple[str, ...] = M1_ASSET_JOINT_NAMES
    planner_joint_names: tuple[str, ...] = M1_PLANNER_JOINT_NAMES
    wheel_joint_names: tuple[str, ...] = M1_WHEEL_JOINT_NAMES
    wheel_radius_m: float = M1_WHEEL_RADIUS_M
    wheel_thickness_m: float = M1_WHEEL_THICKNESS_M
    wheel_horizontal_envelope_m: float = M1_WHEEL_HORIZONTAL_ENVELOPE_M
    # Keep the reset contract identical to M1_CFG/checkpoint_602.  The
    # centered-wheel training pose is useful for a fresh policy but makes an
    # existing locomotion checkpoint fall immediately.
    # Keep the checkpoint's supported stance.  M1_ROOT_Z_M is the centered
    # wheel pose used by the fresh asset; model_600 was trained with the
    # taller -0.573 rad hip stance below.
    root_z_m: float = M1_TRAINING_ROOT_Z_M
    wheel_action_scale: float = M1_WHEEL_ACTION_SCALE_RAD_S
    actions: M1AmeActionsCfg = M1AmeActionsCfg()
    observations: M1AmeObservationsCfg = M1AmeObservationsCfg()
    rewards: M1AmeRewardsCfg = M1AmeRewardsCfg()
    terminations: M1AmeTerminationsCfg = M1AmeTerminationsCfg()
    def __post_init__(self):
        super().__post_init__()
        # M1 training uses one fixed six-obstacle course.  The inherited
        # terrain-level curriculum can move environments onto rows with a
        # different obstacle exposure, starving the MPC teacher and turning
        # the task into ordinary flat locomotion.
        # Preserve the locomotion checkpoint's terrain-level curriculum while
        # overriding only the semantic obstacle counts/layout below.  Disabling
        # this inherited curriculum puts old policies on an unseen terrain
        # distribution and causes early posture collapse.
        # M1 crossing teacher must visibly lift the swing leg before small
        # obstacles instead of grazing them. Keep this in the sole effective
        # post-init method so later definitions cannot shadow it.
        self.mpc_planner_cfg.runtime.robot_name = "m1"
        # M1 must approach obstacles instead of spending most rollouts at a
        # near-zero command. Keep a narrow lateral/yaw band for stability while
        # making the forward command large enough to trigger the crossing MPC.
        # Keep the checkpoint-compatible command distribution for the first
        # adaptation stage.  A later command curriculum widens forward speed
        # after the gait is stable; jumping directly to 0.18--0.45 m/s makes
        # model_602 fall before it can learn the obstacle phase.
        self.commands.base_velocity.ranges.lin_vel_x = (-0.10, 0.10)
        self.commands.base_velocity.ranges.lin_vel_y = (-0.10, 0.10)
        self.commands.base_velocity.ranges.ang_vel_z = (-1.0, 1.0)
        self.commands.base_velocity.limit_ranges.lin_vel_x = (-1.0, 1.0)
        self.commands.base_velocity.limit_ranges.lin_vel_y = (-0.5, 0.5)
        self.commands.base_velocity.limit_ranges.ang_vel_z = (-1.0, 1.0)
        self.commands.base_velocity.rel_standing_envs = 0.10
        obstacle_stage_for_speed = os.environ.get("M1_OBSTACLE_STAGE", "full").strip().lower()
        if obstacle_stage_for_speed != "none":
            # Obstacle stages must actually reach the course; near-zero
            # commands leave the 1.20 m first block outside the scanner.
            default_speed = (
                (0.05, 0.15) if obstacle_stage_for_speed in {"warmup", "two"}
                else (0.18, 0.45)
            )
            speed_min = float(os.environ.get("M1_FORWARD_SPEED_MIN", default_speed[0]))
            speed_max = float(os.environ.get("M1_FORWARD_SPEED_MAX", default_speed[1]))
            if speed_min < 0.0 or speed_max < speed_min:
                raise ValueError("M1_FORWARD_SPEED_MIN/MAX must satisfy 0 <= min <= max")
            self.commands.base_velocity.ranges.lin_vel_x = (speed_min, speed_max)
            # The authored crossing course is a straight world +X lane.
            # Random lateral/yaw commands make a straight-wheel teacher leave
            # the lane and turn obstacle contacts into orientation failures;
            # side avoidance is trained separately in the large-obstacle stage.
            if os.environ.get("M1_ALLOW_COURSE_LATERAL_COMMANDS", "0").strip().lower() in {"1", "true", "yes"}:
                self.commands.base_velocity.ranges.lin_vel_y = (-0.04, 0.04)
                self.commands.base_velocity.ranges.ang_vel_z = (-0.15, 0.15)
            else:
                self.commands.base_velocity.ranges.lin_vel_y = (0.0, 0.0)
                self.commands.base_velocity.ranges.ang_vel_z = (0.0, 0.0)
        # The semantic course is authored in the tile/world +X direction.
        # Keep M1 episodes at its protected start pose; inheriting the generic
        # +/-pi yaw reset makes the forward scanner face away from all six
        # fixed obstacles in most rollouts and starves the MPC teacher.
        if os.environ.get("M1_OBSTACLE_STAGE", "full").strip().lower() == "none":
            # Preserve the checkpoint's locomotion reset distribution during
            # the no-obstacle adaptation stage.
            self.events.reset_base.params["pose_range"] = {
                "x": (-0.5, 0.5), "y": (-0.5, 0.5), "yaw": (-3.14, 3.14),
            }
        else:
            # The authored course is +X; crossing stages must face it.
            self.events.reset_base.params["pose_range"] = {
                "x": (0.0, 0.0), "y": (0.0, 0.0), "yaw": (0.0, 0.0),
            }
        # M1 training refreshes every environment so semantic obstacle rows are not skipped by the parent batch setting.
        self.mpc_planner_cfg.runtime.parallel_plan_batch_size = int(self.scene.num_envs)
        # A 16-frame horizon gave each sequential leg only ~4 control frames;
        # the wheel never reached the IK clearance target before the planner
        # returned to stance.  Reserve 8 frames per leg and keep replanning
        # synchronized with the full serial crossing pass.
        # The M1 wheel needs several slew-limited frames to reach the
        # 0.6--0.8 rad IK lift.  Give each of the four serial legs a 16-frame
        # quarter instead of ending the arc after eight frames.
        self.mpc_planner_cfg.runtime.horizon_steps = 64
        # A replan resets the cached phase counter.  Replanning at the same
        # 32-frame horizon therefore restarted leg 0 every time and never
        # let the serial M1 swing reach legs 1/2.  Keep one complete
        # four-leg crossing pass alive before refreshing from the next
        # obstacle; the teacher latch remains active between replans.
        self.mpc_planner_cfg.runtime.replan_interval_steps = 128
        self.mpc_planner_cfg.runtime.nominal_swing_height_m = 0.30
        self.mpc_planner_cfg.runtime.foot_contact_offset_m = M1_WHEEL_RADIUS_M
        # The semantic course boxes are rigid objects and therefore do not
        # raise the scanner terrain height map.  Pass their physical heights
        # to the classifier/teacher so the wheel target includes the true
        # obstacle top plus the required clearance.
        small_obstacle_height_m = float(os.environ.get(
            "M1_SMALL_OBSTACLE_HEIGHT_M", str(M1_DEFAULT_SMALL_OBSTACLE_HEIGHT_M),
        ))
        if not 0.03 <= small_obstacle_height_m <= 0.16:
            raise ValueError("M1_SMALL_OBSTACLE_HEIGHT_M must be in [0.03, 0.16]")
        self.mpc_planner_cfg.runtime.semantic_small_obstacle_height_m = small_obstacle_height_m
        self.mpc_planner_cfg.runtime.semantic_large_obstacle_height_m = 0.55
        # The generic Go2 planner's 6 cm semantic clearance is insufficient
        # for the M1 wheel/knee geometry after inverse-kinematics projection:
        # PhysX measured only ~2 cm above a 10 cm block. Keep this override
        # M1-specific so generic MPC contracts retain their defaults while
        # the crossing course asks for visible 5 cm top clearance.
        self.mpc_planner_cfg.runtime.low_small_swing_clearance_m = 0.16
        self.mpc_planner_cfg.runtime.low_small_swing_clearance_max_m = 0.26
        self.mpc_planner_cfg.runtime.low_small_swing_height_lower_step_m = 0.28
        self.mpc_planner_cfg.runtime.continuous_low_small_crossing_arc_lift_step_m = 0.18
        # The wheel can clear the block while the knee/calf envelope still
        # scrapes it.  Raise the M1 body-leg clearance constraints separately
        # from the wheel-top clearance so the MPC trajectory lifts the whole
        # linkage, not only the wheel endpoint.
        self.mpc_planner_cfg.runtime.body_leg_semantic_clearance_m = 0.24
        self.mpc_planner_cfg.runtime.body_leg_root_lift_margin_m = 0.14
        self.mpc_planner_cfg.runtime.body_leg_root_lift_max_m = 0.28
        if hasattr(self.mpc_planner_cfg.losses, "fk_body_leg_collision"):
            self.mpc_planner_cfg.losses.fk_body_leg_collision.knee_margin_m = 0.08
            self.mpc_planner_cfg.losses.fk_body_leg_collision.shank_margin_m = 0.08
        if hasattr(self.mpc_planner_cfg.losses, "leg_collision"):
            self.mpc_planner_cfg.losses.leg_collision.knee_margin_m = 0.08
            self.mpc_planner_cfg.losses.leg_collision.shank_margin_m = 0.08
        # Do not use a global root-height target: it destabilizes the learned
        # checkpoint. Instead allow the semantic crossing branch to request a
        # genuinely high arc; the generic 0.18 m cap was below the M1 wheel
        # clearance needed for a 10 cm block.
        self.mpc_planner_cfg.losses.low_small_crossing.max_crossing_height_m = 0.22
        self.mpc_planner_cfg.losses.low_small_crossing.pass_margin_m = 0.08
        self.mpc_planner_cfg.losses.low_small_foot_crossing.soft_margin_m = 0.35
        self.mpc_planner_cfg.losses.swing_foot_clearance.swing_foot_clearance_margin_m = 0.05
        # The 2.0 m forward scanner gives the teacher a full pre-lift horizon
        # before the M1 wheel envelope reaches the first 10 cm block.
        self.mpc_planner_cfg.losses.low_small_crossing.forward_distance_m = 1.8
        self.mpc_planner_cfg.losses.obstacle_risk.linear_forward_distance_m = 1.8
        self.mpc_planner_cfg.losses.high_obstacle_avoidance.forward_distance_m = 1.8
        self.mpc_planner_cfg.losses.swing_clearance_terrain.min_clearance_m = 0.22
        # M1 uses 10 cm semantic obstacles. The generic Go2 course keeps its
        # historical profile; this override is applied only to the M1 terrain.
        self.scene.terrain.semantic_course_scale_profile_overrides = {
            # Keep the required 10 cm height, but leave a narrow 5 cm
            # footprint so the serial wheel lift is not defeated by a side
            # scrape from the M1 knee/calf envelope.
            "small": (M1_SMALL_OBSTACLE_DIAMETER_M, small_obstacle_height_m),
            "large": (0.45, 0.55),
        }
        self.scene.terrain.semantic_course_layout_cfg = SemanticCourseLayoutCfg(
            small_shape_pool=("cuboid", "cylinder"),
            tile_margin_m=0.50,
            center_safety_half_extent_m=0.45,
            center_safety_radius_m=None,
            fixed_small_obstacle_local_xy=M1_FIXED_SMALL_OBSTACLE_LOCAL_XY,
            fixed_large_obstacle_local_xy=(
                () if os.environ.get("M1_OBSTACLE_STAGE", "full").strip().lower()
                in {"small", "small_only"}
                else M1_FIXED_LARGE_OBSTACLE_LOCAL_XY
            ),
            min_spacing_clearance_m=0.45,
        )
        # The shared course embeds geometry by 1.5 cm and its sphere ignores
        # target_height. M1 acceptance needs *exposed* 10 cm geometry, not an
        # 8.5 cm box or 5 cm sphere with a misleading 10 cm config label.
        self.scene.terrain.semantic_course_grounding_cfg = SemanticCourseGroundingCfg(
            embed_depth_m=0.0,
        )
        # More repeated crossing attempts, while leaving a protected reset and
        # touchdown corridor for the M1 wheel footprint.
        # Train in explicit obstacle stages.  A locomotion checkpoint cannot
        # be dropped directly into a six-block course: it falls at the first
        # block before PPO has learned the one-leg swing.  The stage is chosen
        # at process start, so each stage has deterministic geometry and can
        # be resumed from the previous checkpoint.
        obstacle_stage = os.environ.get("M1_OBSTACLE_STAGE", "full").strip().lower()
        # This M1 task uses the authored semantic course, not the inherited
        # Go2 terrain-level curriculum.  In particular, the ``none`` stage is
        # the flat locomotion gate: leaving the parent terrain curriculum
        # enabled silently advances environments onto rough rows (the
        # ``mean_terrain_level`` metric then rises) and makes a fresh policy
        # appear to fail before obstacle logic is even exercised.  All stages
        # therefore stay on the fixed plane/course selected below.
        self.curriculum.terrain_levels = None
        if obstacle_stage == "none":
            stage_small, stage_large = 0, 0
        elif obstacle_stage in {"warmup", "two"}:
            stage_small, stage_large = 2, 0
        elif obstacle_stage in {"small", "small_only"}:
            # Physical crossing gate: expose the complete six-block serial
            # course without side large obstacles masking the teacher.  The
            # full stage restores the two large obstacles for avoidance.
            stage_small, stage_large = 6, 0
        else:
            stage_small, stage_large = 6, 0
        self.semantic_obstacle_curriculum.terrain_obstacle_count_overrides.update({
            # Increase repeated 10 cm crossing opportunities while keeping the
            # protected reset/touchdown corridor and 0.56 m inter-obstacle
            # pitch below. Large obstacles remain sparse so the policy
            # learns crossing on small blocks instead of unsafe contacts.
            "flat_dense_small_obstacles": SemanticObstacleCount(small=stage_small, large=stage_large),
            "flat": SemanticObstacleCount(small=stage_small, large=stage_large),
        })
        self.semantic_obstacle_curriculum.plane_counts = (
            SemanticObstacleCount(small=stage_small, large=stage_large),
        )
        non_plane_large = 2 if obstacle_stage == "full" else stage_large
        self.semantic_obstacle_curriculum.non_plane_counts = (
            SemanticObstacleCount(small=stage_small, large=non_plane_large),
        )
        self.semantic_obstacle_curriculum.center_safety_half_extent_m = (0.45,)
        self.semantic_obstacle_curriculum.min_spacing_clearance_m = (0.45,)
        self.semantic_obstacle_curriculum.tile_margin_m = (0.50,)
        # Rebind after the parent post-init copied its own curriculum into the terrain importer.
        self.scene.terrain.semantic_obstacle_curriculum = self.semantic_obstacle_curriculum
        self.robot_name = "m1"
        self.action_dim = 16
        self.asset_joint_names = M1_ASSET_JOINT_NAMES
        self.planner_joint_names = M1_PLANNER_JOINT_NAMES
        self.wheel_joint_names = M1_WHEEL_JOINT_NAMES
        self.scene.robot = M1_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        # The supplied USD has an enabled world-to-root fixed joint.
        # Locomotion training must release it; the source viewer asset is intact.
        self.scene.robot.spawn.articulation_props.fix_root_link = False
        self.scene.robot.spawn.func = spawn_m1_floating_usd
        actuator = self.scene.robot.actuators["all_joints"]
        self.scene.robot.actuators = {
            # High support gains keep the floating M1's three loaded wheels
            # under the body while a fourth wheel is unloaded.  Lower gains
            # let the root sag and invalidate the serial crossing sequence.
            "legs": actuator.replace(
                joint_names_expr=list(M1_PLANNER_JOINT_NAMES),
                stiffness=float(os.environ.get("M1_LEG_STIFFNESS", "800.0")),
                damping=float(os.environ.get("M1_LEG_DAMPING", "40.0")),
            ),
            "wheels": actuator.replace(
                joint_names_expr=list(M1_WHEEL_JOINT_NAMES), stiffness=0.0,
                # Velocity-servo gain, not passive rolling resistance. The
                # 0.5 default stalls under M1 load; 5.0 passes the rolling gate
                # without changing the USD's 50 Nm wheel effort limit.
                damping=5.0, velocity_limit_sim=M1_WHEEL_SPEED_LIMIT_RAD_S,
            ),
        }
        # AME does not use semantic obstacle contact sensors.
        self.scene.semantic_contact_small = None
        self.scene.semantic_contact_large = None
        # Keep the inherited CrossLargeComplex terrain curriculum active.  AME
        # uses map observations for policy input, while curriculum progression
        # still moves environments through the configured terrain levels.
        if hasattr(self.rewards, "semantic_contact_collision"):
            self.rewards.semantic_contact_collision = None
        # Rebind the inherited scanner to the M1 root body name.
        if self.scene.semantic_height_scanner is not None:
            self.scene.semantic_height_scanner.prim_path = "{ENV_REGEX_NS}/Robot/BASE_LINK"
        # Keep the policy head at 16 actions, with an explicit M1 asset order.
        self.actions.JointPositionAction.joint_names = list(M1_ASSET_JOINT_NAMES)
        self.scene.robot.init_state.pos = (0.0, 0.0, M1_TRAINING_ROOT_Z_M)
        self.scene.robot.init_state.joint_pos = dict(zip(M1_ASSET_JOINT_NAMES, M1_TRAINING_JOINT_POS))
        # Only successful, non-terminated episodes may increase command
        # difficulty; the underlying terrain curriculum already gates on the
        # same episode-success signals.
        self.curriculum.lin_vel_cmd_levels.params["require_success"] = True
        # The M1 USD names its root body BASE_LINK.
        for term_name in ("add_base_mass", "base_external_force_torque"):
            term = getattr(self.events, term_name, None)
            if term is not None:
                term.params["asset_cfg"].body_names = "BASE_LINK"
        if self.terminations.base_contact is not None:
            self.terminations.base_contact.params["sensor_cfg"].body_names = "BASE_LINK"
        # M1 uses upper-case link names for all four wheel/foot bodies.
        m1_foot_pattern = list(m1_rewards.M1_SUPPORT_BODY_NAMES)
        if self.rewards.undesired_contacts is not None:
            self.rewards.undesired_contacts.params["sensor_cfg"].body_names = [
                ".*_ABAD_LINK", ".*_HIP_LINK", ".*_KNEE_LINK"
            ]
        for term_name in ("feet_air_time", "air_time_variance", "feet_slide"):
            term = getattr(self.rewards, term_name, None)
            if term is not None:
                for key in ("sensor_cfg", "contact_sensor_cfg"):
                    if key in term.params:
                        term.params[key].body_names = m1_foot_pattern
                        term.params[key].preserve_order = True
                if "asset_cfg" in term.params:
                    term.params["asset_cfg"].body_names = m1_foot_pattern
                    term.params["asset_cfg"].preserve_order = True
        self.experiment_name = "m1_cross_large_complex_ame"
        # The online MPC teacher owns and refreshes the reference cache.
        self.planner_owned_reference_cache = True
        self.use_batched_reference_trajectory = True
        self.planner_backend = "mpc"

__all__ = [
    "M1AmeCrossLargeComplexEnvCfg",
    "M1AmeObservationsCfg",
    "M1AmeTerminationsCfg",
    "build_m1_policy_joint_terms",
    "m1_joint_pos_rel",
    "m1_joint_vel_rel",
]
