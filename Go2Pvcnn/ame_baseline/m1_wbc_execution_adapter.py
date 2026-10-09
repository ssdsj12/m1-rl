"""Single-owner M1 WBC torque handoff for an isolated diagnostic environment.

This adapter deliberately does not start/advance physics. The caller must
provide a fresh solver result and advance the simulator only after this
function has returned with verified native effort readback.
"""
import hashlib
import numpy as np


def support_damping_target(*, root_com_velocity, joint_velocity, gain=2.0,
                           linear_limit=0.5, angular_limit=2.0,
                           joint_limit=20.0):
    """Build a 22-DOF damping target in the dynamics adapter's coordinates.

    The floating-base coordinates start at the root COM, not the actor/root
    link origin. Using ``root_vel_w`` here mixes coordinate points whenever
    the root link COM is offset or the body rotates.
    """
    base = np.asarray(root_com_velocity, dtype=np.float64)
    joints = np.asarray(joint_velocity, dtype=np.float64)
    bounds = np.asarray([gain, linear_limit, angular_limit, joint_limit], dtype=np.float64)
    if (base.shape != (6,) or joints.shape != (16,) or not np.isfinite(base).all()
            or not np.isfinite(joints).all() or not np.isfinite(bounds).all()
            or gain < 0 or min(linear_limit, angular_limit, joint_limit) <= 0):
        raise ValueError('finite root-COM/joint velocities and positive damping bounds required')
    target = np.zeros(22, dtype=np.float64)
    target[:3] = np.clip(-gain * base[:3], -linear_limit, linear_limit)
    target[3:6] = np.clip(-gain * base[3:], -angular_limit, angular_limit)
    target[6:] = np.clip(-gain * joints, -joint_limit, joint_limit)
    return target

from ame_baseline.m1_wbc_limits import effort_step_bounds


_IDENTITY_KEYS = ('env_id', 'episode', 'step', 'phase', 'leg', 'obstacle_id')
_TOTAL_EFFORT_SLEW_NM_S = 20.0
_DYNAMICS_RESIDUAL_LIMIT = 0.02
_NATIVE_EFFORT_READBACK_TOLERANCE_NM = 1e-6


def pd_handoff_acceleration_contract(*, target_qdd=None):
    """Bound acceleration and ask the QP to realize a validated target.

    The limits are a hard safety envelope for the first explicit-WBC tick;
    a hierarchical task asks the QP to realize target_qdd as closely as the
    measured effort-slew and contact constraints permit. Default is zero.
    """
    limits = np.r_[np.full(3, 2.0), np.full(3, 8.0), np.full(16, 100.0)]
    target = np.zeros(22) if target_qdd is None else np.asarray(target_qdd, dtype=float)
    if (target.shape != (22,) or not np.isfinite(target).all()
            or np.any(np.abs(target) > limits)):
        raise ValueError('target acceleration must be finite and inside the hard acceleration envelope')
    return dict(accel_lower=-limits, accel_upper=limits,
                tasks=((np.eye(22), target.copy(), np.ones(22)),))


def _numpy(value, name):
    if hasattr(value, 'detach'):
        value = value.detach()
    if hasattr(value, 'cpu'):
        value = value.cpu()
    if hasattr(value, 'numpy'):
        value = value.numpy()
    result = np.asarray(value, dtype=np.float64)
    if not np.isfinite(result).all():
        raise ValueError(f'{name} must be finite')
    return result


def _validate_identity(identity, expected_identity, step):
    if (not isinstance(identity, dict) or not isinstance(expected_identity, dict)
            or any(key not in identity or key not in expected_identity for key in _IDENTITY_KEYS)
            or any(identity[key] != expected_identity[key] for key in _IDENTITY_KEYS)
            or type(step) is not int or identity['step'] != step
            or type(identity['episode']) is not int or identity['episode'] < 0
            or type(identity['env_id']) is not int or identity['env_id'] != 0
            or not isinstance(identity['phase'], str) or not identity['phase']):
        raise ValueError('stale or incompatible WBC command identity')


def _joint_order(robot, solution):
    native = tuple(getattr(robot, 'joint_names', ()))
    provided = solution.get('joint_names') if isinstance(solution, dict) else None
    provided = tuple(provided) if isinstance(provided, (tuple, list)) else ()
    if (len(native) != 16 or len(set(native)) != 16
            or any(not isinstance(name, str) or not name for name in native)
            or provided != native):
        raise ValueError('WBC solution joint order does not match native articulation order')
    return native


