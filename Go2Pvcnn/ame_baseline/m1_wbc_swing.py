"""Time-parameterized, single-wheel swing reference for obstacle crossings."""
import numpy as np


def single_wheel_swing_reference(*, start, landing, progress, duration,
                                 obstacle_front_x, obstacle_far_x,
                                 obstacle_top_z, wheel_radius, clearance,
                                 approach_distance, exit_distance):
    """Return world-frame wheel-center position, velocity, and acceleration.

    The caller is responsible for choosing ``landing`` beyond the obstacle's
    far boundary and for keeping the other three wheels in support. The swing
    apex accounts for the wheel envelope, not just its center. A quintic
    endpoint blend and a bounded, C2-continuous lift plateau enforce the wheel
    envelope clearance over the *entire* obstacle overlap, beginning before
    the near edge and descending only after the far edge has cleared.
    """
    start = np.asarray(start, dtype=np.float64)
    landing = np.asarray(landing, dtype=np.float64)
    scalars = np.asarray([progress, duration, obstacle_front_x,
                          obstacle_far_x, obstacle_top_z, wheel_radius,
                          clearance, approach_distance, exit_distance],
                         dtype=np.float64)
    if (start.shape != (3,) or landing.shape != (3,)
            or not np.isfinite(start).all() or not np.isfinite(landing).all()
            or not np.isfinite(scalars).all()):
        raise ValueError('finite 3D endpoints and scalar swing parameters required')
    (progress, duration, obstacle_front_x, obstacle_far_x, obstacle_top_z,
     wheel_radius, clearance, approach_distance, exit_distance) = scalars.tolist()
    if (not 0.0 <= progress <= 1.0 or duration <= 0.0
            or wheel_radius <= 0.0 or clearance < 0.0
            or approach_distance <= 0.0 or exit_distance <= 0.0
            or obstacle_far_x <= obstacle_front_x):
        raise ValueError('progress, duration, wheel radius, or clearance is invalid')

    delta = landing - start
    if delta[0] <= 0.0:
        raise ValueError('single-wheel obstacle swing must advance along world +x')
    lift_start_x = obstacle_front_x - wheel_radius - approach_distance
    overlap_start_x = obstacle_front_x - wheel_radius
    overlap_end_x = obstacle_far_x + wheel_radius
    lower_end_x = overlap_end_x + exit_distance
    if lift_start_x <= start[0] or lower_end_x > landing[0]:
        raise ValueError('swing endpoints must leave approach and far-side landing room')

    p = progress
    blend = 10.0*p**3 - 15.0*p**4 + 6.0*p**5
    blend_d = 30.0*p**2 - 60.0*p**3 + 30.0*p**4
    blend_dd = 60.0*p - 180.0*p**2 + 120.0*p**3
    required_center_z = obstacle_top_z + wheel_radius + clearance
    target_z = max(required_center_z, float(start[2]), float(landing[2]))

    def progress_at_x(x):
        fraction = (x - start[0]) / delta[0]
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            value = 10.0*mid**3 - 15.0*mid**4 + 6.0*mid**5
            if value < fraction:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    lift_start_p, overlap_start_p = map(progress_at_x,
                                        (lift_start_x, overlap_start_x))
    overlap_end_p, lower_end_p = map(progress_at_x,
                                     (overlap_end_x, lower_end_x))

    def smoothstep(value):
        u = min(max(float(value), 0.0), 1.0)
        return (10.0*u**3 - 15.0*u**4 + 6.0*u**5,
                30.0*u**2 - 60.0*u**3 + 30.0*u**4,
                60.0*u - 180.0*u**2 + 120.0*u**3)

    gate, gate_d, gate_dd = 0.0, 0.0, 0.0
    if lift_start_p < p < overlap_start_p:
        width = overlap_start_p - lift_start_p
        gate, gate_d, gate_dd = smoothstep((p-lift_start_p)/width)
        gate_d /= width
        gate_dd /= width*width
    elif overlap_start_p <= p <= overlap_end_p:
        gate = 1.0
    elif overlap_end_p < p < lower_end_p:
        width = lower_end_p - overlap_end_p
        gate, gate_d, gate_dd = smoothstep((p-overlap_end_p)/width)
        gate = 1.0-gate
        gate_d = -gate_d/width
        gate_dd = -gate_dd/(width*width)

    baseline_z = start[2] + blend*delta[2]
    baseline_z_d = blend_d*delta[2]
    baseline_z_dd = blend_dd*delta[2]
    lift_delta = target_z-baseline_z
    position = start + blend*delta
    position[2] = baseline_z + gate*lift_delta
    position_d = blend_d*delta
    position_d[2] = (1.0-gate)*baseline_z_d + gate_d*lift_delta
    position_dd = blend_dd*delta
    position_dd[2] = ((1.0-gate)*baseline_z_dd
                      - 2.0*gate_d*baseline_z_d + gate_dd*lift_delta)
    velocity = position_d/duration
    acceleration = position_dd/(duration*duration)
    phase = 'LIFT_OFF' if p == 0.0 else ('TOUCHDOWN' if p == 1.0 else 'SWING')
    return dict(position=position, velocity=velocity, acceleration=acceleration,
                apex_z=target_z, required_center_z=required_center_z,
                obstacle_overlap_progress=(overlap_start_p, overlap_end_p),
                phase=phase)


def single_wheel_swing_qp_task(*, jacobian, bias_acceleration, position,
                               velocity, reference, kp, kd,
                               max_acceleration, weight):
    """Translate a measured wheel-center tracking error into a WBC task tier.

    The returned equality target accounts for the measured kinematic bias:
    ``J @ qdd = a_desired - bias``. It is a soft tracking objective; hard
    support, collision, effort and actuator constraints remain owned by WBC.
    This function accepts exactly one wheel Jacobian, preventing accidental
    coupling of two legs into one swing task.
    """
    jacobian = np.asarray(jacobian, dtype=np.float64)
    bias_acceleration = np.asarray(bias_acceleration, dtype=np.float64)
    position = np.asarray(position, dtype=np.float64)
    velocity = np.asarray(velocity, dtype=np.float64)
    if not isinstance(reference, dict):
        raise ValueError('one wheel swing reference is required')
    ref_position = np.asarray(reference.get('position'), dtype=np.float64)
    ref_velocity = np.asarray(reference.get('velocity'), dtype=np.float64)
    ref_acceleration = np.asarray(reference.get('acceleration'), dtype=np.float64)
    scalar = np.asarray([kp, kd, max_acceleration, weight], dtype=np.float64)
    vectors = (bias_acceleration, position, velocity, ref_position, ref_velocity,
               ref_acceleration)
    if (jacobian.shape != (3, 22) or any(v.shape != (3,) for v in vectors)
            or not np.isfinite(jacobian).all()
            or any(not np.isfinite(v).all() for v in vectors)
            or not np.isfinite(scalar).all() or kp < 0 or kd < 0
            or max_acceleration <= 0 or weight <= 0):
        raise ValueError('finite single-wheel task geometry and positive task bounds required')
    desired = ref_acceleration + kp*(ref_position-position) + kd*(ref_velocity-velocity)
    magnitude = float(np.linalg.norm(desired))
    if magnitude > max_acceleration:
        desired = desired*(max_acceleration/magnitude)
    return dict(matrix=jacobian.copy(), target=desired-bias_acceleration,
                weight=np.full(3, weight), desired_acceleration=desired)
