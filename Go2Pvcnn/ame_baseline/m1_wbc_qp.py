"""CPU full inverse-dynamics oracle; no simulator or actuator writes.

All acceleration/effort intervals must be derived by the caller from current
state, limits and slew budgets. Contact constraints must represent rolling,
not stationary wheel centers. Invalid output contains no usable command.
"""
import numpy as np
import scipy.sparse as sp
import osqp
import time


# This solver is a CPU correctness oracle, not the hard-real-time control
# backend. Under host contention OSQP may consume its stage limit and leave no
# time for the independent active-set oracle. Keep a bounded, explicit
# per-tier wall-clock budget instead of spuriously rejecting valid solutions.
_CPU_ORACLE_STAGE_BUDGET_S = 0.5


def _event_identity(value):
    keys = ('env_id', 'episode', 'step', 'phase', 'leg', 'obstacle_id')
    if (not isinstance(value, dict) or any(key not in value for key in keys)
            or any(type(value[key]) is not int or value[key] < 0
                   for key in ('env_id', 'episode', 'step'))
            or not isinstance(value['phase'], str) or not value['phase']
            or value['leg'] is not None and not isinstance(value['leg'], str)
            or value['obstacle_id'] is not None
               and not isinstance(value['obstacle_id'], (str, int))):
        raise ValueError('invalid WBC event identity')
    return {key: value[key] for key in keys}


