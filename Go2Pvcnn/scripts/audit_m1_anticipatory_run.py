"""Read-only decomposition of entry reference vs measured support geometry."""
import json,sys,torch
from ame_baseline.m1_anticipatory_support import forecast_lift
from ame_baseline.m1_mass_predictor import load_usd_model,predict
from extension.parallelism.m1_kinematics import m1_fk,M1_PLANNER_JOINT_NAMES,M1_WHEEL_JOINT_NAMES
from ame_baseline.m1_load_transfer import _nearest_halfplane_point
from pathlib import Path
rows={}
for line in open(sys.argv[1]):
    for tag in ('M1_CONTACT_PREPARE','M1_ANTICIPATORY_ENTRY','M1_PHASE_EFFORT'):
        if line.startswith(tag+' '):rows[tag]=json.loads(line[len(tag)+1:])
d=rows['M1_CONTACT_PREPARE'];p=rows['M1_ANTICIPATORY_ENTRY'];last=d['lift_samples'][-1]
model=load_usd_model(Path(__file__).resolve().parents[2]/'m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd')
weight=sum(b['mass'] for b in model['bodies'])*9.81
t=lambda x:torch.tensor(x,dtype=torch.float64)
def loads(com,wheels,leg):
    tri=t([v[:2] for i,v in enumerate(wheels) if i!=leg]);edge=tri.roll(-1,0)-tri
    ab=tri[1]-tri[0];ac=tri[2]-tri[0];area=ab[0]*ac[1]-ab[1]*ac[0]
    inward=torch.stack((-edge[:,1],edge[:,0]),-1)*area.sign()/edge.norm(dim=-1)[:,None]
    return ((t(com[:2])-tri)*inward).sum(-1)/(area.abs()/edge.norm(dim=-1))*weight
def quat(rpy):
    h=rpy/2;cr,cp,cy=h.cos().unbind(-1);sr,sp,sy=h.sin().unbind(-1)
    return torch.stack((cr*cp*cy+sr*sp*sy,sr*cp*cy-cr*sp*sy,cr*sp*cy+sr*cp*sy,cr*cp*sy-sr*sp*cy),-1)
def bounded_support_need(com,wheels,leg,entry,command):
    tri=t([v[:2] for j,v in enumerate(wheels) if j!=leg]);edge=tri.roll(-1,0)-tri
    ab=tri[1]-tri[0];ac=tri[2]-tri[0];area=ab[0]*ac[1]-ab[1]*ac[0]
    length=edge.norm(dim=-1)
    inward=torch.stack((-edge[:,1],edge[:,0]),-1)*area.sign()/length[:,None]
    distance=((t(com[:2])+t(entry[:2])-t(command[:2])-tri)*inward).sum(-1)
    required=torch.maximum(torch.full_like(distance,.02),area.abs()/length*35./weight)
    shift,valid=_nearest_halfplane_point(inward[None],(required-distance)[None])
    return float(shift.norm()*1000),bool(valid[0])
for i,leg in enumerate(d['selected_leg']):
    root=t(p['root'][i:i+1]);rpy=t(p['rpy'][i:i+1])
    forecast=forecast_lift(model=model,roots=root[:,None],rpys=rpy[:,None],
        anchors=t(d['entry_anchor_w'][i:i+1]),selected=torch.tensor([leg]),
        wheel_q=t(last['wheel_joint_position'][i:i+1]),heights=t([0.,last['measured_rise'][i]]))
    nominal_com=forecast['com'][0,0,-1].tolist()
    measured_static=loads(last['com_w'][i],last['wheel_pos_w'][i],leg)
    frozen_static=loads(last['com_w'][i],d['entry_anchor_w'][i],leg)
    # A rigid global translation of COM AND contacts cannot change support.
    # Reconstruct measured joint deformation at the nominal entry attitude to
    # separate joint tracking from attitude, not blame world drift by itself.
    actual_q=t(last['joint_actual'][i:i+1]);command_q=t(last['joint_target'][i:i+1])
    wheel_q=t(last['wheel_joint_position'][i:i+1])
    relaxed=predict(model,M1_PLANNER_JOINT_NAMES+M1_WHEEL_JOINT_NAMES,
        torch.cat((actual_q,wheel_q),-1),root,quat(rpy))
    relaxed_wheels=m1_fk(root,rpy,actual_q).foot_pos_w
    relaxed_load=loads(relaxed['com'][0].tolist(),relaxed_wheels[0].tolist(),leg).min()
    actual_quat=t(last['root_quat_w'][i:i+1]);w,x,y,z=actual_quat.unbind(-1)
    actual_rpy=torch.stack((torch.atan2(2*(w*x+y*z),1-2*(x*x+y*y)),
        torch.asin((2*(w*y-z*x)).clamp(-1,1)),torch.atan2(2*(w*z+x*y),1-2*(y*y+z*z))),-1)
    actual_root=t(last['root_w'][i:i+1])
    reconstructed=predict(model,M1_PLANNER_JOINT_NAMES+M1_WHEEL_JOINT_NAMES,
        torch.cat((actual_q,wheel_q),-1),actual_root,actual_quat)
    reconstructed_wheels=m1_fk(actual_root,actual_rpy,actual_q).foot_pos_w
    reconstruction_load=loads(reconstructed['com'][0].tolist(),reconstructed_wheels[0].tolist(),leg).min()
    required_shift,linear_valid=bounded_support_need(last['com_w'][i],last['wheel_pos_w'][i],leg,
        d['entry_snapshot']['root'][i],last['previous_root_command'][i])
    print(json.dumps(dict(row=i,leg=leg,nominal_lift_static_min_N=float(forecast['min_load'][0,0,-1]),
        measured_geometry_static_min_N=float(measured_static.min()),
        measured_COM_frozen_support_min_N=float(frozen_static.min()),
        COM_error_mm=((t(last['com_w'][i])-t(nominal_com))*1000).tolist(),
        root_error_mm=((t(last['root_w'][i])-root[0])*1000).tolist(),
        measured_rise_mm=last['measured_rise'][i]*1000,
        measured_support_min_N=min(f for j,f in enumerate(last['force'][i]) if j!=leg),
        realized_joints_entry_attitude_min_N=float(relaxed_load),
        reconstructed_actual_min_N=float(reconstruction_load),
        instantaneous_35N_min_entry_shift_mm=required_shift,linear_support_valid=linear_valid,
        joint_tracking_error_deg=((actual_q-command_q)[0]*180/torch.pi).tolist())))
