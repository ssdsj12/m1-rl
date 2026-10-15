"""Bounded measured-load position feedback; never a support certificate."""
from dataclasses import dataclass
import torch
from .m1_teacher_tripod_load import tripod_load


@dataclass(frozen=True)
class LoadProposal:
    target_fz: torch.Tensor
    offset: torch.Tensor
    velocity: torch.Tensor
    valid: torch.Tensor
    unprojected_fz: torch.Tensor
    active_affine: torch.Tensor
    moment_residual_xy: torch.Tensor


def _floating(value, shape, like):
    if (not isinstance(value, torch.Tensor) or value.shape != shape
            or value.dtype != like.dtype or value.device != like.device):
        raise ValueError('floating tensor shape/dtype/device mismatch')


def _project(value, lower, upper, total):
    # Three coordinates: fixed bounded bisection, no external optimizer.
    # Double arithmetic prevents float32 cancellation in zero-sum offsets.
    dtype=value.dtype
    v,lo,hi,s=(x.to(torch.float64) for x in (value,lower,upper,total))
    left=(v-hi).amin(-1);right=(v-lo).amax(-1)
    for _ in range(80):
        middle=(left+right)*.5
        trial=torch.maximum(lo,torch.minimum(hi,v-middle[:,None]))
        above=trial.sum(-1)>s
        left=torch.where(above,middle,left)
        right=torch.where(above,right,middle)
    return torch.maximum(lo,torch.minimum(hi,v-((left+right)*.5)[:,None])).to(dtype)


