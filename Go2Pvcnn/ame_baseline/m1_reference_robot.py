"""Pinned bare-M1 physics, without the reference project's wave controller."""
from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES

REFERENCE_ROBOT_COMMIT = '8aeb845f73e39fd1e121758522ef05ee2378150f'


def configure_reference_robot(cfg, *, dc_motor_cls=None, implicit_cls=None):
    if dc_motor_cls is None or implicit_cls is None:
        from isaaclab.actuators import DCMotorCfg, ImplicitActuatorCfg
        dc_motor_cls, implicit_cls = DCMotorCfg, ImplicitActuatorCfg
    cfg.scene.robot.actuators = {
        'legs': dc_motor_cls(joint_names_expr=list(M1_PLANNER_JOINT_NAMES),
            effort_limit=150., saturation_effort=150., velocity_limit=20.,
            stiffness=120., damping=5.5, friction=0.),
        'wheels': implicit_cls(joint_names_expr=list(M1_WHEEL_JOINT_NAMES),
            effort_limit_sim=200., velocity_limit_sim=20., stiffness=0., damping=30., friction=0.),
    }
    props=cfg.scene.robot.spawn.articulation_props
    props.solver_position_iteration_count=4
    props.solver_velocity_iteration_count=2
    material=cfg.scene.terrain.physics_material
    material.static_friction=1.; material.dynamic_friction=1.; material.restitution=0.
    cfg.events.physics_material.params.update(static_friction_range=(1.,1.),
        dynamic_friction_range=(1.,1.),restitution_range=(0.,0.),num_buckets=8)
    cfg.events.add_base_mass=None
    cfg.events.reset_robot_joints.params.update(position_range=(1.,1.),velocity_range=(0.,0.))
