"""M1 mixed drive action, preserving the documented 16-column asset order."""
from isaaclab.envs.mdp.actions.joint_actions import JointAction
from isaaclab.envs.mdp.actions.actions_cfg import JointActionCfg
from isaaclab.utils import configclass

from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES
from extension.parallelism.rl_adapter import resolve_named_indices
from .m1_ame_contract import m1_action_targets


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
