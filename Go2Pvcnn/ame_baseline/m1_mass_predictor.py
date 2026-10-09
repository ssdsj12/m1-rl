"""Named articulated pose/COM prediction, not contact or stability prediction.

Model uses body-local mass centers and parent/child joint frames from M1 USD.
Quaternion order is wxyz; angles are radians. Invalid rows return finite zeros
and valid=False, which callers must reject (zeros are not a safe reference).
No USD, Isaac, or GPU initialization occurs on import.
"""
import math
import torch


def load_usd_model(path):
    """Read authored masses/frames once; no stage mutation or physics startup."""
    from pxr import Usd, UsdPhysics
    stage=Usd.Stage.Open(str(path))
    if not stage:raise ValueError('cannot open M1 USD')
    bodies=[];joints=[]
    def quat(q):return [float(q.GetReal()),*map(float,q.GetImaginary())]
    for prim in Usd.PrimRange(stage.GetPseudoRoot(),Usd.TraverseInstanceProxies()):
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            mass=UsdPhysics.MassAPI(prim)
            bodies.append(dict(name=prim.GetName(),mass=mass.GetMassAttr().Get(),
                com=list(mass.GetCenterOfMassAttr().Get())))
        if prim.IsA(UsdPhysics.RevoluteJoint):
            joint=UsdPhysics.RevoluteJoint(prim)
            parent=joint.GetBody0Rel().GetTargets();child=joint.GetBody1Rel().GetTargets()
            if len(parent)!=1 or len(child)!=1:raise ValueError('invalid articulated joint endpoints')
            joints.append(dict(name=prim.GetName(),parent=parent[0].name,child=child[0].name,
                pos0=list(joint.GetLocalPos0Attr().Get()),pos1=list(joint.GetLocalPos1Attr().Get()),
                rot0=quat(joint.GetLocalRot0Attr().Get()),rot1=quat(joint.GetLocalRot1Attr().Get()),
                axis=joint.GetAxisAttr().Get()))
    roots={b['name'] for b in bodies}-{j['child'] for j in joints}
    if len(roots)!=1:raise ValueError('expected one articulated root')
    return dict(root=roots.pop(),bodies=bodies,joints=joints)


def _rotation(q):
    q=q/q.norm(dim=-1,keepdim=True).clamp_min(1e-12)
    w,x,y,z=q.unbind(-1)
    return torch.stack((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),
        2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),
        2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)),dim=-1).reshape(q.shape[:-1]+(3,3))


def predict(model,joint_names,q,root,root_quat):
    if q.ndim!=2 or not q.is_floating_point():
        raise ValueError('joint positions must be floating [B,J]')
    if root.shape!=(q.shape[0],3) or root_quat.shape!=(q.shape[0],4):
        raise ValueError('root pose shape mismatch')
    if any(t.device!=q.device or t.dtype!=q.dtype for t in (root,root_quat)):
        raise ValueError('pose tensors must share dtype and device')
    names=tuple(joint_names)
    bodies=model['bodies']; joints=model['joints']; root_name=model['root']
    bnames=tuple(b['name'] for b in bodies); jnames=tuple(j['name'] for j in joints)
    if len(set(names))!=len(names) or q.shape[1]!=len(names) or set(names)!=set(jnames) or len(set(jnames))!=len(jnames):
        raise ValueError('joint names must match the unique model joints')
    if len(set(bnames))!=len(bnames) or root_name not in bnames:
        raise ValueError('body names must be unique and contain root')
    def vector(value,n):
        t=q.new_tensor(value)
        if t.shape!=(n,) or not torch.isfinite(t).all():
            raise ValueError('invalid model vector')
        return t
    def frame(value):
        t=vector(value,4)
        if abs(float(t.norm())-1)>1e-4:raise ValueError('invalid joint quaternion')
        return _rotation(t)
    for b in bodies:
        if not math.isfinite(b['mass']) or b['mass']<=0:raise ValueError('mass must be positive finite')
        vector(b['com'],3)
    children=[j['child'] for j in joints]
    if len(set(children))!=len(children) or set(children)!=set(bnames)-{root_name}:
        raise ValueError('each nonroot body needs one joint')
    valid=torch.isfinite(q).all(-1)&torch.isfinite(root).all(-1)&torch.isfinite(root_quat).all(-1)
    valid &= (root_quat.norm(dim=-1)-1).abs()<=1e-4
    clean_q=torch.where(valid[:,None],q,0.)
    clean_root=torch.where(valid[:,None],root,0.)
    identity=q.new_tensor([1.,0.,0.,0.])
    clean_quat=torch.where(valid[:,None],root_quat,identity)
    poses={root_name:(_rotation(clean_quat),clean_root)}
    pending=list(joints)
    while pending:
        progressed=False
        for j in pending[:]:
            if j['parent'] not in poses:continue
            if j['axis'] not in ('X','Y','Z'):raise ValueError('unsupported joint axis')
            angle=clean_q[:,names.index(j['name'])]/2
            aq=torch.zeros((len(q),4),dtype=q.dtype,device=q.device)
            aq[:,0]=torch.cos(angle);aq[:,1+('X','Y','Z').index(j['axis'])]=torch.sin(angle)
            rp,tp=poses[j['parent']]
            rc=rp@frame(j['rot0'])@_rotation(aq)@frame(j['rot1']).T
            tc=tp+(rp@vector(j['pos0'],3))-(rc@vector(j['pos1'],3))
            poses[j['child']]=(rc,tc)
            pending.remove(j);progressed=True
        if not progressed:raise ValueError('disconnected or cyclic model')
    centers=torch.stack([poses[b['name']][1]+poses[b['name']][0]@vector(b['com'],3) for b in bodies],dim=1)
    mass=q.new_tensor([b['mass'] for b in bodies])
    com=(centers*mass[None,:,None]).sum(1)/mass.sum()
    return dict(com=torch.where(valid[:,None],com,0.),
        body_com=torch.where(valid[:,None,None],centers,0.),body_names=bnames,valid=valid)
