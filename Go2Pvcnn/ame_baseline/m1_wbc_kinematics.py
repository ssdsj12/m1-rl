"""Read-only rigid-tree bias accelerations for the CPU WBC oracle.

Generalized base acceleration is root COM world linear acceleration followed by
world angular acceleration. All supplied body rotations are actor frames, not
principal inertia frames. Returned biases have qdd=0 and do not include gravity.
These are material-body quantities, NOT constraints locking rolling contacts.
"""
import numpy as np


def kinematic_bias(model, joint_names, body_names, rotations, angular_velocities,
                   joint_velocities):
    names, jnames = tuple(body_names), tuple(joint_names)
    bodies, joints, root = model['bodies'], model['joints'], model['root']
    authored_b = [b['name'] for b in bodies]
    authored_j = [j['name'] for j in joints]
    if (len(set(names)) != len(names) or len(set(jnames)) != len(jnames)
            or len(set(authored_b)) != len(authored_b)
            or len(set(authored_j)) != len(authored_j)
            or set(names) != set(authored_b) or set(jnames) != set(authored_j)
            or root not in names):
        raise ValueError('unique complete named model/state correspondence required')
    children = [j['child'] for j in joints]
    if (len(set(children)) != len(children)
            or set(children) != set(names)-{root}
            or any(j['parent'] not in names for j in joints)):
        raise ValueError('each nonroot body requires one parent joint')
    r, w, qd = [np.asarray(x, dtype=np.float64) for x in
                (rotations, angular_velocities, joint_velocities)]
    if (r.shape != (len(names),3,3) or w.shape != (len(names),3)
            or qd.shape != (len(jnames),)
            or any(not np.isfinite(x).all() for x in (r,w,qd))):
        raise ValueError('finite named rotations/velocities required')
    if (not np.allclose(r.transpose(0,2,1)@r, np.eye(3),atol=1e-5,rtol=0)
            or not np.allclose(np.linalg.det(r),1.,atol=1e-5,rtol=0)):
        raise ValueError('actor orientations must be proper rotations')

    def vector(x, size):
        a = np.asarray(x,dtype=np.float64)
        if a.shape != (size,) or not np.isfinite(a).all():
            raise ValueError('invalid authored model vector')
        return a

    def quaternion(x):
        q = vector(x,4)
        if abs(np.linalg.norm(q)-1.) > 1e-4:
            raise ValueError('invalid authored joint quaternion')
        a,b,c,d = q/np.linalg.norm(q)
        return np.array([[1-2*(c*c+d*d),2*(b*c-a*d),2*(b*d+a*c)],
                         [2*(b*c+a*d),1-2*(b*b+d*d),2*(c*d-a*b)],
                         [2*(b*d-a*c),2*(c*d+a*b),1-2*(b*b+c*c)]])

    offsets = {b['name']:vector(b['com'],3) for b in bodies}
    frames = {}
    for j in joints:
        if j['axis'] not in ('X','Y','Z'):
            raise ValueError('unsupported joint axis')
        frames[j['name']] = (vector(j['pos0'],3),vector(j['pos1'],3),
                             quaternion(j['rot0']))
        quaternion(j['rot1'])
    idx = {n:i for i,n in enumerate(names)}
    ji = {n:i for i,n in enumerate(jnames)}
    origin = np.zeros_like(w); alpha = np.zeros_like(w)
    ri = idx[root]
    origin[ri] = -np.cross(w[ri],np.cross(w[ri],r[ri]@offsets[root]))
    done = {root}; pending = list(joints)
    while pending:
        progress = False
        for j in pending[:]:
            if j['parent'] not in done:
                continue
            p,c = idx[j['parent']],idx[j['child']]
            p0,p1,r0 = frames[j['name']]
            spin = r[p]@r0@np.eye(3)['XYZ'.index(j['axis'])]*qd[ji[j['name']]]
            if not np.allclose(w[c],w[p]+spin,atol=1e-5,rtol=0):
                raise ValueError('measured angular velocity inconsistent with joint tree')
            alpha[c] = alpha[p]+np.cross(w[p],spin)
            rp,rc = r[p]@p0,r[c]@p1
            origin[c] = (origin[p]+np.cross(alpha[p],rp)
                +np.cross(w[p],np.cross(w[p],rp))-np.cross(alpha[c],rc)
                -np.cross(w[c],np.cross(w[c],rc)))
            done.add(j['child']); pending.remove(j); progress = True
        if not progress:
            raise ValueError('disconnected or cyclic articulated model')
    arm = np.array([r[i]@offsets[n] for i,n in enumerate(names)])
    com = origin+np.cross(alpha,arm)+np.cross(w,np.cross(w,arm))
    if not all(np.isfinite(x).all() for x in (origin,com,alpha)):
        raise ValueError('nonfinite kinematic acceleration bias')
    return dict(origin_linear=origin,com_linear=com,angular=alpha,body_names=names)
