"""Read-only rolling/slip observations for M1 contact-controller probes."""
import numpy as np

from ame_baseline.m1_wbc_contact_step import smooth_wheel_geometry_velocity
from ame_baseline.m1_wbc_motion import contact_motion


def contact_diagnostics(*, points, normals, owners, com_positions,
                        com_velocity, surface_velocity, gaps=None):
    """Return measured material slip and wheel-geometry velocities.

    This is diagnostic evidence only. It does not decide contact validity,
    certify a rolling mode, or count an obstacle crossing.
    """
    points = np.asarray(points, dtype=np.float64)
    normals = np.asarray(normals, dtype=np.float64)
    owners = np.asarray(owners)
    com_positions = np.asarray(com_positions, dtype=np.float64)
    com_velocity = np.asarray(com_velocity, dtype=np.float64)
    surface_velocity = np.asarray(surface_velocity, dtype=np.float64)
    if gaps is not None:
        gaps = np.asarray(gaps, dtype=np.float64)
    if (points.ndim != 2 or points.shape[1:] != (3,) or len(points) == 0
            or normals.shape != points.shape or surface_velocity.shape != points.shape
            or gaps is not None and gaps.shape != (len(points),)
            or owners.shape != (len(points),) or owners.dtype.kind not in "iu"
            or com_positions.shape != (4, 3) or com_velocity.shape != (4, 6)
            or not all(np.isfinite(value).all() for value in
                       (points, normals, com_positions, com_velocity, surface_velocity))
            or gaps is not None and not np.isfinite(gaps).all()
            or np.any(owners < 0) or np.any(owners >= 4)):
        raise ValueError("finite contact data and four named M1 wheel owners required")

    motion = contact_motion(points=points, normals=normals, owners=owners,
        com_positions=com_positions, com_velocity=com_velocity,
        surface_velocity=surface_velocity)
    geometry = smooth_wheel_geometry_velocity(
        center_velocity=com_velocity[owners, :3], normals=normals)
    rows = []
    for index, owner in enumerate(owners.tolist()):
        row = dict(
            wheel_owner=int(owner),
            material_velocity_mps=motion["material_velocity"][index].tolist(),
            relative_velocity_mps=motion["relative_velocity"][index].tolist(),
            slip_speed_mps=float(motion["slip_speed"][index]),
            normal_speed_mps=float(motion["normal_speed"][index]),
            geometry_velocity_mps=geometry[index].tolist(),
        )
        if gaps is not None:
            row["gap_m"] = float(gaps[index])
        rows.append(row)
    by_wheel = np.zeros((4, 3), dtype=np.float64)
    for owner in range(4):
        selected = owners == owner
        if selected.any():
            by_wheel[owner] = geometry[np.flatnonzero(selected)[0]]
    return dict(
        scope="diagnostic_only_not_crossing_or_contact_acceptance",
        contacts=rows,
        geometry_velocity_by_wheel_mps=by_wheel.tolist(),
    )


def jacobian_velocity_consistency(*, wheel_com_jacobians, generalized_velocity,
                                 wheel_com_velocity, contact_jacobians,
                                 material_contact_velocity):
    """Compare native Jacobian velocity predictions with the same live state."""
    wheel_jac = np.asarray(wheel_com_jacobians, dtype=np.float64)
    qdot = np.asarray(generalized_velocity, dtype=np.float64)
    wheel_velocity = np.asarray(wheel_com_velocity, dtype=np.float64)
    contact_jac = np.asarray(contact_jacobians, dtype=np.float64)
    contact_velocity = np.asarray(material_contact_velocity, dtype=np.float64)
    if (wheel_jac.shape != (4, 6, 22) or qdot.shape != (22,)
            or wheel_velocity.shape != (4, 6)
            or contact_jac.ndim != 3 or contact_jac.shape[1:] != (3, 22)
            or contact_velocity.shape != (len(contact_jac), 3)
            or not all(np.isfinite(value).all() for value in
                       (wheel_jac, qdot, wheel_velocity, contact_jac, contact_velocity))):
        raise ValueError("finite M1 wheel/contact Jacobians and matching live velocities required")
    wheel_predicted = np.einsum("wci,i->wc", wheel_jac, qdot)
    contact_predicted = np.einsum("kci,i->kc", contact_jac, qdot)
    wheel_error = wheel_predicted - wheel_velocity
    contact_error = contact_predicted - contact_velocity
    return dict(
        wheel_predicted_velocity=wheel_predicted.tolist(),
        wheel_velocity_error=wheel_error.tolist(),
        max_wheel_velocity_error_mps=float(np.max(np.abs(wheel_error[:, :3]))),
        max_wheel_angular_velocity_error_rad_s=float(np.max(np.abs(wheel_error[:, 3:]))),
        contact_predicted_velocity_mps=contact_predicted.tolist(),
        contact_velocity_error_mps=contact_error.tolist(),
        max_contact_velocity_error_mps=float(np.max(np.abs(contact_error))),
    )


def contact_acceleration_consistency(*, predicted_acceleration, velocity_before,
                                    velocity_after, dt):
    """Compare a contact-mode acceleration prediction with a live next frame."""
    predicted = np.asarray(predicted_acceleration, dtype=np.float64)
    before = np.asarray(velocity_before, dtype=np.float64)
    after = np.asarray(velocity_after, dtype=np.float64)
    if (predicted.ndim != 2 or predicted.shape[1:] != (3,) or len(predicted) == 0
            or before.shape != predicted.shape or after.shape != predicted.shape
            or not np.isfinite(dt) or dt <= 0
            or not all(np.isfinite(value).all() for value in (predicted, before, after))):
        raise ValueError("finite matching Kx3 contact accelerations/velocities and positive dt required")
    finite_difference = (after - before) / float(dt)
    error = finite_difference - predicted
    return dict(
        predicted_acceleration_mps2=predicted.tolist(),
        finite_difference_acceleration_mps2=finite_difference.tolist(),
        model_error_mps2=error.tolist(),
        max_abs_model_error_mps2=float(np.max(np.abs(error))),
    )


