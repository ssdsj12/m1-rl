"""M1 AME environment contract built on the existing AME scene."""
from __future__ import annotations
from isaaclab.utils import configclass
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import ObservationTermCfg as ObsTerm
from go2_pvcnn.assets.m1 import M1_CFG
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES, M1_ROOT_Z_M, M1_WHEEL_RADIUS_M, M1_WHEEL_THICKNESS_M, M1_WHEEL_HORIZONTAL_ENVELOPE_M
from extension.parallelism.rl_adapter import select_named_joint_state
from .ame_env_cfg import AmeCrossLargeComplexEnvCfg, AmeObservationsCfg

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
        joint_pos = ObsTerm(func=m1_joint_pos_rel, params={"asset_cfg": SceneEntityCfg("robot", joint_names=list(M1_PLANNER_JOINT_NAMES), preserve_order=True)}, noise=None)
        joint_vel = ObsTerm(func=m1_joint_vel_rel, params={"asset_cfg": SceneEntityCfg("robot", joint_names=list(M1_PLANNER_JOINT_NAMES), preserve_order=True)}, noise=None)
    @configclass
    class CriticStateCfg(PolicyStateCfg):
        base_lin_vel = ObsTerm(func=__import__("isaaclab.envs", fromlist=["mdp"]).mdp.base_lin_vel, noise=None)
    policy_state: PolicyStateCfg = PolicyStateCfg()
    critic_state: CriticStateCfg = CriticStateCfg()

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
    root_z_m: float = M1_ROOT_Z_M
    observations: M1AmeObservationsCfg = M1AmeObservationsCfg()
    def __post_init__(self):
        super().__post_init__()
        self.robot_name = "m1"
        self.action_dim = 16
        self.asset_joint_names = M1_ASSET_JOINT_NAMES
        self.planner_joint_names = M1_PLANNER_JOINT_NAMES
        self.wheel_joint_names = M1_WHEEL_JOINT_NAMES
        self.scene.robot = M1_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        # AME does not use semantic obstacle contact sensors.
        self.scene.semantic_contact_small = None
        self.scene.semantic_contact_large = None
        # Disable semantic-contact curriculum fallback; AME uses map observations only.
        self.curriculum.terrain_levels = None
        if hasattr(self.rewards, "semantic_contact_collision"):
            self.rewards.semantic_contact_collision = None
        # The inherited Go2 geometry collision term expects 12 joint inputs;
        # M1 AME uses its 16-D action contract and does not enable that term.
        self.rewards.parallelism_geometry_collision = None
        # Rebind the inherited scanner to the M1 root body name.
        if self.scene.semantic_height_scanner is not None:
            self.scene.semantic_height_scanner.prim_path = "{ENV_REGEX_NS}/Robot/BASE_LINK"
        # Keep the policy head at 16 actions, with an explicit M1 asset order.
        self.actions.JointPositionAction.joint_names = list(M1_ASSET_JOINT_NAMES)
        self.scene.robot.init_state.pos = (0.0, 0.0, M1_ROOT_Z_M)
        # The M1 USD names its root body BASE_LINK (the Go2 config uses base).
        for term_name in ("add_base_mass", "base_external_force_torque"):
            term = getattr(self.events, term_name, None)
            if term is not None:
                term.params["asset_cfg"].body_names = "BASE_LINK"
        if self.terminations.base_contact is not None:
            self.terminations.base_contact.params["sensor_cfg"].body_names = "BASE_LINK"
        # M1 uses upper-case link names for all four wheel/foot bodies.
        m1_foot_pattern = ".*_FOOT_LINK"
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
                if "asset_cfg" in term.params:
                    term.params["asset_cfg"].body_names = m1_foot_pattern
        self.experiment_name = "m1_cross_large_complex_ame"

__all__ = ["M1AmeCrossLargeComplexEnvCfg", "M1AmeObservationsCfg", "build_m1_policy_joint_terms", "m1_joint_pos_rel", "m1_joint_vel_rel"]