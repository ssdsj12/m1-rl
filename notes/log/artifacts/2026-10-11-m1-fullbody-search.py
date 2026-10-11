"""Offline bounded fixed-posture whole-robot C-space diagnostic, no actions."""
import sys, math, json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy import ndimage
from pxr import Usd, UsdGeom, UsdPhysics
sys.path.insert(0, str(Path('/tmp/m1-lift-roll-candidate-20261011/Go2Pvcnn')))
from ame_baseline.m1_mass_predictor import load_usd_model
from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS,M1_TRAINING_ROOT_Z_M
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
from ame_baseline.m1_lift_roll_layout import candidate_blocks

asset=Path('/root/quad/m1-rl/.worktrees/contact-recovery/m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd')
model=load_usd_model(asset);stage=Usd.Stage.Open(str(asset));cache=UsdGeom.XformCache()
names={b['name'] for b in model['bodies']};meshes=[]
for p in Usd.PrimRange(stage.GetPseudoRoot(),Usd.TraverseInstanceProxies()):
    if not p.IsA(UsdGeom.Mesh) or not p.HasAPI(UsdPhysics.CollisionAPI):continue
    body=p
    while body and body.GetName() not in names:body=body.GetParent()
    assert body
    pts=np.asarray(UsdGeom.Mesh(p).GetPointsAttr().Get(),float)
    tx=np.asarray(cache.GetLocalToWorldTransform(p)*cache.GetLocalToWorldTransform(body).GetInverse())
    pts=(np.c_[pts,np.ones(len(pts))]@tx)[:,:3]
    edges=set()
    for tri in ConvexHull(pts).simplices:
        for i,j in ((0,1),(1,2),(2,0)):edges.add(tuple(sorted((int(tri[i]),int(tri[j])))))
    meshes.append((body.GetName(),pts,np.array(sorted(edges))))