def generalized_acceleration_consistency(*, predicted_acceleration, velocity_before,
                                        velocity_after, dt):
    """Compare full 6+16 WBC acceleration against a live physics step."""
    predicted = np.asarray(predicted_acceleration, dtype=np.float64)
    before = np.asarray(velocity_before, dtype=np.float64)
    after = np.asarray(velocity_after, dtype=np.float64)
    if (predicted.shape != (22,) or before.shape != (22,) or after.shape != (22,)
            or not np.isfinite(dt) or dt <= 0
            or not all(np.isfinite(value).all() for value in (predicted, before, after))):
        raise ValueError("finite 22D generalized acceleration/velocity and positive dt required")
    finite_difference = (after - before) / float(dt)
    error = finite_difference - predicted
    return dict(
        predicted_acceleration=predicted.tolist(),
        finite_difference_acceleration=finite_difference.tolist(),
        model_error=error.tolist(),
        max_abs_model_error=float(np.max(np.abs(error))),
        max_abs_base_linear_error_mps2=float(np.max(np.abs(error[:3]))),
        max_abs_base_angular_error_rad_s2=float(np.max(np.abs(error[3:6]))),
        max_abs_joint_error_rad_s2=float(np.max(np.abs(error[6:]))),
    )


def wheel_contact_force_consistency(*, predicted_world_force, contact_normals, owners,
                                    measured_wheel_normal_load):
    """Compare WBC normal load with PhysX's explicitly normal-only sensor output."""
    predicted = np.asarray(predicted_world_force, dtype=np.float64)
    normals = np.asarray(contact_normals, dtype=np.float64)
    owners = np.asarray(owners)
    measured = np.asarray(measured_wheel_normal_load, dtype=np.float64)
    if (predicted.ndim != 2 or predicted.shape[1:] != (3,) or len(predicted) == 0
            or normals.shape != predicted.shape
            or owners.shape != (len(predicted),) or owners.dtype.kind not in 'iu'
            or np.any(owners < 0) or np.any(owners >= 4)
            or measured.shape != (4,)
            or not np.isfinite(predicted).all() or not np.isfinite(normals).all()
            or not np.isfinite(measured).all()):
        raise ValueError('finite point forces/normals, four wheel owners and four normal loads required')
    normal_norm = np.linalg.norm(normals, axis=1)
    if not np.allclose(normal_norm, 1.0, atol=1e-4, rtol=0):
        raise ValueError('unit contact normals required for normal-load projection')
    point_normal = np.einsum('ki,ki->k', predicted, normals)
    aggregate = np.zeros(4, dtype=np.float64)
    for index, owner in enumerate(owners.tolist()):
        aggregate[owner] += point_normal[index]
    error = measured - aggregate
    return dict(
        predicted_wheel_normal_load_n=aggregate.tolist(),
        measured_wheel_normal_load_n=measured.tolist(),
        normal_load_error_n=error.tolist(),
        max_abs_normal_load_error_n=float(np.max(np.abs(error))),
        tangential_force_observed=False,
    )


def wheel_contact_force_vector_consistency(*, predicted_world_force, owners,
        measured_wheel_normal_force, raw_wheel_friction_force):
    """Compare QP forces under both friction-buffer sign conventions.

    The tensor API documents friction force as between sensor/filter bodies but
    does not identify which body's reaction the vector represents. Preserve the
    raw vector and report both orientations instead of guessing.
    """
    predicted = np.asarray(predicted_world_force, dtype=np.float64)
    owners = np.asarray(owners)
    normal = np.asarray(measured_wheel_normal_force, dtype=np.float64)
    friction = np.asarray(raw_wheel_friction_force, dtype=np.float64)
    if (predicted.ndim != 2 or predicted.shape[1:] != (3,) or len(predicted) == 0
            or owners.shape != (len(predicted),) or owners.dtype.kind not in 'iu'
            or np.any(owners < 0) or np.any(owners >= 4)
            or normal.shape != (4, 3) or friction.shape != (4, 3)
            or not np.isfinite(predicted).all() or not np.isfinite(normal).all()
            or not np.isfinite(friction).all()):
        raise ValueError('finite point forces, wheel owners, and separate 4x3 normal/friction buffers required')
    aggregate = np.zeros((4, 3), dtype=np.float64)
    for index, owner in enumerate(owners.tolist()):
        aggregate[owner] += predicted[index]
    direct = normal + friction
    reverse = normal - friction
    direct_error = direct - aggregate
    reverse_error = reverse - aggregate
    return dict(
        predicted_wheel_force_n=aggregate.tolist(),
        measured_wheel_normal_force_n=normal.tolist(),
        raw_wheel_friction_force_n=friction.tolist(),
        total_force_if_friction_on_sensor_n=direct.tolist(),
        total_force_if_friction_on_filter_n=reverse.tolist(),
        force_error_if_friction_on_sensor_n=direct_error.tolist(),
        force_error_if_friction_on_filter_n=reverse_error.tolist(),
        max_abs_force_error_n=float(min(np.max(np.abs(direct_error)),
                                        np.max(np.abs(reverse_error)))),
    )
