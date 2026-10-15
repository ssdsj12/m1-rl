"""Quasi-static tripod guidance, never a certificate of actual support."""
from dataclasses import dataclass
import torch


def _tensor(value, shape, like=None):
    if (not isinstance(value, torch.Tensor) or value.shape != shape
            or value.dtype not in (torch.float32, torch.float64)):
        raise ValueError('expected floating tensor with matching shape')
    if like is not None and (value.dtype != like.dtype or value.device != like.device):
        raise ValueError('tensor dtype/device mismatch')


@dataclass(frozen=True)
class TripodLoad:
    support_indices: torch.Tensor
    fractions: torch.Tensor
    loads_n: torch.Tensor
    min_load_n: torch.Tensor
    valid: torch.Tensor


def tripod_load(com_w, wheels_w, active_wheel, total_load_n):
    if not isinstance(com_w, torch.Tensor) or com_w.ndim != 2:
        raise ValueError('com must be [B,3]')
    b=com_w.shape[0]
    _tensor(com_w,(b,3)); _tensor(wheels_w,(b,4,3),com_w)
    _tensor(total_load_n,(b,),com_w)
    if (not isinstance(active_wheel,torch.Tensor) or active_wheel.shape!=(b,)
            or active_wheel.dtype!=torch.long or active_wheel.device!=com_w.device
            or bool(((active_wheel<0)|(active_wheel>3)).any())):
        raise ValueError('active wheel must be matching long vector in 0..3')
    ids=torch.arange(4,device=com_w.device).expand(b,4)
    support=ids[ids!=active_wheel[:,None]].reshape(b,3)
    points=wheels_w.gather(1,support[:,:,None].expand(-1,-1,3))
    xy=points[:,:,:2]-com_w[:,None,:2]
    ab=xy[:,1]-xy[:,0];ac=xy[:,2]-xy[:,0]
    area=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    valid=(torch.isfinite(com_w).all(-1)&torch.isfinite(wheels_w).all(dim=(-1,-2))
        &torch.isfinite(total_load_n)&(total_load_n>0)&torch.isfinite(area)&(area.abs()>1e-10))
    matrix=torch.cat((xy.transpose(1,2),torch.ones_like(xy[:,:,:1]).transpose(1,2)),1)
    safe=torch.where(valid[:,None,None],matrix,torch.eye(3,device=com_w.device,dtype=com_w.dtype)[None])
    rhs=com_w.new_tensor([0.,0.,1.]).expand(b,3)
    fractions,info=torch.linalg.solve_ex(safe,rhs)
    loads=fractions*total_load_n[:,None]
    valid &= (info==0)&torch.isfinite(fractions).all(-1)&torch.isfinite(loads).all(-1)
    fractions=torch.where(valid[:,None],fractions,torch.full_like(fractions,float('nan')))
    loads=torch.where(valid[:,None],loads,torch.full_like(loads,float('nan')))
    return TripodLoad(support,fractions,loads,loads.amin(-1),valid)


def capped_load_scale(raw_fz, captured_load_n):
    if not isinstance(raw_fz,torch.Tensor) or raw_fz.ndim!=2:
        raise ValueError('raw forces must be [B,4]')
    b=raw_fz.shape[0]
    _tensor(raw_fz,(b,4));_tensor(captured_load_n,(b,),raw_fz)
    current=raw_fz.clamp_min(0).sum(-1)
    scale=torch.minimum(current,captured_load_n)
    valid=(torch.isfinite(raw_fz).all(-1)&torch.isfinite(captured_load_n)
        &torch.isfinite(scale)&(scale>0))
    return torch.where(valid,scale,torch.full_like(scale,float('nan')))
