"""M1 mixed drive action, preserving the documented 16-column asset order."""
from isaaclab.envs.mdp.actions.joint_actions import JointAction
from isaaclab.envs.mdp.actions.actions_cfg import JointActionCfg
from isaaclab.utils import configclass

from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES
from extension.parallelism.rl_adapter import resolve_named_indices
from .m1_ame_contract import m1_action_targets, expand_fixed_wheel_actions, validate_fixed_wheel_speed


class M1MixedJointAction(JointAction):
    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        if tuple(self._joint_names) != M1_ASSET_JOINT_NAMES:
            raise ValueError("M1 mixed action must preserve the explicit 16-joint order")
        self._leg_columns = list(resolve_named_indices(self._joint_names, M1_PLANNER_JOINT_NAMES))
        self._wheel_columns = list(resolve_named_indices(self._joint_names, M1_WHEEL_JOINT_NAMES))
        self._leg_ids = [self._joint_ids[i] for i in self._leg_columns]
        self._wheel_ids = [self._joint_ids[i] for i in self._wheel_columns]
        self._default_pos = self._asset.data.default_joint_pos[:, self._joint_ids].clone()

    def process_actions(self, actions):
        self._raw_actions[:] = actions
        self._processed_actions[:] = m1_action_targets(actions, self._default_pos)

    def apply_actions(self):
        self._asset.set_joint_position_target(self.processed_actions[:, self._leg_columns], joint_ids=self._leg_ids)
        self._asset.set_joint_velocity_target(self.processed_actions[:, self._wheel_columns], joint_ids=self._wheel_ids)


@configclass
class M1MixedJointActionCfg(JointActionCfg):
    class_type: type = M1MixedJointAction
    joint_names: list[str] = list(M1_ASSET_JOINT_NAMES)
    preserve_order: bool = True


@configclass
class M1AmeActionsCfg:
    JointPositionAction = M1MixedJointActionCfg(asset_name="robot")


class M1FixedWheelLegAction(JointAction):
    """Twelve policy actions; wheel velocity targets are not policy outputs."""
    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        if tuple(self._joint_names) != M1_PLANNER_JOINT_NAMES:
            raise ValueError("Fixed-wheel action requires the explicit 12-leg order")
        self._fixed_speed = validate_fixed_wheel_speed(cfg.fixed_wheel_speed_m_s)
        asset_ids = list(resolve_named_indices(self._asset.joint_names, M1_ASSET_JOINT_NAMES))
        self._wheel_ids = list(resolve_named_indices(self._asset.joint_names, M1_WHEEL_JOINT_NAMES))
        self._leg_columns = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
        self._wheel_columns = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES))
        self._default_asset_pos = self._asset.data.default_joint_pos[:, asset_ids].clone()
        self._default_pos = self._default_asset_pos[:, self._leg_columns].clone()
        executed = expand_fixed_wheel_actions(self._raw_actions, self._fixed_speed)
        self._fixed_wheel_targets = m1_action_targets(executed, self._default_asset_pos)[:, self._wheel_columns].clone()

    def targets_for_actions(self, actions):
        executed = expand_fixed_wheel_actions(actions, self._fixed_speed)
        return m1_action_targets(executed, self._default_asset_pos)[:, self._leg_columns]

    def process_actions(self, actions):
        targets = self.targets_for_actions(actions)
        self._raw_actions[:] = actions
        self._processed_actions[:] = targets

    def apply_actions(self):
        self._asset.set_joint_position_target(self.processed_actions, joint_ids=self._joint_ids)
        self._asset.set_joint_velocity_target(self._fixed_wheel_targets, joint_ids=self._wheel_ids)


@configclass
class M1FixedWheelLegActionCfg(JointActionCfg):
    class_type: type = M1FixedWheelLegAction
    joint_names: list[str] = list(M1_PLANNER_JOINT_NAMES)
    preserve_order: bool = True
    fixed_wheel_speed_m_s: float = .30


