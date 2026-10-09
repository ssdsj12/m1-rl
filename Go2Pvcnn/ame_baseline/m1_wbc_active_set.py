"""Independent CPU fallback, preserving all original physical constraint checks.

Native active-set call is not interruptible: elapsed time is checked on return.
This is an offline/small-batch oracle, not a certified real-time actuator backend.
"""
import time
import numpy as np


def solve_active_set(p,q,a,lower,upper,*,time_limit):
    started=time.perf_counter()
    def reject(reason):
        return dict(valid=False,reason=reason,x=None,elapsed=time.perf_counter()-started)
    if not np.isfinite(time_limit) or time_limit<=0:
        return reject('fallback_time_budget')
    try:
        import quadprog
    except ImportError:
        return reject('active_set_backend_unavailable')
    p,q,a,lower,upper=[np.asarray(v,dtype=np.float64) for v in (p,q,a,lower,upper)]
    n=len(q)
    if (q.shape!=(n,) or p.shape!=(n,n) or a.ndim!=2 or a.shape[1]!=n
            or lower.shape!=(len(a),) or upper.shape!=(len(a),)
            or not all(np.isfinite(v).all() for v in (p,q,a))
            or np.isnan(lower).any() or np.isnan(upper).any() or (lower>upper).any()):
        raise ValueError('invalid active-set QP contract')
    eq=np.isfinite(lower)&(lower==upper)
    e,b=a[eq],lower[eq]
    origin=np.zeros(n); null=np.eye(n); rank=0
    if len(e):
        u,s,vt=np.linalg.svd(e,full_matrices=True)
        cutoff=np.finfo(float).eps*max(e.shape)*(s[0] if len(s) else 0.)
        rank=int(np.sum(s>cutoff))
        origin=vt[:rank].T@((u[:,:rank].T@b)/s[:rank])
        null=vt[rank:].T
        if np.max(np.abs(e@origin-b))>1e-8:
            return reject('inconsistent_equalities')
    iterations=0
    try:
        if null.shape[1]:
            reduced_p=null.T@p@null
            reduced_p=(reduced_p+reduced_p.T)/2
            reduced_q=null.T@(p@origin+q)
            reduced_a=a[~eq]@null; offset=a[~eq]@origin
            lo=lower[~eq]-offset; hi=upper[~eq]-offset
            finite_lo=np.isfinite(lo); finite_hi=np.isfinite(hi)
            constraints=np.vstack((reduced_a[finite_lo],-reduced_a[finite_hi]))
            bounds=np.r_[lo[finite_lo],-hi[finite_hi]]
            if time.perf_counter()-started>=time_limit:
                return reject('fallback_time_budget')
            result=quadprog.solve_qp(reduced_p,-reduced_q,constraints.T,bounds)
            x=origin+null@result[0]; iterations=int(result[3][0])
        else:
            x=origin
    except (ValueError,np.linalg.LinAlgError) as error:
        return reject('active_set_rejected: '+str(error))
    elapsed=time.perf_counter()-started
    if elapsed>time_limit:
        return reject('fallback_time_budget')
    if not np.isfinite(x).all():
        return reject('nonfinite_active_set_result')
    actual=a@x
    violation=float(max(0.,np.max(lower-actual,initial=0.),np.max(actual-upper,initial=0.)))
    if violation>1e-5:
        return reject('active_set_original_constraint_check')
    return dict(valid=True,reason='solved',x=x,elapsed=elapsed,
                iterations=iterations,equality_rank=rank,max_violation=violation)
