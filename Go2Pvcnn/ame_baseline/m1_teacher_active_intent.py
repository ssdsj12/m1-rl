"""Atomic active intent refinement after a safe, unchanged support transaction."""
from dataclasses import fields, replace
import torch
from .m1_teacher_ik import IKResult, body_feet
from .m1_teacher_pose import PoseReference, world_to_goal_body, solve_constrained_ik


def improve_active_intent(step, accepted, requested, measured, active,
                          last_applied, q_seed, branch, dt, cfg, validator):
    target=step.execution_target
    if target is None:
        return step
    batch=last_applied.shape[0]
    leg=torch.arange(4,device=last_applied.device)[None]==active[:,None]
    change=(requested.wheels_w-accepted.wheels_w).abs().amax(-1)
    enabled=step.valid & (target.mode==1) & (target.fraction<1) & (change.gather(1,active[:,None])[:,0]>0)
    if not bool(enabled.any()):
        return step
    baseline=step
    start=body_feet(last_applied)
    best=target.intent_fraction.clone()
    found=~enabled
    gamma_best=torch.zeros_like(best)
    lower=upper=None

    def select(old,new,rows):
        return torch.where(rows.reshape((-1,)+(1,)*(old.ndim-1)),new,old)

    def select_ik(old,new,rows):
        return IKResult(*(select(getattr(old,f.name),getattr(new,f.name),rows) for f in fields(IKResult)))

    for attempt in range(12):
        refining=attempt>=8
        if refining:
            if attempt==8:
                lower=gamma_best.clone();upper=(2*lower).clamp_max(1)
            gamma=(lower+upper)/2
            rows=enabled & (upper>lower)
        else:
            gamma=best.new_full((batch,),2.**(-attempt))
            rows=enabled & ~found
        if not bool(rows.any()):
            continue
        alpha=target.fraction+(1-target.fraction)*gamma
        active_world=accepted.wheels_w+alpha[:,None,None]*(requested.wheels_w-accepted.wheels_w)
        wheels=torch.where(leg[...,None],active_world,baseline.physical.wheels_w)
        physical=PoseReference(baseline.physical.body,wheels)
        command=PoseReference(baseline.command.body,
            torch.where(leg[...,None],active_world,baseline.command.wheels_w))
        nominal=solve_constrained_ik(q_seed,world_to_goal_body(physical),branch,cfg)
        measured_goal=world_to_goal_body(PoseReference(measured,command.wheels_w))
        solve_target=torch.where(leg[...,None],measured_goal,start)
        trial=solve_constrained_ik(last_applied,solve_target,branch,cfg,
            tolerance_m=last_applied.new_full((batch,4),min(cfg.ik_tolerance_m,.0001)))
        values={}
        for field in fields(IKResult):
            if field.name=='valid':
                continue
            mask=leg.repeat_interleave(3,dim=-1) if field.name=='q' else leg
            values[field.name]=torch.where(mask,getattr(trial,field.name),getattr(baseline.command_ik,field.name))
        values['valid']=(values['reason']==0).all(-1)
        assembled=IKResult(**values)
        slew=torch.isfinite(assembled.q).all(-1)&((assembled.q-last_applied).abs()<=2.5*dt).all(-1)
        checked=validator(assembled,baseline.output)
        if not isinstance(checked,torch.Tensor) or checked.shape!=(batch,) or checked.dtype!=torch.bool or checked.device!=last_applied.device:
            raise ValueError('intent validator must return bool [B] on matching device')
        safe=rows & nominal.valid & assembled.valid & slew & checked
        if refining:
            lower=torch.where(safe,gamma,lower)
            upper=torch.where(rows & ~safe,gamma,upper)
        else:
            found |= safe
        gamma_best=torch.where(safe,gamma,gamma_best)
        best=torch.where(safe,alpha,best)
        physical=PoseReference(step.physical.body,select(step.physical.wheels_w,physical.wheels_w,safe))
        command=PoseReference(step.command.body,select(step.command.wheels_w,command.wheels_w,safe))
        selected_target=replace(step.execution_target,
            body_goal=select(step.execution_target.body_goal,torch.where(leg[...,None],measured_goal,target.body_goal),safe),
            body_step=select(step.execution_target.body_step,torch.where(leg[...,None],measured_goal,target.body_step),safe),
            active_fraction=torch.where(safe,torch.ones_like(best),step.execution_target.active_fraction),
            intent_fraction=best)
        step=replace(step,physical=physical,command=command,
            nominal_ik=select_ik(step.nominal_ik,nominal,safe),
            command_ik=select_ik(step.command_ik,assembled,safe),execution_target=selected_target)
    return step
