"""Offline bounded pose feasibility, not a controller or dynamic proof."""
import ast
import contextlib
import io
import itertools
import json
import runpy
import sys
import torch
from ame_baseline.m1_mass_predictor import predict
from extension.parallelism.m1_kinematics import m1_ik

torch.set_num_threads(2)
with contextlib.redirect_stdout(io.StringIO()):
    inventory=runpy.run_path('scripts/inspect_m1_mass_tree.py')
model=dict(root='BASE_LINK',bodies=[dict(name=b['name'],mass=b['mass'],com=b['com']) for b in inventory['bodies']],joints=[])
for j in inventory['joints']:
    if j['type']=='PhysicsRevoluteJoint':
        model['joints'].append(dict(name=j['name'],parent=j['parent'][0].split('/')[-1],child=j['child'][0].split('/')[-1],
            pos0=j['pos0'],pos1=j['pos1'],rot0=ast.literal_eval(j['rot0']),rot1=ast.literal_eval(j['rot1']),axis=j['axis']))
record=next(json.loads(line[len('M1_CONTACT_PREPARE '):]) for line in open(sys.argv[1]) if line.startswith('M1_CONTACT_PREPARE '))
sample=next(s for s in record['lift_samples'] if s['step']==89)
entry=record['samples'][0]['root_w']
legs=('FBL','FAR','RBL','RAR')
names=[f'{l}_{j}_JOINT' for l in legs for j in ('ABAD','HIP','KNEE')]+[f'{l}_FOOT_JOINT' for l in legs]
tensor=lambda x:torch.tensor(x,dtype=torch.float64)
grid=tensor(list(itertools.product((.04,.06,.07,.075,.0799),(-.5,-.3,-.1,0.,.1,.3,.5),(-.06,-.04,-.02,0.,.02,.04,.06),(-.06,-.04,-.02,0.,.02,.04,.06))))
for row in range(8):
    w,x,y,z=tensor(sample['root_quat_w'][row])
    base_rpy=torch.stack((torch.atan2(2*(w*x+y*z),1-2*(x*x+y*y)),torch.asin((2*(w*y-z*x)).clamp(-1,1)),torch.atan2(2*(w*z+x*y),1-2*(y*y+z*z))))
    rpy=base_rpy.expand(len(grid),3).clone();rpy[:,:2]+=grid[:,2:]
    origin=tensor(entry[row]);root=tensor(sample['root_w'][row]).expand(len(grid),3).clone()
    angle=torch.atan2(root[0,1]-origin[1],root[0,0]-origin[0])+grid[:,1]
    root[:,0]=origin[0]+grid[:,0]*angle.cos();root[:,1]=origin[1]+grid[:,0]*angle.sin()
    root[:,2]=origin[2]
    anchors=tensor(sample['wheel_pos_w'][row]).expand(len(grid),4,3)
    if '--entry-anchors' in sys.argv:
        anchors=tensor(record['entry_anchor_w'][row]).expand(len(grid),4,3).clone()
        anchors[:,row%4,2]+=.16
    q,reachable=m1_ik(root,rpy,anchors)
    half=rpy/2;cr,cp,cy=half.cos().unbind(-1);sr,sp,sy=half.sin().unbind(-1)
    quat=torch.stack((cr*cp*cy+sr*sp*sy,sr*cp*cy-cr*sp*sy,cr*sp*cy+sr*cp*sy,cr*cp*sy-sr*sp*cy),-1)
    wheel=tensor(sample['wheel_joint_position'][row]).expand(len(grid),4)
    out=predict(model,names,torch.cat((q.reshape(-1,12),wheel),1),root,quat)
    support=[i for i in range(4) if i!=row%4]
    triangle=anchors[0,support,:2]
    matrix=torch.cat((triangle.T,torch.ones(1,3,dtype=root.dtype)),0)
    rhs=torch.cat((out['com'][:,:2],torch.ones(len(grid),1,dtype=root.dtype)),1)
    forces=torch.linalg.solve(matrix,rhs.T).T*sum(b['mass'] for b in model['bodies'])*9.81
    edge=triangle.roll(-1,0)-triangle
    area=torch.linalg.det(torch.stack((triangle[1]-triangle[0],triangle[2]-triangle[0])))
    inward=torch.stack((-edge[:,1],edge[:,0]),-1)*area.sign()/edge.norm(dim=-1)[:,None]
    margin=((out['com'][:,None,:2]-triangle)*inward).sum(-1).min(-1).values
    valid=out['valid']&reachable.all(-1)&((root-origin).norm(dim=-1)<=.08)&(rpy[:,:2].abs().max(-1).values<=.15)&(grid[:,2:].norm(dim=-1)<=.08)&(margin>=.02)
    score=torch.where(valid,forces.min(-1).values,-torch.inf)
    best=score.argmax()
    print(json.dumps(dict(row=row,selected=legs[row%4],candidates=len(grid),valid=int(valid.sum()),
        entry_anchors='--entry-anchors' in sys.argv,
        measured_entry_shift_mm=float((tensor(sample['root_w'][row])-origin).norm()*1000),
        feasible35=int((valid&(forces.min(-1).values>=35)).sum()),
        best_min_force=float(score[best]),root_shift_mm=((root[best]-origin)*1000).tolist(),
        rpy_delta=grid[best,2:].tolist(),margin_mm=float(margin[best]*1000))))
