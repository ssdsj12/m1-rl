"""Explicit diagnostic policies, not manufacturer ratings or actuator writes."""
import numpy as np


def diagnostic_speed_limits(*,names,leg_names,wheel_names,native_limits,leg_cap,wheel_cap):
    names,legs,wheels=tuple(names),set(leg_names),set(wheel_names)
    native=np.asarray(native_limits,dtype=float)
    if (len(names)!=16 or len(set(names))!=16 or len(legs)!=12 or len(wheels)!=4
            or legs&wheels or set(names)!=legs|wheels or native.shape!=(16,)
            or not np.isfinite(native).all() or (native<=0).any()
            or not np.isfinite([leg_cap,wheel_cap]).all() or min(leg_cap,wheel_cap)<=0):
        raise ValueError('complete named M1 joints and explicit positive speed caps required')
    return np.minimum(native,[leg_cap if n in legs else wheel_cap for n in names])


def effort_step_bounds(*,previous,limits,rate,dt,step,episode):
    """Caller must establish sole ownership; metadata alone is not verification.

    No implicit initialization. A fresh simulator startup needs an explicitly
    verified initial-command procedure before it can provide this history.
    """
    if (not isinstance(previous,dict) or previous.get('owner')!='explicit_total'
            or type(step) is not int or step<1 or type(episode) is not int or episode<0
            or previous.get('step')!=step-1 or previous.get('episode')!=episode):
        raise ValueError('previous explicit total command from prior tick/same episode required')
    p,lim,r=[np.asarray(v,dtype=float) for v in (previous.get('command'),limits,rate)]
    if (p.ndim!=1 or lim.shape!=p.shape or r.shape!=p.shape
            or not np.isfinite(dt) or not 0<dt<=.1
            or any(not np.isfinite(v).all() for v in (p,lim,r))
            or (lim<=0).any() or (r<=0).any() or (np.abs(p)>lim).any()):
        raise ValueError('finite in-limit prior effort and positive limits/rates required')
    return dict(lower=np.maximum(-lim,p-r*dt),upper=np.minimum(lim,p+r*dt))


def qp_effort_interior_bounds(*,bounds,margin):
    """Inset solver bounds so numerical feasibility tolerance cannot break slew.

    The returned interval is always strictly inside the hard actuator interval;
    it never increases the allowed physical effort change.
    """
    if not isinstance(bounds,dict) or not np.isfinite(margin) or margin <= 0:
        raise ValueError('finite positive solver margin and effort bounds required')
    lower=np.asarray(bounds.get('lower'),dtype=float)
    upper=np.asarray(bounds.get('upper'),dtype=float)
    if (lower.ndim!=1 or upper.shape!=lower.shape or lower.size==0
            or not np.isfinite(lower).all() or not np.isfinite(upper).all()
            or np.any(lower>=upper) or np.any(upper-lower<=2*margin)):
        raise ValueError('effort slew interval is invalid or too narrow for solver margin')
    return dict(lower=lower+margin,upper=upper-margin)
