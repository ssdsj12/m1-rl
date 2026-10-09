"""Acceleration of a rigid velocity field at a moving contact location.

This is a transport identity, not a wheel-shape or contact-mode estimator.
Callers must supply a verified geometric evaluation-point velocity; it is not
the material point velocity and must not come from differencing patch IDs.
All quantities are world-frame, same instant, per-contact K x 3.
"""
import numpy as np


def contact_acceleration_bias(*, com_bias, angular_bias, omega, arm,
                              material_velocity, geometry_velocity):
    """Return the bias in d(v_material_at_geometry)/dt = Jpoint*qdd + bias.

    com_bias/angular_bias are the corresponding body's qdd=0 accelerations.
    arm is evaluation point minus that body's COM. For no-slip stationary ground,
    zero derivative yields Jpoint*qdd=-total_bias, but the caller must separately
    confirm active contact/mode and handle current slip and unilateral conditions.
    No ground constraint or actuator command is imposed by this function.
    """
    data=[np.asarray(x,dtype=np.float64) for x in
          (com_bias,angular_bias,omega,arm,material_velocity,geometry_velocity)]
    shape=data[0].shape
    if (len(shape)!=2 or shape[1]!=3
            or any(x.shape!=shape or not np.isfinite(x).all() for x in data)):
        raise ValueError('finite matching K x 3 world contact data required')
    linear,alpha,w,r,vm,vg=data
    material=linear+np.cross(alpha,r)+np.cross(w,np.cross(w,r))
    migration=np.cross(w,vg-vm)
    total=material+migration
    if not all(np.isfinite(x).all() for x in (material,migration,total)):
        raise ValueError('nonfinite transported acceleration')
    return dict(material_bias=material,transport_bias=migration,total_bias=total)
