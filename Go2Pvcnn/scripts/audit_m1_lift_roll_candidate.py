"""CPU-only falsification of the undeployed candidate; never controls a robot.

Exit 2 means a geometry readiness gate fails, NOT a software-test failure.
No native simulation, policy action, reward change, or GPU initialization.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ame_baseline.m1_lift_roll_layout import candidate_blocks


def recovery_report(blocks):
    minimum = math.inf
    worst = None
    count = 0
    max_root = -math.inf
    for index, target in enumerate(b for b in blocks if b.required_crossing):
        for selected_x in (.3295,-.3295):
            for travel in np.linspace(0.,.045,6):
                root = target.x+target.length/2+.119208+.04-selected_x+float(travel)
                max_root = max(max_root,root)
                for wx in (.3295,-.3295):
                    for wy in (.215,-.215):
                        for bi,b in enumerate(blocks):
                            dx = max(abs(root+wx-b.x)-b.length/2,0.)
                            dy = max(abs(wy-b.y)-b.width/2,0.)
                            margin = math.hypot(dx,dy)-.119208
                            if margin < minimum:
                                minimum = margin
                                worst = dict(target=index,selected_x=selected_x,travel=float(travel),
                                             root_x=root,wheel_offset=[wx,wy],block=bi,fill=not b.required_crossing)
                count += 1
    return dict(samples=count,min_xy_margin=minimum,worst=worst,
                terminal_margin=7.25-max_root,pass_gate=minimum>0 and max_root<7.25)


def ground_connectivity(blocks):
    """Optimistic inscribed-disk model; 2mm grid, 8-connected, whole tile.

    Every oriented tire contains a sphere of radius thickness/2. Blocking only
    this disk leaves MORE free space than the true wheel. Discrete no-path is
    not a continuous/all-pose proof. No elevated surface traversal is modeled.
    """
    step,radius = .002,.02325
    axis = np.arange(-7.95,7.95+step/2,step)
    free = np.ones((len(axis),len(axis)),dtype=bool)
    for b in blocks:
        x0,x1 = np.searchsorted(axis,[b.x-b.length/2-radius,b.x+b.length/2+radius],side='left')
        y0,y1 = np.searchsorted(axis,[b.y-b.width/2-radius,b.y+b.width/2+radius],side='left')
        xs,ys = axis[x0:x1],axis[y0:y1]
        dx = np.maximum(np.abs(xs-b.x)-b.length/2,0.)
        dy = np.maximum(np.abs(ys-b.y)-b.width/2,0.)
        free[x0:x1,y0:y1] &= (dx[:,None]**2+dy[None,:]**2 > radius**2)
    seed = np.zeros_like(free)
    starts=[]
    for dx in (.3295,-.3295):
        for y in (.215,-.215):
            ix,iy = (np.abs(axis-(-2+dx)).argmin(),np.abs(axis-y).argmin())
            starts.append(bool(free[ix,iy]))
            seed[ix,iy] = free[ix,iy]
    reached = ndimage.binary_propagation(seed,structure=np.ones((3,3),dtype=bool),mask=free)
    return dict(grid_step_m=step,grid_shape=list(free.shape),inscribed_disk_radius=radius,
                starts_free=starts,reachable_cells=int(reached.sum()),
                any_reaches_x7=bool(reached[axis>=7].any()),
                max_reached_x=float(axis[np.where(reached)[0]].max()),
                limitation='ground-only optimistic disk; no continuous/all-pose certificate')


def top_bridge_report(blocks):
    """Exact circular-wheel vertical drop bridging adjacent equal-height edges.

    A straight elevated corridor is a readiness rejection, even without proof
    of the policy's ability to mount it from spawn. No learned bypass claim.
    """
    radius=.095958
    ys=(1.2+.215,1.2-.215)
    gaps=[]
    for y in ys:
        supports=sorted((b.x-b.length/2,b.x+b.length/2) for b in blocks
                        if not b.required_crossing and b.y-b.width/2+.02325<y<b.y+b.width/2-.02325)
        gaps += [right[0]-left[1] for left,right in zip(supports,supports[1:])]
    max_gap=max(gaps)
    bridged=all(0<gap<2*radius for gap in gaps)
    drop=radius-math.sqrt(radius**2-(max_gap/2)**2) if bridged else None
    return dict(root_y=1.2,wheel_ys=list(ys),gaps=len(gaps),max_gap=max_gap,
                wheel_radius=radius,all_gaps_bridgeable=bridged,max_center_drop=drop,
                pass_gate=not bridged,
                limitation='elevated straight rolling corridor; entry/torque/native feasibility unproven')


def source_mesh_report(asset):
    from pxr import Usd, UsdGeom, UsdPhysics
    from ame_baseline.m1_mass_predictor import load_usd_model
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS,M1_TRAINING_ROOT_Z_M
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES

    def rotation(q):
        w,x,y,z=np.asarray(q)/np.linalg.norm(q)
        return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                         [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                         [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

    model=load_usd_model(asset)
    stage=Usd.Stage.Open(str(asset));cache=UsdGeom.XformCache()
    names={b['name'] for b in model['bodies']}
    meshes=[]
    for prim in Usd.PrimRange(stage.GetPseudoRoot(),Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Mesh) or not prim.HasAPI(UsdPhysics.CollisionAPI):
            continue
        body=prim
        while body and body.GetName() not in names:
            body=body.GetParent()
        if not body:
            raise ValueError('unassigned mesh '+str(prim.GetPath()))
        points=np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(),dtype=float)
        transform=np.asarray(cache.GetLocalToWorldTransform(prim)*cache.GetLocalToWorldTransform(body).GetInverse())
        meshes.append((body.GetName(),str(prim.GetPath()),(np.c_[points,np.ones(len(points))]@transform)[:,:3]))
    if not meshes:
        raise ValueError('no source collision meshes')
    reports=[]
    # Nominal pose and bounded lateral perturbations, NOT an IK/control policy.
    for abad in (0.,-.05,.05,-.10,.10):
        joints=list(M1_TRAINING_JOINT_POS)
        for i in (0,4,8,12):
            joints[i]=abad
        q=dict(zip(M1_ASSET_JOINT_NAMES,joints))
        poses={model['root']:(np.eye(3),np.array([0.,0.,M1_TRAINING_ROOT_Z_M]))}
        pending=list(model['joints'])
        while pending:
            before=len(pending)
            for j in pending[:]:
                if j['parent'] not in poses:
                    continue
                axis=np.zeros(3);axis['XYZ'.index(j['axis'])]=math.sin(q[j['name']]/2)
                rp,tp=poses[j['parent']]
                rc=rp@rotation(j['rot0'])@rotation([math.cos(q[j['name']]/2),*axis])@rotation(j['rot1']).T
                tc=tp+rp@np.array(j['pos0'])-rc@np.array(j['pos1'])
                poses[j['child']]=(rc,tc);pending.remove(j)
            if before==len(pending):
                raise ValueError('disconnected joints')
        for height in (.03,.06,.10):
            margins=[];offenders=[]
            for body,path,points in meshes:
                r,t=poses[body];world=points@r.T+t
                low=world[(world[:,2]>=0)&(world[:,2]<=height+.003)]
                if not len(low):
                    continue
                # Distance inside union of two reserved strips at low heights.
                margin=.13-np.minimum(abs(low[:,1]-.215),abs(low[:,1]+.215))
                margins.append(float(margin.min()))
                if margin.min()<=0:
                    offenders.append(dict(body=body,path=path,min_margin=float(margin.min())))
            reports.append(dict(abad=abad,height=height,min_low_vertex_strip_margin=min(margins) if margins else None,
                                offenders=offenders))
    return dict(collision_mesh_count=len(meshes),poses=reports,
                limitation='source vertex envelope at bounded poses, not swept convex/native collision proof')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset',type=Path,required=True)
    parser.add_argument('--skip-grid',action='store_true')
    parser.add_argument('--fill-gap',type=float,default=.02)
    args=parser.parse_args()
    result=dict(scope='CPU candidate falsification only',fill_gap=args.fill_gap,rows=[])
    for row in (1,2,3):
        blocks=candidate_blocks(row,fill_gap=args.fill_gap)
        result['rows'].append(dict(row=row,targets=sum(b.required_crossing for b in blocks),
            fill=sum(not b.required_crossing for b in blocks),recovery=recovery_report(blocks),
            ground=None if args.skip_grid else ground_connectivity(blocks),top_bridge=top_bridge_report(blocks)))
    result['mesh']=source_mesh_report(args.asset)
    result['candidate_rejected']=any(not r['recovery']['pass_gate'] or not r['top_bridge']['pass_gate']
        or (r['ground'] is not None and (r['ground']['any_reaches_x7'] or not all(r['ground']['starts_free'])))
        for r in result['rows']) or any(p['offenders'] for p in result['mesh']['poses'])
    # The bounded tests can falsify a candidate, never certify all postures.
    result['native_readiness_proven']=False
    import torch
    result['cuda_initialized']=torch.cuda.is_initialized()
    print(json.dumps(result,indent=2))
    return 2 if result['candidate_rejected'] else 0


if __name__=='__main__':
    raise SystemExit(main())
