"""Improve only active-wheel execution after a valid support transaction."""
from dataclasses import fields,replace
import torch
from .m1_teacher_ik import body_feet,solve_constrained_ik,IKResult


def improve_active_progress(target,baseline,last_applied,branch,active,dt,cfg,eligible,validator):
    """Keep support joints/history exact; every assembled trial is revalidated."""
    batch=last_applied.shape[0]
    leg=torch.arange(4,device=last_applied.device)[None]==active[:,None]
    enabled=eligible & baseline.valid & (target.mode==1) & (target.fraction<1)
    if not bool(enabled.any()):return target,baseline
    start=body_feet(last_applied)
    best=target.active_fraction.clone()
    result=baseline
    step=target.body_step.clone()
    found=~enabled
    lower=upper=None
    for attempt in range(12):
        refining=attempt>=8
        if refining:
            if attempt==8:
                lower=best.clone();upper=(2*lower).clamp_max(1.)
            alpha=(lower+upper)/2
            rows=enabled & (upper>lower)
        else:
            alpha=best.new_full((batch,),2.**(-attempt))
            rows=enabled & ~found & (alpha>best)
        if not bool(rows.any()):continue
        active_step=start+alpha[:,None,None]*(target.body_goal-start)
        # Other legs are numerical no-ops in this solve, never substituted
        # into the baseline support result below.
        solve_target=torch.where(leg[...,None],active_step,start)
        trial=solve_constrained_ik(last_applied,solve_target,branch,cfg,
            tolerance_m=last_applied.new_full((batch,4),min(cfg.ik_tolerance_m,.0001)))
        values={}
        for field in fields(IKResult):
            name=field.name
            if name=='valid':continue
            old=getattr(baseline,name);new=getattr(trial,name)
            mask=leg.repeat_interleave(3,dim=-1) if name=='q' else leg
            values[name]=torch.where(mask,new,old)
        values['valid']=(values['reason']==0).all(-1)
        assembled=IKResult(**values)
        slew=torch.isfinite(assembled.q).all(-1)&((assembled.q-last_applied).abs()<=2.5*dt).all(-1)
        accepted=validator(assembled)
        if not isinstance(accepted,torch.Tensor) or accepted.shape!=(batch,) or accepted.dtype!=torch.bool or accepted.device!=last_applied.device:
            raise ValueError('active validator must return bool [B] on matching device')
        safe=rows & assembled.valid & slew & accepted
        if refining:
            lower=torch.where(safe,alpha,lower)
            upper=torch.where(rows & ~safe,alpha,upper)
        else:found |= safe
        best=torch.where(safe,alpha,best)
        step=torch.where((safe[:,None]&leg)[...,None],active_step,step)
        result=IKResult(*(torch.where(safe.reshape((-1,)+(1,)*(getattr(assembled,f.name).ndim-1)),
            getattr(assembled,f.name),getattr(result,f.name)) for f in fields(IKResult)))
    return replace(target,body_step=step,active_fraction=best),result
