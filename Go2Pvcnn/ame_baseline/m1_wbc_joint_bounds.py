"""One-step authored joint-state bounds; not a braking/viability certificate."""
import numpy as np


def joint_step_bounds(*,position,velocity,position_limits,velocity_limits,dt):
    q,v,ql,vl=[np.asarray(x,dtype=float) for x in
               (position,velocity,position_limits,velocity_limits)]
    if (q.ndim!=1 or v.shape!=q.shape or ql.shape!=(len(q),2) or vl.shape!=q.shape
            or not np.isfinite(dt) or dt<=0
            or any(not np.isfinite(x).all() for x in (q,v,ql,vl))
            or (ql[:,0]>ql[:,1]).any() or (vl<=0).any()
            or (q<ql[:,0]).any() or (q>ql[:,1]).any() or (np.abs(v)>vl).any()):
        raise ValueError('finite in-limit joint state and positive timestep required')
    next_lower=np.maximum(-vl,(ql[:,0]-q)/dt)
    next_upper=np.minimum(vl,(ql[:,1]-q)/dt)
    lower=(next_lower-v)/dt;upper=(next_upper-v)/dt
    if not np.isfinite(lower).all() or not np.isfinite(upper).all() or (lower>upper).any():
        raise ValueError('empty or nonfinite next-state acceleration interval')
    return dict(lower=lower,upper=upper)
