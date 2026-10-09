"""Explicit candidate point-mode constraints; not a contact-mode estimator."""
import numpy as np


def contact_mode_constraints(*, jac, frames, bias, attached, normal_max,
                             separation_accel_min):
    """Construct fixed-mode acceleration and force bounds for the WBC QP.

    Attached points have zero evaluated velocity derivative. Released points
    have zero force and caller-specified normal acceleration lower bounds.
    Caller must establish current validity, slip/gap/velocity and geometry
    migration before choosing any mode; this function does not certify those.
    Original point ordering/moment arms are retained, including zero-force slots.
    """
    jac,frames,bias,normal_max,separation_accel_min=[np.asarray(x,dtype=np.float64)
        for x in (jac,frames,bias,normal_max,separation_accel_min)]
    attached=np.asarray(attached)
    if jac.ndim!=3 or jac.shape[1:]!=(3,22):
        raise ValueError('point Jacobian must be K x 3 x 22')
    k=len(jac)
    if (frames.shape!=(k,3,3) or bias.shape!=(k,3) or normal_max.shape!=(k,)
            or separation_accel_min.shape!=(k,) or attached.shape!=(k,)
            or attached.dtype.kind!='b'
            or any(not np.isfinite(x).all() for x in (jac,frames,bias,normal_max,separation_accel_min))
            or (normal_max<0).any()):
        raise ValueError('finite aligned point data and explicit boolean mode required')
    if (not np.allclose(frames.transpose(0,2,1)@frames,np.eye(3),atol=1e-6,rtol=0)
            or not np.allclose(np.linalg.det(frames),1.,atol=1e-6,rtol=0)):
        raise ValueError('right-handed orthonormal contact frames required')
    released=~attached; normals=frames[released,:,2]
    return dict(contact_matrix=jac[attached].reshape(-1,22),
        contact_rhs=-bias[attached].reshape(-1),
        separation_matrix=np.einsum('ki,kij->kj',normals,jac[released]),
        separation_lower=separation_accel_min[released]-np.einsum('ki,ki->k',normals,bias[released]),
        normal_max=np.where(attached,normal_max,0.))
