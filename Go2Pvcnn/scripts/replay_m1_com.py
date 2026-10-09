"""Read-only FK/COM replay against existing native wheel and COM telemetry.

Rigid pose is fitted from the root and four wheel centers because historical
samples do not record the root quaternion. This is not an independent attitude
measurement or a dynamic support predictor.
"""
import json
import sys
import numpy as np
from pxr import Usd, UsdPhysics, Gf

stage = Usd.Stage.Open('/home/hexinkun/m1_rl/.worktrees/m1-contact-crossing/m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd')
bodies = {}
joints = []
for p in stage.Traverse():
    if p.HasAPI(UsdPhysics.RigidBodyAPI):
        m = UsdPhysics.MassAPI(p)
        bodies[p.GetName()] = (m.GetMassAttr().Get(), np.array(m.GetCenterOfMassAttr().Get()))
    if p.IsA(UsdPhysics.RevoluteJoint):
        j = UsdPhysics.Joint(p)
        joints.append((p.GetName(), j.GetBody0Rel().GetTargets()[0].name,
            j.GetBody1Rel().GetTargets()[0].name,
            np.array(j.GetLocalPos0Attr().Get()), np.array(j.GetLocalPos1Attr().Get()),
            np.array(Gf.Matrix3d(j.GetLocalRot0Attr().Get())).T,
            np.array(Gf.Matrix3d(j.GetLocalRot1Attr().Get())).T,
            p.GetAttribute('physics:axis').Get()))
legs = ('FBL','FAR','RBL','RAR')
names = [f'{l}_{j}_JOINT' for l in legs for j in ('ABAD','HIP','KNEE')]
record = next(json.loads(line[len('M1_CONTACT_PREPARE '):]) for line in open(sys.argv[1]) if line.startswith('M1_CONTACT_PREPARE '))
results=[]
for s in record['lift_samples']:
    for row,q in enumerate(s['joint_actual']):
        angles=dict(zip(names,q))
        angles.update({f'{l}_FOOT_JOINT':s['wheel_joint_position'][row][i] for i,l in enumerate(legs)})
        poses={'BASE_LINK':(np.eye(3),np.zeros(3))}
        pending=list(joints)
        while pending:
            progressed=False
            for j in pending[:]:
                name,parent,child,p0,p1,r0,r1,axis=j
                if parent not in poses: continue
                axisvec={'X':Gf.Vec3d(1,0,0),'Y':Gf.Vec3d(0,1,0),'Z':Gf.Vec3d(0,0,1)}[axis]
                rotation=np.array(Gf.Matrix3d(Gf.Rotation(axisvec,np.degrees(angles[name])))).T
                rp,tp=poses[parent]
                rc=rp@r0@rotation@r1.T
                poses[child]=(rc,tp+rp@p0-rc@p1)
                pending.remove(j); progressed=True
            assert progressed, 'disconnected joint tree'
        local=np.array([np.zeros(3)]+[poses[f'{l}_FOOT_LINK'][1] for l in legs])
        world=np.array([s['root_w'][row]]+s['wheel_pos_w'][row])
        a,b=local.mean(0),world.mean(0)
        u,_,vt=np.linalg.svd((local-a).T@(world-b))
        sign=np.eye(3);sign[2,2]=np.linalg.det(vt.T@u.T)
        rot=vt.T@sign@u.T; trans=b-rot@a
        mass=sum(m for m,c in bodies.values())
        com=sum(m*(poses[n][0]@c+poses[n][1]) for n,(m,c) in bodies.items())/mass
        native={}
        if 'root_quat_w' in s:
            qw,qx,qy,qz=s['root_quat_w'][row]
            direct_rot=np.array(Gf.Matrix3d(Gf.Quatd(qw,Gf.Vec3d(qx,qy,qz)))).T
            direct_root=np.array(s['root_w'][row])
            native=dict(direct_com_error=float(np.linalg.norm(direct_rot@com+direct_root-np.array(s['com_w'][row]))),
                direct_body_error=max(float(np.linalg.norm(direct_rot@(poses[n][0]@bodies[n][1]+poses[n][1])+direct_root-np.array(actual)))
                    for n,actual in zip(s['body_names'],s['body_com_w'][row])))
        results.append(dict(step=s['step'],row=row,phase=s['phase'],
            fit_error=float(np.max(np.linalg.norm(local@rot.T+trans-world,axis=1))),
            com_error=float(np.linalg.norm(rot@com+trans-np.array(s['com_w'][row]))),**native))
print(json.dumps(dict(samples=len(results),bodies=len(bodies),joints=len(joints),
    max_direct_com_error=max((r['direct_com_error'] for r in results if 'direct_com_error' in r),default=None),
    max_direct_body_error=max((r['direct_body_error'] for r in results if 'direct_body_error' in r),default=None),
    max_fit_error=max(r['fit_error'] for r in results),
    max_com_error=max(r['com_error'] for r in results),
    worst=sorted(results,key=lambda r:r['com_error'],reverse=True)[:4]),indent=2))
