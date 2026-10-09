"""Choose bounded entry-time pose from sampled static support forecasts.

Each candidate must satisfy every supplied sample, not merely the lift apex.
Caller owns causal candidate generation, sufficient sampling, dynamics, effort,
continuous collision checks and safe execution. This is not crossing success.
Invalid row has index=-1; returned entry pose is NOT a verified recovery action.
"""
import torch


def entry_plan(*,model,root,rpy,anchors,selected,wheel_q,height,translation_only=False):
    """Entry-only finite candidate search; no future telemetry or live control."""
    import itertools
    import math
    if not math.isfinite(height) or not 0<height<=.3:raise ValueError('invalid lift height')
    if type(translation_only) is not bool:raise ValueError('invalid executor capability')
    attitude_grid=(0.,) if translation_only else (-.06,-.04,-.02,0.,.02,.04,.06)
    grid=root.new_tensor(list(itertools.product((0.,.02,.04,.06,.07,.075,.0799),
        (-.6,-.4,-.2,0.,.2,.4,.6),attitude_grid,attitude_grid)))
    outputs=[]
    for row in range(len(root)):
        leg=int(selected[row]);origin=root[row:row+1];orientation=rpy[row:row+1]
        if not 0<=leg<4:raise ValueError('leg index')
        direction=anchors[row,[i for i in range(4) if i!=leg],:2].mean(0)-origin[0,:2]
        angle=torch.atan2(direction[1],direction[0])+grid[:,1]
        roots=origin[:,None].expand(1,len(grid),3).clone()
        roots[0,:,0]+=grid[:,0]*angle.cos();roots[0,:,1]+=grid[:,0]*angle.sin()
        rpys=orientation[:,None].expand_as(roots).clone();rpys[0,:,:2]+=grid[:,2:]
        forecasts=forecast_lift(model=model,roots=roots,rpys=rpys,anchors=anchors[row:row+1],
            selected=selected[row:row+1],wheel_q=wheel_q[row:row+1],
            heights=torch.linspace(0.,height,17,device=root.device,dtype=root.dtype))
        chosen=choose_pose(entry_root=origin,entry_rpy=orientation,roots=roots,rpys=rpys,
            **{k:forecasts[k] for k in ('min_load','min_margin','reachable')})
        outputs.append({k:chosen[k] for k in ('root','rpy','valid')})
    return {k:torch.cat([o[k] for o in outputs],0) for k in ('root','rpy','valid')}


def fixed_reference_step(*,entry,rpy,anchors,previous,velocity,previous_joint,goal,dt):
    """Bounded fixed-entry translation; ready flag is reference convergence only."""
    from ame_baseline.m1_com_trajectory import root_step
    from extension.parallelism.m1_kinematics import m1_ik,m1_joint_limit_mask
    ramp=root_step(entry,previous,velocity,goal,dt=dt)
    q,reachable=m1_ik(ramp['root'],rpy,anchors);q=q.reshape(-1,12)
    valid=ramp['valid']&reachable.all(-1)&m1_joint_limit_mask(q)&m1_joint_limit_mask(previous_joint)
    valid &= ((q-previous_joint).abs()<=.5*dt+1e-7).all(-1)
    ready=valid&((ramp['root']-goal).norm(dim=-1)<=.001)&(ramp['velocity'].norm(dim=-1)<=.001)
    return dict(root=torch.where(valid[:,None],ramp['root'],previous),
        joint=torch.where(valid[:,None],q,previous_joint),velocity=ramp['velocity'],valid=valid,
        reason=torch.where(valid,0,1),desired_root=goal,post_lift_load_ready=ready)


