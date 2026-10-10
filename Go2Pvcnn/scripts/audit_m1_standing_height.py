"""CPU-only source-mesh standing-height calibration; no simulation or control."""
import json
import math
import sys
from pathlib import Path
import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ame_baseline.m1_mass_predictor import load_usd_model
from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS, M1_TRAINING_ROOT_Z_M
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES

asset=Path(__file__).resolve().parents[2]/'m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd'
model=load_usd_model(asset)
stage=Usd.Stage.Open(str(asset)); cache=UsdGeom.XformCache()

def rotation(q):
    w,x,y,z=np.array(q)/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
        [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
        [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

meshes=[]
body_names={b['name'] for b in model['bodies']}
for prim in Usd.PrimRange(stage.GetPseudoRoot(),Usd.TraverseInstanceProxies()):
    if not prim.IsA(UsdGeom.Mesh): continue
    body=prim
    while body and body.GetName() not in body_names: body=body.GetParent()
    if not body: raise ValueError('unassigned mesh '+str(prim.GetPath()))
    points=np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(),dtype=float)
    transform=np.asarray(cache.GetLocalToWorldTransform(prim)*cache.GetLocalToWorldTransform(body).GetInverse())
    points=(np.c_[points,np.ones(len(points))]@transform)[:,:3]
    meshes.append((body.GetName(),str(prim.GetPath()),points))

def measure(q,root_z):
    q=dict(zip(M1_ASSET_JOINT_NAMES,q));poses={model['root']:(np.eye(3),np.array([0.,0.,root_z]))}
    pending=list(model['joints'])
    while pending:
        before=len(pending)
        for j in pending[:]:
            if j['parent'] not in poses:continue
            axis=np.zeros(3);axis['XYZ'.index(j['axis'])]=math.sin(q[j['name']]/2)
            rp,tp=poses[j['parent']]
            rc=rp@rotation(j['rot0'])@rotation([math.cos(q[j['name']]/2),*axis])@rotation(j['rot1']).T
            tc=tp+rp@np.array(j['pos0'])-rc@np.array(j['pos1'])
            poses[j['child']]=(rc,tc);pending.remove(j)
        if before==len(pending):raise ValueError('disconnected joints')
    bounds=[]
    for body,path,points in meshes:
        r,t=poses[body];world=points@r.T+t
        bounds.append((float(world[:,2].min()),float(world[:,2].max()),path))
    low=min(bounds);high=max(bounds,key=lambda b:b[1])
    return dict(min_z=low[0],max_z=high[1],height=high[1]-low[0],
        lowest_mesh=low[2],highest_mesh=high[2])

current=measure(M1_TRAINING_JOINT_POS,M1_TRAINING_ROOT_Z_M)
lo,hi=.05,2.0
def pose(knee):
    hip=-math.atan2(.28*math.sin(knee),.26+.28*math.cos(knee))
    return (0.,hip,knee,0.)*4
assert measure(pose(lo),0)['height']>.585>measure(pose(hi),0)['height']
for _ in range(45):
    mid=(lo+hi)/2
    if measure(pose(mid),0)['height']>.585:lo=mid
    else:hi=mid
q=pose((lo+hi)/2);raw=measure(q,0);root=-raw['min_z']
print(json.dumps(dict(scope='source_mesh_kinematics_not_physical_stability',mesh_count=len(meshes),
    current=current,current_root_z=M1_TRAINING_ROOT_Z_M,
    candidate_joint_pos=q,candidate_root_z=root,candidate=measure(q,root)),indent=2))