def configure_fixed_wheel_control(cfg, speed_m_s):
    speed = validate_fixed_wheel_speed(speed_m_s)
    if (getattr(cfg, 'planner_owned_reference_cache', False)
            or getattr(cfg, 'use_batched_reference_trajectory', False)
            or getattr(cfg, 'planner_backend', None) is not None):
        raise ValueError('Fixed-wheel PPO cannot share action ownership with a planner')
    cfg.m1_fixed_wheel_speed_m_s = speed
    cfg.m1_fixed_abad = False
    cfg.action_dim = 12
    cfg.actions.JointPositionAction = M1FixedWheelLegActionCfg(asset_name='robot', fixed_wheel_speed_m_s=speed)
    command = cfg.commands.base_velocity
    for ranges in (command.ranges, command.limit_ranges):
        ranges.lin_vel_x = (speed, speed)
        ranges.lin_vel_y = (0., 0.)
        ranges.ang_vel_z = (0., 0.)
    command.rel_standing_envs = 0.
    command.heading_command = False
    cfg.curriculum.lin_vel_cmd_levels = None


from .m1_fixed_abad import M1_HIP_KNEE_JOINT_NAMES, M1_ABAD_JOINT_NAMES, expand_fixed_abad_actions


class M1FixedAbadHipKneeAction(JointAction):
    """Eight stochastic outputs; ABAD uses fixed targets, not physical locks."""
    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        if tuple(self._joint_names) != M1_HIP_KNEE_JOINT_NAMES:
            raise ValueError('Fixed ABAD requires explicit eight HIP/KNEE joint order')
        self._fixed_speed = validate_fixed_wheel_speed(cfg.fixed_wheel_speed_m_s)
        asset_ids = list(resolve_named_indices(self._asset.joint_names, M1_ASSET_JOINT_NAMES))
        self._leg_ids = list(resolve_named_indices(self._asset.joint_names, M1_PLANNER_JOINT_NAMES))
        self._wheel_ids = list(resolve_named_indices(self._asset.joint_names, M1_WHEEL_JOINT_NAMES))
        self._leg_columns = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
        self._policy_columns = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_HIP_KNEE_JOINT_NAMES))
        self._abad_columns = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_ABAD_JOINT_NAMES))
        self._default_asset_pos = self._asset.data.default_joint_pos[:, asset_ids].clone()
        self._default_asset_pos[:, self._abad_columns] = 0.
        self._default_pos = self._default_asset_pos[:, self._policy_columns].clone()
        initial = m1_action_targets(expand_fixed_abad_actions(self._raw_actions, self._fixed_speed), self._default_asset_pos)
        self._fixed_wheel_targets = initial[:, list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES))].clone()
        self._leg_targets = initial[:, self._leg_columns].clone()
        self._processed_actions[:] = initial[:, self._policy_columns]

    def targets_for_actions(self, actions):
        return m1_action_targets(expand_fixed_abad_actions(actions, self._fixed_speed),
                                 self._default_asset_pos)[:, self._policy_columns]

    def process_actions(self, actions):
        targets = m1_action_targets(expand_fixed_abad_actions(actions, self._fixed_speed), self._default_asset_pos)
        self._raw_actions[:] = actions
        self._processed_actions[:] = targets[:, self._policy_columns]
        self._leg_targets[:] = targets[:, self._leg_columns]

    def apply_actions(self):
        self._asset.set_joint_position_target(self._leg_targets, joint_ids=self._leg_ids)
        self._asset.set_joint_velocity_target(self._fixed_wheel_targets, joint_ids=self._wheel_ids)

    def reset(self, env_ids=None):
        ids = slice(None) if env_ids is None else env_ids
        self._raw_actions[ids] = 0.
        initial = m1_action_targets(expand_fixed_abad_actions(self._raw_actions, self._fixed_speed), self._default_asset_pos)
        self._processed_actions[ids] = initial[ids][:, self._policy_columns]
        self._leg_targets[ids] = initial[ids][:, self._leg_columns]


@configclass
class M1FixedAbadHipKneeActionCfg(JointActionCfg):
    class_type: type = M1FixedAbadHipKneeAction
    joint_names: list[str] = list(M1_HIP_KNEE_JOINT_NAMES)
    preserve_order: bool = True
    fixed_wheel_speed_m_s: float = .30


def configure_fixed_abad_control(cfg, speed_m_s):
    configure_fixed_wheel_control(cfg, speed_m_s)
    from .m1_ame_contract import m1_training_contract
    cfg.m1_fixed_abad = True
    cfg.action_dim = 8
    cfg.m1_training_contract = m1_training_contract(fixed_abad=True)
    cfg.actions.JointPositionAction = M1FixedAbadHipKneeActionCfg(asset_name='robot', fixed_wheel_speed_m_s=float(speed_m_s))