def forecast_lift(*,model,roots,rpys,anchors,selected,wheel_q,heights):
    """Static support at supplied heights; unchanged three support anchors.

    Fixed candidate body pose across height samples. No temporal dynamics,
    friction, effort or continuous-collision claim. Returns raw sampled evidence.
    """
    from ame_baseline.m1_mass_predictor import predict
    from extension.parallelism.m1_kinematics import m1_ik,M1_PLANNER_JOINT_NAMES,M1_WHEEL_JOINT_NAMES
    if roots.ndim!=3 or roots.shape[-1]!=3 or roots.shape!=rpys.shape:raise ValueError('pose shape')
    b,c,_=roots.shape
    if anchors.shape!=(b,4,3) or selected.shape!=(b,) or selected.dtype!=torch.long or wheel_q.shape!=(b,4):raise ValueError('entry shape')
    if not roots.is_floating_point() or any(x.device!=roots.device or x.dtype!=roots.dtype for x in (rpys,anchors,wheel_q,heights)) or selected.device!=roots.device:raise ValueError('entry dtype/device')
    if not ((selected>=0)&(selected<4)).all():raise ValueError('leg index')
    if heights.ndim!=1 or len(heights)<2 or not torch.isfinite(heights).all() or heights[0]!=0 or not (heights[1:]>heights[:-1]).all():raise ValueError('heights must start at zero and strictly increase')
    if not all(torch.isfinite(x).all() for x in (roots,rpys,anchors,wheel_q)):raise ValueError('nonfinite entry')
    s=len(heights)
    targets=anchors[:,None,None].expand(b,c,s,4,3).clone()
    targets[torch.arange(b,device=roots.device),:,:,selected,2]+=heights[None,None,:]
    proot=roots[:,:,None].expand(b,c,s,3).reshape(-1,3)
    prpy=rpys[:,:,None].expand(b,c,s,3).reshape(-1,3)
    q,ik=m1_ik(proot,prpy,targets.reshape(-1,4,3))
    half=prpy/2;cr,cp,cy=half.cos().unbind(-1);sr,sp,sy=half.sin().unbind(-1)
    quat=torch.stack((cr*cp*cy+sr*sp*sy,sr*cp*cy-cr*sp*sy,cr*sp*cy+sr*cp*sy,cr*cp*sy-sr*sp*cy),-1)
    wq=wheel_q[:,None,None].expand(b,c,s,4).reshape(-1,4)
    pred=predict(model,M1_PLANNER_JOINT_NAMES+M1_WHEEL_JOINT_NAMES,torch.cat((q.reshape(-1,12),wq),-1),proot,quat)
    com=pred['com'].reshape(b,c,s,3)
    indices=torch.tensor([[1,2,3],[0,2,3],[0,1,3],[0,1,2]],device=roots.device)[selected]
    tri=anchors.gather(1,indices[:,:,None].expand(-1,-1,3))[:,:,:2]
    edge=tri.roll(-1,1)-tri
    ab,ac=tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]
    area=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    if (area.abs()<1e-10).any():raise ValueError('degenerate support triangle')
    inward=torch.stack((-edge[:,:,1],edge[:,:,0]),-1)*area.sign()[:,None,None]/edge.norm(dim=-1)[:,:,None]
    distance=((com[:,:,:,None,:2]-tri[:,None,None])*inward[:,None,None]).sum(-1)
    altitude=area.abs()[:,None]/edge.norm(dim=-1)
    force=distance/altitude[:,None,None]*sum(body['mass'] for body in model['bodies'])*9.81
    return dict(min_load=force.min(-1).values,min_margin=distance.min(-1).values,
        reachable=ik.all(-1).reshape(b,c,s)&pred['valid'].reshape(b,c,s),
        joint=q.reshape(b,c,s,12),wheel_targets=targets,com=com)


def choose_pose(*,entry_root,entry_rpy,roots,rpys,min_load,min_margin,reachable):
    if roots.ndim!=3 or roots.shape[-1]!=3 or roots.shape[1]<1:
        raise ValueError('candidate roots must be [B,C,3]')
    b,c,_=roots.shape
    if entry_root.shape!=(b,3) or entry_rpy.shape!=(b,3) or rpys.shape!=roots.shape:
        raise ValueError('pose shape mismatch')
    if min_load.ndim!=3 or min_load.shape[:2]!=(b,c) or min_load.shape[2]<2:
        raise ValueError('support forecasts need [B,C,S] with at least two samples')
    if min_margin.shape!=min_load.shape or reachable.shape!=min_load.shape or reachable.dtype!=torch.bool:
        raise ValueError('support forecast shape/type mismatch')
    values=(entry_root,entry_rpy,roots,rpys,min_load,min_margin)
    if not roots.is_floating_point() or any(t.dtype!=roots.dtype or t.device!=roots.device for t in values) or reachable.device!=roots.device:
        raise ValueError('inputs must share floating dtype/device')
    shift=roots-entry_root[:,None]
    delta=torch.atan2(torch.sin(rpys-entry_rpy[:,None]),torch.cos(rpys-entry_rpy[:,None]))
    valid=reachable.all(-1)&(min_load>=35.).all(-1)&(min_margin>=.02).all(-1)
    valid &= torch.isfinite(min_load).all(-1)&torch.isfinite(min_margin).all(-1)
    valid &= torch.isfinite(roots).all(-1)&torch.isfinite(rpys).all(-1)
    valid &= torch.isfinite(entry_root).all(-1)[:,None]&torch.isfinite(entry_rpy).all(-1)[:,None]
    valid &= (shift.norm(dim=-1)<=.08)&(shift[:,:,2].abs()<=1e-7)
    valid &= (delta[:,:,:2].norm(dim=-1)<=.08)&(delta[:,:,2].abs()<=1e-7)
    valid &= (rpys[:,:,:2].abs()<=.15).all(-1)
    # Prefer smaller displacement/tilt, not maximum force at the bounds.
    cost=shift.square().sum(-1)+.2**2*delta.square().sum(-1)
    index=torch.where(valid,cost,torch.inf).argmin(-1)
    rows=torch.arange(b,device=roots.device);ok=valid.any(-1)
    return dict(root=torch.where(ok[:,None],roots[rows,index],entry_root),
        rpy=torch.where(ok[:,None],rpys[rows,index],entry_rpy),valid=ok,
        index=torch.where(ok,index,-torch.ones_like(index)),candidate_valid=valid)
