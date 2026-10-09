"""Measured material-point motion, not a contact-mode acceptance policy."""
import numpy as np


def contact_motion(*,points,normals,owners,com_positions,com_velocity,surface_velocity):
    points,normals,com_positions,com_velocity,surface_velocity=[np.asarray(v,dtype=float)
        for v in (points,normals,com_positions,com_velocity,surface_velocity)]
    owners=np.asarray(owners)
    if (points.ndim!=2 or points.shape[1]!=3 or normals.shape!=points.shape
            or surface_velocity.shape!=points.shape or owners.shape!=(len(points),)
            or owners.dtype.kind not in 'iu' or com_positions.ndim!=2
            or com_positions.shape[1]!=3 or com_velocity.shape!=(len(com_positions),6)
            or (owners<0).any() or (owners>=len(com_positions)).any()
            or any(not np.isfinite(v).all() for v in
                   (points,normals,com_positions,com_velocity,surface_velocity))):
        raise ValueError('finite aligned material point and surface motion required')
    if not np.allclose(np.linalg.norm(normals,axis=1),1.,atol=1e-6,rtol=0):
        raise ValueError('unit surface normal required')
    velocity=com_velocity[owners]
    material=velocity[:,:3]+np.cross(velocity[:,3:],points-com_positions[owners])
    relative=material-surface_velocity
    normal=np.einsum('ki,ki->k',relative,normals)
    tangent=relative-normal[:,None]*normals
    return dict(material_velocity=material,relative_velocity=relative,
                normal_speed=normal,tangent_velocity=tangent,
                slip_speed=np.linalg.norm(tangent,axis=1))