def propose_load_feedback(raw_fz, fractions, active_wheel, previous, dt, valid, *, wheels_w, attitude_error_m=None):
    if (not isinstance(raw_fz,torch.Tensor) or raw_fz.ndim!=2
            or raw_fz.shape[1]!=4 or raw_fz.dtype not in (torch.float32,torch.float64)):
        raise ValueError('raw_fz must be floating [B,4]')
    b=raw_fz.shape[0]
    for x,shape in ((fractions,(b,3)),(previous,(b,4)),(dt,(b,)),(wheels_w,(b,4,3))):
        _floating(x,shape,raw_fz)
    for x,dtype in ((active_wheel,torch.long),(valid,torch.bool)):
        if (not isinstance(x,torch.Tensor) or x.shape!=(b,)
                or x.dtype!=dtype or x.device!=raw_fz.device):
            raise ValueError('index/validity contract mismatch')
    if bool(((active_wheel<0)|(active_wheel>3)).any()):
        raise ValueError('active wheel outside 0..3')
    if not bool((torch.isfinite(dt)&(dt>0)).all()):
        raise ValueError('dt must be positive finite')
    if (not bool(torch.isfinite(previous).all())
            or bool((previous.abs()>.015000001).any())
            or bool((previous.sum(-1).abs()>1e-8).any())
            or bool((previous.gather(1,active_wheel[:,None]).abs()>0).any())):
        raise ValueError('previous offset must be bounded, zero-sum, active zero')
    ids=torch.arange(4,device=raw_fz.device).expand(b,4)
    support=ids[ids!=active_wheel[:,None]].reshape(b,3)
    attitude_finite=torch.ones(b,dtype=torch.bool,device=raw_fz.device)
    if attitude_error_m is not None:
        _floating(attitude_error_m,(b,4),raw_fz)
        attitude_finite=torch.isfinite(attitude_error_m).all(-1)
        structure=(attitude_error_m.gather(1,active_wheel[:,None]).squeeze(1)==0)&(attitude_error_m.sum(-1).abs()<=1e-8)
        if bool((attitude_finite&~structure).any()):
            raise ValueError('attitude error must be zero-sum with active zero')
    measured=raw_fz.gather(1,support)
    # Near-collinear triangles can have huge opposite affine coordinates.
    # Keep moment accounting in double, including the diagnostic intermediates.
    total=measured.double().clamp_min(0).sum(-1)
    geometry_wheels=wheels_w.double()
    active_point=geometry_wheels.gather(1,active_wheel[:,None,None].expand(-1,1,3)).squeeze(1)
    geometry=tripod_load(active_point,geometry_wheels,active_wheel,torch.ones_like(total))
    active_fz=raw_fz.double().gather(1,active_wheel[:,None]).squeeze(1).clamp_min(0)
    weights64=fractions.double()
    safe=(valid & attitude_finite & torch.isfinite(raw_fz).all(-1)
          & torch.isfinite(fractions).all(-1) & (fractions>=0).all(-1)
          & torch.isfinite(weights64.sum(-1)) & (weights64.sum(-1)>0)
          & torch.isfinite(total+active_fz) & (total>=135) & geometry.valid)
    # Invalid rows use finite dummy values for computation, then freeze.
    total=torch.where(safe,total,torch.full_like(total,135.))
    weights=torch.where(safe[:,None],weights64,torch.ones_like(weights64))
    affine=torch.where(safe[:,None],geometry.fractions,torch.zeros_like(geometry.fractions))
    active_fz=torch.where(safe,active_fz,torch.zeros_like(active_fz))
    # Keep the active wheel's measured moment until it actually leaves contact.
    desired=weights/weights.sum(-1,keepdim=True)*(total+active_fz)[:,None]-active_fz[:,None]*affine
    target=_project(desired,torch.full_like(desired,45.),
                    total[:,None].expand_as(desired),total).to(raw_fz.dtype)
    measured=torch.where(safe[:,None],measured,torch.zeros_like(measured))
    old=previous.gather(1,support)
    lower=torch.maximum(torch.full_like(old,-.01),(-.015-old)/dt[:,None])
    upper=torch.minimum(torch.full_like(old,.01),(.015-old)/dt[:,None])
    feasible=(lower<=upper).all(-1)&(lower.sum(-1)<=1e-8)&(upper.sum(-1)>=-1e-8)
    safe &= feasible
    preference=-.0002*(target-measured)
    if attitude_error_m is not None:
        weak=(measured<45.)|((target-measured)>15.)
        strong=((measured-target)>15.)&~weak
        lower=torch.where(strong,lower.clamp_min(0),lower)
        upper=torch.where(weak,upper.clamp_max(0),upper)
        baseline=_project(preference,lower,upper,torch.zeros_like(total))
        # Preserve at least the load-only correction on priority contacts.
        # Merely enforcing a sign would allow the posture preference to stall
        # an urgently needed correction at zero.
        lower=torch.where(strong,torch.maximum(lower,baseline),lower)
        upper=torch.where(weak,torch.minimum(upper,baseline),upper)
        attitude=torch.where(safe[:,None],attitude_error_m.gather(1,support),torch.zeros_like(measured))
        preference=preference+.5*attitude
    velocity=_project(preference,lower,upper,torch.zeros_like(total))
    velocity=torch.where(safe[:,None],velocity,torch.zeros_like(velocity))
    # Re-project the integrated position, too: float32 integration otherwise
    # accumulates a nonzero sum and eventually invalidates its own next input.
    position_lower=torch.maximum(torch.full_like(old,-.015),old-.01*dt[:,None])
    position_upper=torch.minimum(torch.full_like(old,.015),old+.01*dt[:,None])
    if attitude_error_m is not None:
        position_lower=torch.maximum(position_lower,old+dt[:,None]*lower)
        position_upper=torch.minimum(position_upper,old+dt[:,None]*upper)
    candidate=_project(old+dt[:,None]*velocity,position_lower,position_upper,torch.zeros_like(total))
    candidate=torch.where(safe[:,None],candidate,old)
    velocity=torch.where(safe[:,None],(candidate-old)/dt[:,None],torch.zeros_like(old))
    offset=previous.scatter(1,support,candidate)
    points=geometry_wheels.gather(1,support[:,:,None].expand(-1,-1,3))[:,:,:2]
    relative=torch.where(safe[:,None,None],points-points[:,:1],torch.zeros_like(points))
    residual=((target.double()-desired)[:,:,None]*relative).sum(1)
    return LoadProposal(
        torch.zeros_like(raw_fz).scatter(1,support,torch.where(safe[:,None],target,torch.zeros_like(target))),
        offset,torch.zeros_like(raw_fz).scatter(1,support,velocity),safe,
        torch.zeros_like(raw_fz,dtype=torch.float64).scatter(1,support,torch.where(safe[:,None],desired,torch.zeros_like(desired))),
        torch.where(safe[:,None],affine,torch.zeros_like(affine)),
        torch.where(safe[:,None],residual,torch.zeros_like(residual)))
