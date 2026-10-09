"""Local semiimplicit contact predictor, not an impact/actuation certificate."""
import numpy as np
from ame_baseline.m1_wbc_modes import contact_mode_constraints
from ame_baseline.m1_wbc_transport import contact_acceleration_bias


def project_contact_rows_to_local_frames(*, jac, frames, rhs):
    """Project world contact acceleration equations into their local bases."""
    jac = np.asarray(jac, dtype=np.float64)
    frames = np.asarray(frames, dtype=np.float64)
    rhs = np.asarray(rhs, dtype=np.float64)
    if (jac.ndim != 3 or jac.shape[1:] != (3, 22)
            or frames.shape != (len(jac), 3, 3) or rhs.shape != (len(jac), 3)
            or any(not np.isfinite(v).all() for v in (jac, frames, rhs))):
        raise ValueError('finite Kx3x22 Jacobians, K local frames and Kx3 RHS required')
    gram = np.einsum('kji,kjl->kil', frames, frames)
    if not np.allclose(gram, np.broadcast_to(np.eye(3), gram.shape), atol=1e-5, rtol=0):
        raise ValueError('contact frames must be orthonormal')
    return (np.einsum('kji,kjm->kim', frames, jac),
            np.einsum('kji,kj->ki', frames, rhs))


def contact_step_constraints(*,jac,frames,bias,velocity,gap,attached,normal_max,dt,
                             tangent_velocity_time_constant=None):
    velocity,gap,bias,frames=[np.asarray(v,dtype=float) for v in (velocity,gap,bias,frames)]
    attached=np.asarray(attached)
    if (not np.isfinite(dt) or dt<=0 or gap.ndim!=1
            or velocity.shape!=(len(gap),3) or bias.shape!=velocity.shape
            or frames.shape!=(len(gap),3,3)
            or any(not np.isfinite(v).all() for v in (velocity,gap,bias,frames))):
        raise ValueError('finite measured motion/gap and positive physics timestep required')
    if tangent_velocity_time_constant is None:
        tangent_velocity_time_constant=dt
    if (not np.isfinite(tangent_velocity_time_constant)
            or tangent_velocity_time_constant<=0):
        raise ValueError('positive finite tangent velocity time constant required')
    normals=frames[:,:,2]
    normal_velocity=np.einsum('ki,ki->k',velocity,normals)
    separation_accel=(-gap/dt-normal_velocity)/dt
    result=contact_mode_constraints(jac=jac,frames=frames,bias=bias,attached=attached,
        normal_max=normal_max,separation_accel_min=separation_accel)
    normal_target=np.maximum(0.,-gap/dt)
    normal_accel=((normal_target-normal_velocity)/dt)[:,None]*normals
    tangent_velocity=velocity-normal_velocity[:,None]*normals
    target_accel=normal_accel-tangent_velocity/tangent_velocity_time_constant
    result['contact_rhs']=(target_accel-bias)[attached].reshape(-1)
    return result


def normal_only_contact_step_constraints(*,jac,frames,bias,velocity,gap,attached,
                                         normal_max,dt):
    """Diagnostic ablation: keep normal contact, omit tangent acceleration rows.

    This is deliberately not presented as a rolling-contact controller: the
    omitted tangent rows need a verified migrating-patch rolling constraint.
    It is useful only as a same-state counterfactual against a welded-point
    model. Released points retain the normal non-penetration constraint.
    """
    jac=np.asarray(jac,dtype=np.float64)
    frames=np.asarray(frames,dtype=np.float64)
    bias=np.asarray(bias,dtype=np.float64)
    velocity=np.asarray(velocity,dtype=np.float64)
    gap=np.asarray(gap,dtype=np.float64)
    attached=np.asarray(attached)
    result=contact_step_constraints(jac=jac,frames=frames,bias=bias,
        velocity=velocity,gap=gap,attached=attached,normal_max=normal_max,dt=dt)
    normals=frames[:,:,2]
    normal_velocity=np.einsum('ki,ki->k',velocity,normals)
    normal_bias=np.einsum('ki,ki->k',bias,normals)
    normal_target=np.maximum(0.,-gap/dt)
    normal_rhs=(normal_target-normal_velocity)/dt-normal_bias
    normal_rows=np.einsum('ki,kij->kj',normals,jac)
    result['contact_matrix']=normal_rows[attached]
    result['contact_rhs']=normal_rhs[attached]
    return result


def rolling_contact_step_constraints(*,jac,frames,com_bias,angular_bias,omega,
        arm,material_velocity,geometry_velocity,velocity,gap,attached,normal_max,dt,
        tangent_velocity_time_constant=None):
    """Build attached-wheel acceleration rows with contact-patch transport.

    `geometry_velocity` is the velocity of the *geometric evaluation point*
    moving over the static terrain, not the velocity of the wheel material
    currently at that point. The transport term is required for rolling wheels;
    caller must supply it from a verified surface/shape model rather than a
    differenced contact-patch identifier. Released points retain the existing
    unilateral normal separation constraints.
    """
    jac=np.asarray(jac,dtype=np.float64)
    frames=np.asarray(frames,dtype=np.float64)
    gap=np.asarray(gap,dtype=np.float64)
    attached=np.asarray(attached)
    transported=contact_acceleration_bias(com_bias=com_bias,
        angular_bias=angular_bias,omega=omega,arm=arm,
        material_velocity=material_velocity,geometry_velocity=geometry_velocity)
    result=contact_step_constraints(jac=jac,frames=frames,
        bias=transported['total_bias'],velocity=velocity,gap=gap,
        attached=attached,normal_max=normal_max,dt=dt,
        tangent_velocity_time_constant=tangent_velocity_time_constant)
    rhs=np.asarray(result['contact_rhs'],dtype=np.float64)
    if rhs.shape!=(int(np.sum(attached))*3,) or not np.isfinite(rhs).all():
        raise ValueError('invalid transported rolling-contact rhs')
    result['contact_matrix']=jac[attached].reshape(-1,22)
    result['transport_bias']=transported['transport_bias']
    result['material_bias']=transported['material_bias']
    result['total_bias']=transported['total_bias']
    return result


def smooth_wheel_geometry_velocity(*,center_velocity,normals):
    """Instantaneous evaluation-point velocity for a round wheel on a static plane.

    For a smooth circular wheel, the geometric point at the terrain support
    normal is `center - radius * normal`; on a locally planar stationary patch,
    its tangent velocity is the wheel-center velocity projected to that plane.
    This is not valid for polygon vertices, moving terrain, or a discontinuous
    patch transition; callers must reject those modes instead of guessing.
    """
    center_velocity=np.asarray(center_velocity,dtype=np.float64)
    normals=np.asarray(normals,dtype=np.float64)
    if (center_velocity.ndim!=2 or center_velocity.shape[1]!=3
            or normals.shape!=center_velocity.shape
            or not np.isfinite(center_velocity).all() or not np.isfinite(normals).all()):
        raise ValueError('finite matching wheel-center velocity and surface normal required')
    norm=np.linalg.norm(normals,axis=1)
    if not np.allclose(norm,1.,atol=1e-4,rtol=0):
        raise ValueError('unit normals required for wheel geometry velocity')
    normal=normals/norm[:,None]
    result=center_velocity-np.einsum('ki,ki->k',center_velocity,normal)[:,None]*normal
    if not np.isfinite(result).all():
        raise ValueError('nonfinite wheel geometry velocity')
    return result
