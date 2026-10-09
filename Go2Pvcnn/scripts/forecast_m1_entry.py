"""CPU causal entry-only forecast; does not send robot commands."""
import ast
import contextlib
import io
import itertools
import json
import runpy
import sys
import torch
from ame_baseline.m1_anticipatory_support import forecast_lift,choose_pose
from extension.parallelism.m1_kinematics import M1_WHEEL_JOINT_NAMES
from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES,m1_ik
from ame_baseline.m1_com_trajectory import root_step

torch.set_num_threads(2)
with contextlib.redirect_stdout(io.StringIO()):
    inv=runpy.run_path('scripts/inspect_m1_mass_tree.py')
model=dict(root='BASE_LINK',bodies=[dict(name=b['name'],mass=b['mass'],com=b['com']) for b in inv['bodies']],joints=[])
for j in inv['joints']:
    if j['type']=='PhysicsRevoluteJoint':
        model['joints'].append(dict(name=j['name'],parent=j['parent'][0].split('/')[-1],child=j['child'][0].split('/')[-1],
            pos0=j['pos0'],pos1=j['pos1'],rot0=ast.literal_eval(j['rot0']),rot1=ast.literal_eval(j['rot1']),axis=j['axis']))
data=next(json.loads(s[len('M1_CONTACT_PREPARE '):]) for s in open(sys.argv[1]) if s.startswith('M1_CONTACT_PREPARE '))
# Only stage-entry snapshot, frozen anchors and selected identity consumed.
entry=data['entry_snapshot'];anchors=data['entry_anchor_w'];selected=data['selected_leg']
t=lambda x:torch.tensor(x,dtype=torch.float64)
grid=t(list(itertools.product((0.,.02,.04,.06,.07,.075,.0799),(-.6,-.4,-.2,0.,.2,.4,.6),(-.06,-.04,-.02,0.,.02,.04,.06),(-.06,-.04,-.02,0.,.02,.04,.06))))
for row in range(len(selected)):
    origin=t(entry['root'][row:row+1]);rpy=t(entry['rpy'][row:row+1]);anchor=t(anchors[row:row+1]);leg=selected[row]
    ids=[i for i in range(4) if i!=leg]
    direction=anchor[0,ids,:2].mean(0)-origin[0,:2]
    angle=torch.atan2(direction[1],direction[0])+grid[:,1]
    roots=origin[:,None].expand(1,len(grid),3).clone()
    roots[0,:,0]+=grid[:,0]*angle.cos();roots[0,:,1]+=grid[:,0]*angle.sin()
    rpys=rpy[:,None].expand_as(roots).clone();rpys[0,:,:2]+=grid[:,2:]
    wheel=t([[entry['joint_position'][row][entry['joint_names'].index(n)] for n in M1_WHEEL_JOINT_NAMES]])
    forecast=forecast_lift(model=model,roots=roots,rpys=rpys,anchors=anchor,
        selected=torch.tensor([leg]),wheel_q=wheel,heights=torch.linspace(0.,.16,17,dtype=roots.dtype))
    choice=choose_pose(entry_root=origin,entry_rpy=rpy,roots=roots,rpys=rpys,
        **{key:forecast[key] for key in ('min_load','min_margin','reachable')})
    index=int(choice['index'][0]);valid=bool(choice['valid'][0])
    print(json.dumps(dict(row=row,valid=valid,candidates=len(grid),eligible=int(choice['candidate_valid'].sum()),
        root_delta_mm=((choice['root']-origin)*1000).tolist(),rpy_delta=(choice['rpy']-rpy).tolist(),
        min_load=float(forecast['min_load'][0,index].min()) if valid else None,
        min_margin_mm=float(forecast['min_margin'][0,index].min()*1000) if valid else None)))
    if '--audit-transfer' in sys.argv and valid:
        # Proposed four-second offline budget only; no live timeout change.
        p=origin.clone();v=torch.zeros(1,2,dtype=p.dtype)
        previous=t([[entry['joint_position'][row][entry['joint_names'].index(n)] for n in M1_PLANNER_JOINT_NAMES]])
        max_slew=0.;all_valid=True;first_ready=None
        for step in range(1,201):
            ramp=root_step(origin,p,v,choice['root'],dt=.02)
            p,v=ramp['root'],ramp['velocity']
            q,reachable=m1_ik(p,rpy,anchor);q=q.reshape(1,12)
            max_slew=max(max_slew,float((q-previous).abs().max()/.02));previous=q
            all_valid &= bool(ramp['valid'].all()&reachable.all())
            if first_ready is None and (p-choice['root']).norm()<=.001 and v.norm()<=.001:first_ready=step*.02
        print(json.dumps(dict(transfer_row=row,offline_budget=4.,all_ik_reference_valid=all_valid,
            max_joint_speed=max_slew,within_joint_slew=max_slew<=.5,
            reference_ready_seconds=first_ready,final_error_mm=float((p-choice['root']).norm()*1000),
            final_speed_mm_s=float(v.norm()*1000))))