def rot(q):
    w,x,y,z=np.asarray(q)/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
       [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
       [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def pose_points(splay,inward=0.,joint_override=None):
    joints=list(M1_TRAINING_JOINT_POS)
    for i in (0,8):joints[i]=-inward
    for i in (4,12):joints[i]=inward
    for i in (1,5):joints[i]-=splay
    for i in (9,13):joints[i]+=splay
    if joint_override is not None:joints=list(joint_override)
    q=dict(zip(M1_ASSET_JOINT_NAMES,joints))
    poses={model['root']:(np.eye(3),np.array([0.,0.,M1_TRAINING_ROOT_Z_M]))}
    pending=list(model['joints'])
    while pending:
        before=len(pending)
        for j in pending[:]:
            if j['parent'] not in poses:continue
            axis=np.zeros(3);axis['XYZ'.index(j['axis'])]=math.sin(q[j['name']]/2)
            rp,tp=poses[j['parent']]
            rc=rp@rot(j['rot0'])@rot([math.cos(q[j['name']]/2),*axis])@rot(j['rot1']).T
            tc=tp+rp@np.array(j['pos0'])-rc@np.array(j['pos1'])
            poses[j['child']]=(rc,tc);pending.remove(j)
        assert len(pending)<before
    points=[(body,pts@poses[body][0].T+poses[body][1],edges) for body,pts,edges in meshes]
    bottoms=[float(p[:,2].min()) for b,p,e in points if 'FOOT_LINK' in b]
    shift=min(bottoms)
    return [(b,p-np.array([0,0,shift]),e) for b,p,e in points],dict(splay=splay,inward=inward,
        diagnostic_root_z=M1_TRAINING_ROOT_Z_M-shift,foot_bottom_spread=max(bottoms)-min(bottoms),
        joints=joints)

def lower_envelopes(points,height,yaw):
    c,s=math.cos(yaw),math.sin(yaw);r=np.array([[c,-s],[s,c]])
    envelopes=[]
    for name,pts,edges in points:
        plane=height+.003
        low=pts[pts[:,2]<=plane]
        if not len(low):continue
        a,b=pts[edges[:,0]],pts[edges[:,1]]
        crossing=((a[:,2]<plane)&(b[:,2]>plane))|((a[:,2]>plane)&(b[:,2]<plane))
        a,b=a[crossing],b[crossing]
        if len(a):
            alpha=(plane-a[:,2])/(b[:,2]-a[:,2])
            low=np.concatenate([low,a+alpha[:,None]*(b-a)])
        xy=low[:,:2]@r.T
        envelopes.append((name,xy.min(0),xy.max(0)))
    return envelopes

def root_free(blocks,envelopes,xs,ys,padding=.001):
    free=np.ones((len(xs),len(ys)),bool)
    for b in blocks:
        for name,lo,hi in envelopes:
            # Minkowski difference: obstacle rectangle minus robot envelope.
            xlo=b.x-b.length/2-hi[0]-padding;xhi=b.x+b.length/2-lo[0]+padding
            ylo=b.y-b.width/2-hi[1]-padding;yhi=b.y+b.width/2-lo[1]+padding
            ix0,ix1=np.searchsorted(xs,[xlo,xhi],side='left')
            iy0,iy1=np.searchsorted(ys,[ylo,yhi],side='left')
            free[ix0:ix1,iy0:iy1]=False
    return free

if '--lift-clearance' in sys.argv:
    from extension.parallelism.m1_kinematics import M1_HIP_LOWER,M1_HIP_UPPER,M1_KNEE_LOWER,M1_KNEE_UPPER
    reports=[]
    for row in (1,2,3):
        blocks=candidate_blocks(row,fill_gap=.20);height=blocks[0].height
        for leg,prefix in enumerate(('FBL','FAR','RBL','RAR')):
            chosen=None
            for delta in np.arange(.1,1.01,.05):
                joints=list(M1_TRAINING_JOINT_POS);joints[4*leg+1]-=float(delta)/2;joints[4*leg+2]+=float(delta)
                if not(M1_HIP_LOWER[leg]<=joints[4*leg+1]<=M1_HIP_UPPER[leg] and M1_KNEE_LOWER[leg]<=joints[4*leg+2]<=M1_KNEE_UPPER[leg]):continue
                points,info=pose_points(0,joint_override=joints)
                foot=next(p for b,p,e in points if b==prefix+'_FOOT_LINK')
                bottom=float(foot[:,2].min())
                if bottom>=height+.033:
                    chosen=(float(delta),points,info,bottom,float((foot[:,0].min()+foot[:,0].max())/2));break
            assert chosen is not None
            delta,points,info,bottom,fx=chosen
            envs=lower_envelopes(points,height,0.)
            targets=[b for b in blocks if b.required_crossing and (b.y>0)==(leg in (0,2))]
            checks=0;failures=[]
            for ti,target in enumerate(targets):
                roots=np.linspace(target.x-.05-.119208-.04-fx,target.x+.05+.119208+.04-fx,61)
                free=root_free(blocks,envs,roots,np.array([0.]),padding=.001)[:,0]
                checks+=len(roots)
                if not free.all():failures.append(dict(target_x=target.x,first_root_x=float(roots[np.where(~free)[0][0]])))
                # At the near/far endpoints check interpolated lift/lower geometries.
                for alpha in np.linspace(0,1,11):
                    js=list(M1_TRAINING_JOINT_POS);js[4*leg+1]-=delta/2*float(alpha);js[4*leg+2]+=delta*float(alpha)
                    pp,_=pose_points(0,joint_override=js)
                    ff=root_free(blocks,lower_envelopes(pp,height,0.),roots[[0,-1]],np.array([0.]),padding=.001)[:,0]
                    checks+=2
                    if not ff.all():failures.append(dict(target_x=target.x,lift_fraction=float(alpha),ends_free=ff.tolist()))
            reports.append(dict(row=row,leg=prefix,knee_delta=delta,hip_delta=-delta/2,
                wheel_bottom=bottom,required_bottom=height+.03,checks=checks,failures=failures,
                joints=info['joints']))
    print(json.dumps(dict(scope='source-convex AABB collision screening of hypothetical one-leg folds and body translation',
        reports=reports,limitations='Diagnostic FK grid, no IK/controller/actions/training data; not a swing prescription, not stability/no-slip/native or learned skill proof'),indent=2))
    raise SystemExit(0)

if '--layered' in sys.argv:
    from collections import deque, defaultdict
    step=.01;xs=np.arange(-2.8,7.25001,step);ys=np.arange(-1.8,1.80001,step)
    configs=[(0.,0.),(.06,0.),(.06,.10),(.06,.20),(.06,.25),(.06,.30),(.06,.35),(.06,.40)]
    yaws=np.deg2rad(np.arange(-30,31,10))
    reports=[]
    for row in (1,2,3):
        blocks=candidate_blocks(row,fill_gap=.20);labels={};graph=defaultdict(set)
        def mask(splay,inward,yaw):
            points,_=pose_points(splay,inward)
            return root_free(blocks,lower_envelopes(points,blocks[0].height,yaw),xs,ys,padding=.008)
        for ci,(sp,inn) in enumerate(configs):
            for yi,yaw in enumerate(yaws):
                labels[(ci,yi)]=ndimage.label(mask(sp,inn,yaw),structure=np.ones((3,3)))[0]
        for key,lab in labels.items():
            ci,yi=key
            for nxt in ((ci+1,yi),(ci,yi+1)):
                if nxt not in labels:continue
                other=labels[nxt];valid=(lab>0)&(other>0)
                for alpha in (.25,.5,.75):
                    a=np.array([*configs[ci],yaws[yi]])
                    b=np.array([*configs[nxt[0]],yaws[nxt[1]]])
                    valid &= mask(*(a+(b-a)*alpha))
                pairs=np.unique(np.stack([lab[valid],other[valid]],axis=1),axis=0)
                for la,lb in pairs:
                    n1=(*key,int(la));n2=(*nxt,int(lb))
                    graph[n1].add(n2);graph[n2].add(n1)
        start=(int(abs(xs+2).argmin()),int(abs(ys).argmin()))
        node=(0,3,int(labels[(0,3)][start]));seen={node} if node[-1] else set();todo=deque(seen)
        while todo:
            for n in graph[todo.popleft()]:
                if n not in seen:seen.add(n);todo.append(n)
        max_x=None;exits=[]
        for ci,yi,label in seen:
            ij=np.argwhere(labels[(ci,yi)]==label)
            local_x=float(xs[ij[:,0]].max())
            max_x=local_x if max_x is None else max(max_x,local_x)
            if local_x>=7:exits.append(dict(config=configs[ci],yaw=float(yaws[yi]),max_root_x=local_x))
        reports.append(dict(row=row,start_free=bool(node[-1]),reaches_exit=bool(exits),
            max_root_x=max_x,reachable_config_regions=len(seen),exits=exits))
    print(json.dumps(dict(scope='bounded multi-posture/yaw clipped-convex AABB graph',
        configs=configs,yaw_degrees=list(range(-30,31,10)),xy_step=step,padding=.008,
        transition_samples=[0,.25,.5,.75,1],reports=reports,
        limitations='No-path is not all-pose proof; sampled transitions, holonomic, no self-collision/no-slip/dynamics/native/policy proof'),indent=2))
    raise SystemExit(0)

reports=[]
step=.002;xs=np.arange(-2.8,7.25001,step);ys=np.arange(-1.8,1.80001,step)
for splay,inward in ((0.,0.),(.06,0.),(.06,.25),(.06,.30),(.06,.35),(.06,.40)):
    points,info=pose_points(splay,inward)
    for row in (1,2,3):
        blocks=candidate_blocks(row,fill_gap=.20)
        # Fixed +X yaw first. This admits holonomic translation, not no-slip steering.
        envelopes=lower_envelopes(points,blocks[0].height,0.)
        free=root_free(blocks,envelopes,xs,ys)
        start=(int(abs(xs+2).argmin()),int(abs(ys).argmin()))
        seed=np.zeros_like(free);seed[start]=free[start]
        reached=ndimage.binary_propagation(seed,structure=np.ones((3,3),bool),mask=free)
        exit_cells=np.argwhere(reached & (xs[:,None]>=7.0))
        report=dict(row=row,pose=info,start_free=bool(free[start]),
            reaches_exit=bool(len(exit_cells)),max_root_x=float(xs[np.where(reached)[0]].max()) if reached.any() else None,
            reachable_cells=int(reached.sum()),grid_step=step,padding=.001,
            low_convex_meshes=len(envelopes),yaw=0.)
        if len(exit_cells):report['exit_root_xy']=[float(xs[exit_cells[0,0]]),float(ys[exit_cells[0,1]])]
        reports.append(report)
print(json.dumps(dict(scope='fixed-posture clipped-source-convex AABB whole-body C-space, holonomic only',
    limitations='No-path is not all-pose proof; path is geometric only, no self-collision/no-slip/stability/native/policy proof; diagnostic postures never deployed',
    reports=reports),indent=2))