def _state_fingerprint(robot):
    data = robot.data
    parts = (
        ('root_pos_w', (1, 3)), ('root_quat_w', (1, 4)),
        ('root_vel_w', (1, 6)), ('joint_pos', (1, 16)), ('joint_vel', (1, 16)),
    )
    digest = hashlib.sha256()
    for name, shape in parts:
        value = _numpy(getattr(data, name, None), name)
        if value.shape != shape:
            raise ValueError(f'invalid handoff state field: {name}')
        digest.update(np.asarray(value, dtype='<f8').tobytes(order='C'))
    return digest.hexdigest()


def _validate_native_clock(env, step, physics_steps, dt):
    sim = getattr(env, 'sim', None)
    native_steps = getattr(sim, 'current_time_step_index', None)
    native_time = getattr(sim, 'current_time', None)
    if (type(physics_steps) is not int or physics_steps < 0
            or not np.isfinite(dt) or not 0 < dt <= .1
            or type(native_steps) is not int or not isinstance(native_time, (float, int))
            or not np.isfinite(native_time) or native_steps != physics_steps
            or native_steps != step):
        raise ValueError('caller step disagrees with native simulation time')
    get_dt = getattr(sim, 'get_physics_dt', None)
    native_dt = get_dt() if callable(get_dt) else dt
    if (not isinstance(native_dt, (float, int)) or not np.isfinite(native_dt)
            or abs(native_dt-dt) > max(1e-12, dt*1e-7)):
        raise ValueError('caller step disagrees with native simulation time')
    # Isaac's timer sums callback step_size (float32 promoted to Python float),
    # not necessarily the original float64 configuration value. Check the two
    # explicit representations; do not accept an arbitrary growing drift band.
    expected = (physics_steps*native_dt,
                physics_steps*float(np.float32(native_dt)))
    if min(abs(native_time-value) for value in expected) > max(1e-9, dt*1e-5):
        raise ValueError('caller step disagrees with native simulation time')
    return sim, float(native_time)


def capture_pd_handoff(*, env, robot, view, identity, expected_identity,
                       step, physics_steps, dt):
    """Capture same-state native PD effort for an atomic diagnostic handoff.

    The caller must not advance simulation between this capture and
    ``apply_wbc_command(..., handoff=record)``. The command remains subject to
    the fixed slew bound from the measured projected native drive effort.
    """
    _validate_identity(identity, expected_identity, step)
    if getattr(env, 'num_envs', None) != 1:
        raise ValueError('PD handoff requires exactly one environment')
    _, native_time = _validate_native_clock(env, step, physics_steps, dt)
    if step <= 0:
        raise ValueError('PD handoff requires a settled, stepped diagnostic state')
    names = tuple(getattr(robot, 'joint_names', ()))
    if len(names) != 16 or len(set(names)) != 16:
        raise ValueError('native articulation joint order is invalid')
    stiffness = _numpy(view.get_dof_stiffnesses(), 'native stiffness')
    damping = _numpy(view.get_dof_dampings(), 'native damping')
    if (stiffness.size != 16 or damping.size != 16
            or not (np.any(stiffness != 0.) or np.any(damping != 0.))):
        raise ValueError('native implicit PD must be active for handoff capture')
    projected = _numpy(view.get_dof_projected_joint_forces(), 'projected native PD effort')
    direct = _numpy(view.get_dof_actuation_forces(), 'native direct effort before handoff')
    if projected.shape != (1, 16) or direct.shape != (1, 16):
        raise ValueError('native handoff effort dimensions rejected')
    native_limit = _numpy(view.get_dof_max_forces(), 'native PhysX effort limits')
    configured_limit = _numpy(robot.data.joint_effort_limits, 'configured effort limits')
    if native_limit.size != 16 or configured_limit.size != 16:
        raise ValueError('native handoff limit dimensions rejected')
    limits = np.minimum(native_limit.reshape(16), configured_limit.reshape(16))
    if np.any(limits <= 0) or np.any(np.abs(projected[0]) > limits + 1e-9):
        raise ValueError('projected PD effort exceeds native effort limits')
    return dict(owner='native_projected_pd', effort=projected[0].copy(),
        direct_effort=direct[0].copy(), stiffness=stiffness.reshape(16).copy(),
        damping=damping.reshape(16).copy(), state_hash=_state_fingerprint(robot),
        step=step, sim_time=native_time, episode=identity['episode'],
        identity=dict(identity), joint_names=names)


