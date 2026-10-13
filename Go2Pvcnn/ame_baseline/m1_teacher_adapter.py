"""Read-only, simulator-import-free extraction for the independent teacher."""
import torch

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES,
)
from extension.parallelism.rl_adapter import resolve_named_indices
from .m1_required_crossing import progressive_required_wheels
from .m1_reference_teacher import TeacherState
from .m1_teacher_measurements import mass_weighted_com

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
    def snapshot(self, *, control_step, episode_id, reset_mask, collision,
                 last_applied_leg_target, applied_target_valid,
                 applied_leg_joint_names=M1_PLANNER_JOINT_NAMES):
        """Applied targets are explicit [B,12] radians in the supplied leg order.

        The default order is planner names; callers extracting 16 applied targets
        must select legs by name first. Missing execution evidence is never guessed.
        """
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
        target_names = tuple(applied_leg_joint_names)
        if len(target_names) != 12 or set(target_names) != set(M1_PLANNER_JOINT_NAMES):
            raise ValueError('applied_leg_joint_names must name all 12 legs exactly once')
        target_ids = list(resolve_named_indices(target_names, M1_PLANNER_JOINT_NAMES))
        if (not isinstance(last_applied_leg_target, torch.Tensor)
                or last_applied_leg_target.shape != (b,12)
                or last_applied_leg_target.device != data.root_pos_w.device
                or not last_applied_leg_target.is_floating_point()):
            raise ValueError('last_applied_leg_target has invalid shape, device or dtype')
        if (not isinstance(applied_target_valid, torch.Tensor)
                or applied_target_valid.shape != (b,) or applied_target_valid.dtype != torch.bool
                or applied_target_valid.device != data.root_pos_w.device):
            raise ValueError('applied_target_valid must be bool [B] on measurement device')
        body_names = tuple(robot.body_names)
        if len(set(body_names)) != len(body_names):
            raise ValueError('duplicate articulation body names')
        # Absent COM buffers are invalid evidence, rather than a root-position proxy.
        body_com = getattr(data, 'body_com_pos_w', None)
        mass_view = getattr(robot, 'root_physx_view', None)
        if body_com is None or mass_view is None or not hasattr(mass_view, 'get_masses'):
            com = data.root_pos_w.new_full((b,3), float('nan'))
            measured = torch.zeros(b, dtype=torch.bool, device=data.root_pos_w.device)
        else:
            masses = mass_view.get_masses()
            if (not isinstance(body_com, torch.Tensor)
                    or body_com.shape != (b,len(body_names),3)
                    or body_com.device != data.root_pos_w.device
                    or not body_com.is_floating_point()):
                raise ValueError('body_com_pos_w has invalid articulation body shape, device or dtype')
            if (not isinstance(masses, torch.Tensor)
                    or masses.shape != (b,len(body_names)) or not masses.is_floating_point()):
                raise ValueError('masses have invalid articulation body shape or dtype')
            # PhysX may expose CPU masses beside device-local body COM buffers.
            # Normalize this boundary only; the pure function remains strict.
            com, measured = mass_weighted_com(body_com, masses.to(body_com))
        applied = last_applied_leg_target[:,target_ids].clone()
        nominal_z = data.default_root_state[:,2]+env.scene.env_origins[:,2]
        state = TeacherState(
            root_pos_w=data.root_pos_w.clone(), root_quat_w=data.root_quat_w.clone(),
            com_pos_w=com.clone(), measurement_valid=measured.clone(),
            last_applied_leg_target=applied,
            applied_target_valid=applied_target_valid.clone() & torch.isfinite(applied).all(-1),
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
        # Check measured floating buffers row-locally, including quaternion norms.
        for value in (state.root_pos_w, state.root_quat_w, state.root_lin_vel_w,
                      state.root_ang_vel_w, state.leg_pos, state.default_joint_pos,
                      state.wheel_pos_w, state.wheel_quat_w, state.wheel_force_w):
            state.measurement_valid.logical_and_(torch.isfinite(value).reshape(b,-1).all(-1))
        state.measurement_valid.logical_and_((state.root_quat_w.norm(dim=-1)-1).abs() <= 1e-3)
        state.measurement_valid.logical_and_(((state.wheel_quat_w.norm(dim=-1)-1).abs() <= 1e-3).all(-1))
        return state
