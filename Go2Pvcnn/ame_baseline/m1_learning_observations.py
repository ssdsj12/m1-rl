"""Measured scan/load features only. No terrain registry or action generation."""
import torch
from .m1_ame_rewards import M1_SUPPORT_BODY_NAMES
from extension.parallelism.rl_adapter import resolve_named_indices


def wheel_loads(env):
    """Named current forces and actual total weight; no nominal-mass shortcut."""
    robot=env.scene['robot'];sensor=env.scene['contact_forces']
    indices=list(resolve_named_indices(tuple(sensor.body_names),M1_SUPPORT_BODY_NAMES))
    forces=sensor.data.net_forces_w[:,indices]
    # Mass is immutable in this contract (no reset mass randomization). Cache
    # the PhysX query, which may return a CPU tensor, on the simulation device.
    if not hasattr(env,'_m1_actual_weight'):
        mass=robot.root_physx_view.get_masses().sum(-1).to(forces.device)
        gravity=abs(float(env.cfg.sim.gravity[2]))
        weight=mass*gravity
        if not torch.isfinite(weight).all() or (weight<=0).any():
            raise ValueError('positive actual robot weight required')
        env._m1_actual_weight=weight
    return forces,env._m1_actual_weight


def wheel_learning_features(hits,labels,valid,wheel_pos,root_quat,forces,weight):
    """[B,4*8]: observed near/far/dy/top/valid/contact/load/other-min.

    Distances in meters clipped to [-1,1], loads in body-weight units [0,2].
    Each cluster is a bounded visible patch around the nearest small hit:
    +/-10cm longitudinal, +/-12cm lateral. Not an inferred full box extent.
    Process 64 environments and one wheel at a time to bound scan scratch RAM.
    """
    b=hits.shape[0]; labels=labels.reshape(b,-1);valid=valid.reshape(b,-1)
    if hits.shape!=(b,labels.shape[1],3) or wheel_pos.shape!=(b,4,3) or forces.shape!=(b,4,3) or root_quat.shape!=(b,4) or weight.shape!=(b,):
        raise ValueError('aligned scan/wheel/force batches required')
    out=hits.new_zeros(b,4,8)
    finite_force=torch.isfinite(forces).all(-1)
    upward=torch.where(finite_force,forces[...,2].clamp_min(0),0.)
    good_weight=torch.isfinite(weight)&(weight>0)
    load=torch.where(good_weight[:,None],upward/weight.clamp_min(1e-8)[:,None],0.).clamp(0,2)
    out[:,:,5]=(upward>10).to(hits.dtype);out[:,:,6]=load
    for wheel in range(4): out[:,wheel,7]=load[:,[j for j in range(4) if j!=wheel]].amin(-1)
    q=torch.nan_to_num(root_quat);q=q/q.norm(dim=-1,keepdim=True).clamp_min(1e-8)
    w,x,y,z=q.unbind(-1);yaw=torch.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
    heading=torch.stack((yaw.cos(),yaw.sin()),-1);side=torch.stack((-yaw.sin(),yaw.cos()),-1)
    pose_ok=torch.isfinite(root_quat).all(-1)&(root_quat.norm(dim=-1)>1e-8)
    for start in range(0,b,64):
        sl=slice(start,min(start+64,b)); h=hits[sl]
        good=valid[sl].bool()&(labels[sl]==1)&torch.isfinite(h).all(-1)&pose_ok[sl,None]
        for wheel in range(4):
            rel=h-wheel_pos[sl,wheel,None]
            dx=(rel[...,:2]*heading[sl,None]).sum(-1);dy=(rel[...,:2]*side[sl,None]).sum(-1)
            usable=good&torch.isfinite(rel).all(-1)&(dx>=-.35)&(dx<=.8)&(dy.abs()<=.12)
            idx=torch.where(usable,dx.abs(),torch.inf).argmin(-1)
            anchor_x=dx.gather(1,idx[:,None]);anchor_y=dy.gather(1,idx[:,None])
            patch=usable&((dx-anchor_x).abs()<=.10)&((dy-anchor_y).abs()<=.12)
            present=patch.any(-1)
            near=torch.where(patch,dx,torch.inf).amin(-1)
            far=torch.where(patch,dx,-torch.inf).amax(-1)
            lateral=torch.where(patch,dy,0.).sum(-1)/patch.sum(-1).clamp_min(1)
            top=torch.where(patch,rel[...,2],-torch.inf).amax(-1)
            geometry=torch.stack((near,far,lateral,top),-1)
            out[sl,wheel,:4]=torch.where(present[:,None],geometry,0.).clamp(-1,1)
            out[sl,wheel,4]=present.to(hits.dtype)
    return out.flatten(1)


def m1_wheel_learning_observation(env):
    robot=env.scene['robot'];scanner=env.scene['semantic_height_scanner'].data
    ids=list(resolve_named_indices(tuple(robot.body_names),M1_SUPPORT_BODY_NAMES))
    forces,weight=wheel_loads(env)
    # Native SemanticGridRayCasterData encodes misses as non-finite ray hits;
    # it does not expose the planner's separate valid_mask field.
    valid=torch.isfinite(scanner.ray_hits_w).all(-1)
    return wheel_learning_features(scanner.ray_hits_w,scanner.semantic_map,valid,
        robot.data.body_pos_w[:,ids],robot.data.root_quat_w,forces,weight)