def solve_wbc(*, mass, bias, jac, frames, mu, normal_min, normal_max,
              accel_lower, accel_upper, effort_lower, effort_upper,
              contact_matrix, contact_rhs, tasks=(),
              group_ids=None, group_min=None, group_max=None,
              separation_matrix=None, separation_lower=None, identity=None,
              joint_names=None):
    """Single-environment hierarchical QP, up to four ordered soft task tiers.

    Variables qdd22/tau16/world contact forces. Each contact frame has tangent,
    tangent, normal columns. No inactive force slots: omit inactive contacts.
    """
    identity = None if identity is None else _event_identity(identity)
    if joint_names is not None:
        joint_names = tuple(joint_names)
        if (len(joint_names) != 16 or len(set(joint_names)) != 16
                or any(not isinstance(name, str) or not name for name in joint_names)):
            raise ValueError('joint_names must identify the unique native 16-DOF order')

    def array(x, shape, name):
        a = np.asarray(x, dtype=np.float64)
        if a.shape != shape or not np.isfinite(a).all():
            raise ValueError(f'invalid {name} shape or nonfinite data')
        return a

    jac = np.asarray(jac, dtype=np.float64)
    if jac.ndim != 3 or jac.shape[1:] != (3, 22):
        raise ValueError('contact Jacobian must be K x 3 x 22')
    k = jac.shape[0]
    jac = array(jac, (k,3,22), 'jac')
    mass = array(mass, (22,22), 'mass')
    bias = array(bias, (22,), 'bias')
    if not np.allclose(mass, mass.T, atol=1e-9, rtol=1e-9):
        raise ValueError('mass must be symmetric')
    if np.linalg.eigvalsh(mass).min() <= 0:
        raise ValueError('mass must be positive definite')
    frames = array(frames, (k,3,3), 'frames')
    if (not np.allclose(frames.transpose(0,2,1)@frames, np.eye(3), atol=1e-6, rtol=0)
            or np.any(np.linalg.det(frames) < 1-1e-6)):
        raise ValueError('right-handed orthonormal contact frames required')
    mu = array(mu, (k,), 'mu')
    normal_min = array(normal_min, (k,), 'normal_min')
    normal_max = array(normal_max, (k,), 'normal_max')
    if np.any(mu < 0) or np.any(normal_min < 0) or np.any(normal_max < normal_min):
        raise ValueError('invalid friction or unilateral force interval')
    if group_ids is None:
        if group_min is not None or group_max is not None:
            raise ValueError('group limits require point ownership')
        groups = 0
    else:
        group_ids = np.asarray(group_ids)
        group_min = np.asarray(group_min,dtype=np.float64)
        if group_min.ndim != 1:
            raise ValueError('group minima must be a vector')
        groups = len(group_min)
        group_min = array(group_min,(groups,),'group_min')
        group_max = array(group_max,(groups,),'group_max')
        if (group_ids.shape != (k,) or group_ids.dtype.kind not in 'iu'
                or np.any(group_ids < 0) or np.any(group_ids >= groups)
                or np.any(group_min < 0) or np.any(group_max < group_min)):
            raise ValueError('invalid wheel group ownership or bounds')
    al = array(accel_lower, (22,), 'accel_lower')
    au = array(accel_upper, (22,), 'accel_upper')
    tl = array(effort_lower, (16,), 'effort_lower')
    tu = array(effort_upper, (16,), 'effort_upper')
    if np.any(al > au) or np.any(tl > tu):
        raise ValueError('invalid acceleration or effort interval')
    contact_matrix = np.asarray(contact_matrix, dtype=np.float64)
    if contact_matrix.ndim != 2 or contact_matrix.shape[1] != 22:
        raise ValueError('contact acceleration matrix must have22columns')
    contact_matrix = array(contact_matrix, contact_matrix.shape, 'contact_matrix')
    contact_rhs = array(contact_rhs, (len(contact_matrix),), 'contact_rhs')
    if separation_matrix is None:
        if separation_lower is not None:
            raise ValueError('separation lower bound requires its matrix')
        separation_matrix = np.empty((0,22))
        separation_lower = np.empty(0)
    else:
        separation_matrix = np.asarray(separation_matrix,dtype=np.float64)
        if separation_matrix.ndim != 2 or separation_matrix.shape[1] != 22:
            raise ValueError('separation acceleration matrix must have22columns')
        separation_matrix = array(separation_matrix,separation_matrix.shape,'separation_matrix')
        separation_lower = array(separation_lower,(len(separation_matrix),),'separation_lower')
    if len(tasks) > 4:
        raise ValueError('at most four task tiers')
    clean_tasks = []
    for task_a, task_b, task_w in tasks:
        task_a = np.asarray(task_a, dtype=np.float64)
        if task_a.ndim != 2 or task_a.shape[1] != 22 or len(task_a) == 0:
            raise ValueError('task matrix must have22columns and nonempty rows')
        task_a = array(task_a, task_a.shape, 'task_matrix')
        task_b = array(task_b, (len(task_a),), 'task_rhs')
        task_w = array(task_w, (len(task_a),), 'task_weight')
        if np.any(task_w <= 0):
            raise ValueError('task weights must be positive')
        clean_tasks.append((task_a, task_b, task_w))

    size = 38+3*k
    selection = np.vstack((np.zeros((6,16)), np.eye(16)))
    jt = jac.transpose(2,0,1).reshape(22,3*k)
    rows = [np.hstack((mass, -selection, -jt)),
            np.hstack((contact_matrix, np.zeros((len(contact_matrix),size-22)))),
            np.eye(size)[:38]]
    lows = [-bias, contact_rhs, np.r_[al,tl]]
    highs = [-bias, contact_rhs, np.r_[au,tu]]
    rows.append(np.hstack((separation_matrix,np.zeros((len(separation_matrix),size-22)))))
    lows.append(separation_lower)
    highs.append(np.full(len(separation_matrix),np.inf))
    for i in range(k):
        tangent1, tangent2, normal = frames[i].T
        directions = [normal, tangent1-mu[i]/np.sqrt(2)*normal,
                      -tangent1-mu[i]/np.sqrt(2)*normal,
                      tangent2-mu[i]/np.sqrt(2)*normal,
                      -tangent2-mu[i]/np.sqrt(2)*normal]
        force_rows = np.zeros((5,size))
        force_rows[:,38+3*i:41+3*i] = directions
        rows.append(force_rows)
        lows.append(np.array([normal_min[i],-np.inf,-np.inf,-np.inf,-np.inf]))
        highs.append(np.array([normal_max[i],0,0,0,0]))
    if groups:
        group_rows = np.zeros((groups,size))
        for i in range(k):
            group_rows[group_ids[i],38+3*i:41+3*i] = frames[i,:,2]
        rows.append(group_rows); lows.append(group_min); highs.append(group_max)
    a = np.vstack(rows); lower = np.concatenate(lows); upper = np.concatenate(highs)
    stage_reports = []

    def reject(reason, violation=None):
        return dict(valid=False,reason=reason,qdd=None,effort=None,force=None,
                    max_violation=violation,stages=stage_reports,identity=identity,
                    joint_names=joint_names)

    # Lock the achieved task vector, not the requested infeasible target. Strict
    # convexity in task output makes that vector unique for positive weights.
    for tier in [*clean_tasks, None]:
        p = np.eye(size)*1e-10
        q = np.zeros(size)
        if tier is not None:
            task_a, task_b, task_w = tier
            p[:22,:22] += task_a.T @ (task_w[:,None]*task_a)
            q[:22] -= task_a.T @ (task_w*task_b)
        else:
            p[22:,22:] += np.eye(size-22)*1e-6
        qp = osqp.OSQP()
        stage_started=time.perf_counter()
        qp.setup(P=sp.csc_matrix(p),q=q,A=sp.csc_matrix(a),l=lower,u=upper,
                 eps_abs=1e-8,eps_rel=1e-8,max_iter=10000,time_limit=.03,
                 polish=True,verbose=False)
        result = qp.solve()
        stage_reports.append(dict(status=result.info.status,iterations=result.info.iter,
                                  solve_time=result.info.run_time))
        if result.info.status_val != 1:
            from ame_baseline.m1_wbc_active_set import solve_active_set
            fallback=solve_active_set(p,q,a,lower,upper,
                time_limit=_CPU_ORACLE_STAGE_BUDGET_S-(time.perf_counter()-stage_started))
            stage_reports[-1].update(fallback_status=fallback['reason'],
                fallback_time=fallback['elapsed'])
            if not fallback['valid']:
                return reject(result.info.status+'; '+fallback['reason'])
            x=fallback['x']
        else:
            x = result.x
        if x is None or not np.isfinite(x).all():
            return reject('nonfinite_solution')
        actual = a@x
        violation = float(max(0.,np.max(lower-actual),np.max(actual-upper)))
        if violation > 1e-5:
            return reject('independent_constraint_check', violation)
        if tier is not None:
            lock = np.hstack((task_a,np.zeros((len(task_a),size-22))))
            achieved = task_a@x[:22]
            a = np.vstack((a,lock))
            lower = np.r_[lower,achieved-1e-7]
            upper = np.r_[upper,achieved+1e-7]
    return dict(valid=True,reason='solved',qdd=x[:22].copy(),effort=x[22:38].copy(),
                force=x[38:].reshape(k,3).copy(),max_violation=violation,
                dynamics_residual=(mass@x[:22]+bias-selection@x[22:38]-jt@x[38:]),
                stages=stage_reports,identity=identity,joint_names=joint_names)
