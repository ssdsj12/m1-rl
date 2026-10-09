"""CPU audit: original triangle surface height from recorded link poses."""
import json
import numpy as np
from pxr import Usd, UsdGeom

stage=Usd.Stage.Open('/home/hexinkun/m1_rl/.worktrees/m1-contact-crossing/m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd')
body=stage.GetPrimAtPath('/ZJ_V3_URDF_V1_0/RAR_FOOT_LINK')
mesh=UsdGeom.Mesh(stage.GetPrimAtPath(str(body.GetPath())+'/collisions/RAR_FOOT_LINK/mesh'))
cache=UsdGeom.XformCache()
relative=np.asarray(cache.GetLocalToWorldTransform(mesh.GetPrim())*cache.GetLocalToWorldTransform(body).GetInverse())
points=np.asarray(mesh.GetPointsAttr().Get(),dtype=np.float64)
points=points@relative[:3,:3]+relative[3,:3]
prefix='M1_STANDING_CONTACT_SUBSTEPS '
previous=None
with open('/tmp/m1_sdf_contact_pose_20261007.log') as stream:
    for line in stream:
        if not line.startswith(prefix): continue
        row=json.loads(line[len(prefix):])
        for sub,snapshot in enumerate(row['records']):
            q=np.asarray(snapshot['wheel_quat_wxyz'][3],dtype=np.float64)
            if abs(np.linalg.norm(q)-1)>1e-4: raise ValueError('nonunit pose quaternion')
            w,x,y,z=q/np.linalg.norm(q)
            rz=np.array([2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)])
            minimum=float((points@rz).min()+snapshot['wheel_center'][3][2])
            if row['phase']=='standing' and row['step']==2:
                print(json.dumps(dict(sub=sub,original_surface_min_z=minimum,
                    previous_surface_min_z=previous,native_normal=snapshot['pair_net'][0][2],
                    reported_separation_min=min(snapshot['pairs'][0]['separation']))))
            previous=minimum