def apply_wbc_command(*, env, robot, view, solution, identity, expected_identity,
                      previous, step, physics_steps, dt, handoff=None):
    """Validate, write, and read back one M1 total-effort command.

    The first command is slew-limited from the measured native total effort at
    the verified pre-first-step boundary. Every later command requires the
    actual explicit-total command read back on the prior tick and passes the
    unchanged 20 Nm/s effort slew policy.
    """
    _validate_identity(identity, expected_identity, step)
    if getattr(env, 'num_envs', None) != 1:
        raise ValueError('grounded diagnostic execution requires exactly one environment')
    if (type(physics_steps) is not int or physics_steps < 0
            or not np.isfinite(dt) or not 0 < dt <= .1):
        raise ValueError('invalid physical step or timestep contract')
    sim, native_time = _validate_native_clock(env, step, physics_steps, dt)
    initial = step == 0 and physics_steps == 0 and previous is None and handoff is None
    if (handoff is None and (step == 0) != initial) or (handoff is not None and
            (step <= 0 or previous is not None)):
        raise ValueError('fresh explicit-total initialization required before first step')

    if not isinstance(solution, dict) or solution.get('valid') is not True:
        raise ValueError('invalid WBC solution; actuator write refused')
    try:
        _validate_identity(solution.get('identity'), identity, step)
    except (TypeError, ValueError):
        raise ValueError('WBC solution identity does not match current event') from None
    qdd = _numpy(solution.get('qdd'), 'WBC acceleration')
    effort = _numpy(solution.get('effort'), 'WBC effort')
    force = _numpy(solution.get('force'), 'WBC contact force')
    residual = _numpy(solution.get('dynamics_residual'), 'WBC dynamics residual')
    if (qdd.shape != (22,) or effort.shape != (16,) or force.ndim != 2
            or force.shape[1:] != (3,) or len(force) == 0 or residual.shape != (22,)
            or np.max(np.abs(residual)) > _DYNAMICS_RESIDUAL_LIMIT):
        raise ValueError('WBC solution dimensions or dynamics residual rejected')
    names = _joint_order(robot, solution)

    stiffness = _numpy(view.get_dof_stiffnesses(), 'native stiffness')
    damping = _numpy(view.get_dof_dampings(), 'native damping')
    if stiffness.size != 16 or damping.size != 16:
        raise ValueError('native implicit drive dimensions rejected')
    if handoff is None:
        if np.any(stiffness != 0.) or np.any(damping != 0.):
            raise ValueError('native implicit drive remains enabled; sole-owner command refused')
    else:
        if (not isinstance(handoff, dict) or handoff.get('owner') != 'native_projected_pd'
                or handoff.get('step') != step or handoff.get('episode') != identity['episode']
                or handoff.get('sim_time') != native_time
                or handoff.get('identity') != identity
                or tuple(handoff.get('joint_names', ())) != names
                or handoff.get('state_hash') != _state_fingerprint(robot)):
            raise ValueError('stale or changed native PD handoff state')
        if (not np.array_equal(stiffness.reshape(16), _numpy(handoff.get('stiffness'), 'handoff stiffness'))
                or not np.array_equal(damping.reshape(16), _numpy(handoff.get('damping'), 'handoff damping'))
                or not (np.any(stiffness != 0.) or np.any(damping != 0.))):
            raise ValueError('native PD gains changed since handoff capture')

    native_limit = _numpy(view.get_dof_max_forces(), 'native PhysX effort limits')
    configured_limit = _numpy(robot.data.joint_effort_limits, 'configured effort limits')
    if (native_limit.size != 16 or configured_limit.size != 16):
        raise ValueError('native M1 effort limit dimensions rejected')
    limits = np.minimum(native_limit.reshape(16), configured_limit.reshape(16))
    if np.any(limits <= 0) or np.any(np.abs(effort) > limits + 1e-9):
        raise ValueError('WBC effort exceeds native effort limits')
    native_before = _numpy(view.get_dof_actuation_forces(), 'prewrite native total effort')
    if native_before.shape != (1, 16) or np.any(np.abs(native_before[0]) > limits + 1e-9):
        raise ValueError('prewrite native total effort is invalid')
    rate = np.full(16, _TOTAL_EFFORT_SLEW_NM_S)
    if handoff is not None:
        prior_pd = _numpy(handoff.get('effort'), 'captured native projected PD effort')
        direct_pd = _numpy(handoff.get('direct_effort'), 'captured native direct effort')
        if (prior_pd.shape != (16,) or direct_pd.shape != (16,)
                or not np.allclose(native_before[0], direct_pd, atol=1e-7, rtol=0)):
            raise ValueError('native direct effort changed since PD handoff capture')
        lower = np.maximum(-limits, prior_pd - rate * dt)
        upper = np.minimum(limits, prior_pd + rate * dt)
        if np.any(effort < lower - 1e-6) or np.any(effort > upper + 1e-6):
            raise ValueError('handoff WBC effort violates measured-total slew bound')
    elif initial:
        lower = np.maximum(-limits, native_before[0] - rate * dt)
        upper = np.minimum(limits, native_before[0] + rate * dt)
        if np.any(effort < lower - 1e-6) or np.any(effort > upper + 1e-6):
            raise ValueError('initial WBC effort violates measured-total slew bound')
    else:
        if not isinstance(previous, dict):
            raise ValueError('actual previous explicit-total effort required')
        prior_command = _numpy(previous.get('command'), 'previous explicit-total effort')
        if prior_command.shape != (16,) or not np.allclose(
                prior_command, native_before[0], atol=1e-7, rtol=0):
            raise ValueError('native total effort changed since prior explicit command')
        bounds = effort_step_bounds(previous=previous, limits=limits, rate=rate, dt=dt,
                                    step=step, episode=identity['episode'])
        if np.any(effort < bounds['lower'] - 1e-6) or np.any(effort > bounds['upper'] + 1e-6):
            excess = np.maximum(bounds['lower']-effort, effort-bounds['upper']).clip(min=0.)
            raise ValueError('WBC effort violates total-command slew bound: '
                f'max_slew_excess_nm={float(np.max(excess))}, '
                f'effort_nm={effort.tolist()}, lower_nm={bounds["lower"].tolist()}, '
                f'upper_nm={bounds["upper"].tolist()}')

    if handoff is not None:
        joint_pos = robot.data.joint_pos
        zero = (joint_pos.new_zeros(joint_pos.shape) if hasattr(joint_pos, 'new_zeros')
                else np.zeros_like(joint_pos))
        robot.write_joint_stiffness_to_sim(zero)
        robot.write_joint_damping_to_sim(zero)
        switched_stiffness = _numpy(view.get_dof_stiffnesses(), 'native stiffness after handoff')
        switched_damping = _numpy(view.get_dof_dampings(), 'native damping after handoff')
        if np.any(switched_stiffness != 0.) or np.any(switched_damping != 0.):
            raise ValueError('native implicit PD disable readback mismatch')

    joint_pos = robot.data.joint_pos
    if tuple(joint_pos.shape) != (1, 16):
        raise ValueError('native one-environment M1 joint state required')
    if hasattr(joint_pos, 'new_tensor'):
        command = joint_pos.new_tensor(effort).reshape_as(joint_pos)
    else:
        command = np.asarray(effort, dtype=np.asarray(joint_pos).dtype).reshape(1, 16)
    robot.set_joint_effort_target(command)
    robot.write_data_to_sim()
    readback = _numpy(view.get_dof_actuation_forces(), 'native effort readback')
    if readback.shape != (1, 16):
        raise ValueError(f'native total-effort readback shape mismatch: {readback.shape}')
    readback_error = float(np.max(np.abs(readback[0]-effort)))
    if readback_error > _NATIVE_EFFORT_READBACK_TOLERANCE_NM:
        raise ValueError('native total-effort readback mismatch; do not advance physics: '
                         f'max_error_nm={readback_error}, '
                         f'expected_nm={effort.tolist()}, actual_nm={readback[0].tolist()}')
    actual = readback[0].copy()
    record = dict(command=actual, step=step, episode=identity['episode'],
                  owner='explicit_total', identity=dict(identity), initial=initial,
                  handoff_source='native_projected_pd' if handoff is not None else None,
                  joint_names=names)
    return dict(record=record, readback_error=readback_error)
