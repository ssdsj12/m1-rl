"""Read-only, simulator-import-free extraction for the independent teacher."""
import torch

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES,
)
from extension.parallelism.rl_adapter import resolve_named_indices
from .m1_required_crossing import progressive_required_wheels
from .m1_reference_teacher import TeacherState

WHEEL_BODY_NAMES = tuple(name.replace('_JOINT', '_LINK') for name in M1_WHEEL_JOINT_NAMES)


class ReferenceTeacherAdapter:
    """Does not step physics, update trackers, modify observations or own resets.

    Lifecycle tensors are mandatory to avoid reconstructing an old terminal
    state from new reset poses. The caller must use pre-reset snapshots for
    terminal evaluation and mark post-reset rows; the wrapper clears receipts
    on done rows before its next observation. No missing signal is guessed.
    """
    def __init__(self, wrapper):
        self.wrapper = wrapper

    @torch.no_grad()
    def snapshot(self, *, control_step, episode_id, reset_mask, collision):
        env = self.wrapper.unwrapped
        robot, sensor = env.scene['robot'], env.scene['contact_forces']
        data = robot.data
        course = self.wrapper._m1_current_course()
        source = tuple(robot.joint_names)
        legs = list(resolve_named_indices(source, M1_PLANNER_JOINT_NAMES))
        assets = list(resolve_named_indices(source, M1_ASSET_JOINT_NAMES))
        wheels = list(resolve_named_indices(tuple(robot.body_names), WHEEL_BODY_NAMES))
        contacts = list(resolve_named_indices(tuple(sensor.body_names), WHEEL_BODY_NAMES))
        b = data.root_pos_w.shape[0]
        nominal_z = data.default_root_state[:,2]+env.scene.env_origins[:,2]
        state = TeacherState(
            root_pos_w=data.root_pos_w.clone(), root_quat_w=data.root_quat_w.clone(),
            root_lin_vel_w=data.root_lin_vel_w.clone(), root_ang_vel_w=data.root_ang_vel_w.clone(),
            leg_pos=data.joint_pos[:,legs].clone(), default_joint_pos=data.default_joint_pos[:,assets].clone(),
            wheel_pos_w=data.body_pos_w[:,wheels].clone(), wheel_quat_w=data.body_quat_w[:,wheels].clone(),
            wheel_force_w=sensor.data.net_forces_w[:,contacts].clone(),
            centers_top=course['centers_top'].clone(), half_extents=course['half_extents'].clone(),
            ground_z=course['ground_z'].clone(), course_valid=course['valid'].clone(), course_ids=course['ids'].clone(),
            required_wheels=progressive_required_wheels(course, env.scene.env_origins[:,1]).clone(),
            recovered=self.wrapper._m1_strict_crossing.recovered_for_course(course).clone(),
            nominal_root_z_w=nominal_z.clone(), dt=data.root_pos_w.new_full((b,), float(env.step_dt)),
            reset_mask=reset_mask.clone(), episode_id=episode_id.clone(), control_step=control_step.clone(),
            collision=collision.clone())
        state.validate()
        return state
