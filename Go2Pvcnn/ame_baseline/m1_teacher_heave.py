"""Common support-height feedback, separate from zero-sum load allocation."""
from dataclasses import dataclass
import torch


@dataclass(frozen=True)
class HeaveProposal:
    offset: torch.Tensor
    valid: torch.Tensor


def propose_support_heave(command_z, measured_z, captured_error, previous, dt, restore, valid):
    if (not isinstance(command_z,torch.Tensor) or command_z.ndim!=1
            or command_z.dtype not in (torch.float32,torch.float64)):
        raise ValueError('command_z must be floating [B]')
    for value in (measured_z,captured_error,previous,dt):
        if (not isinstance(value,torch.Tensor) or value.shape!=command_z.shape
                or value.dtype!=command_z.dtype or value.device!=command_z.device):
            raise ValueError('heave shape/dtype/device mismatch')
    for flag in (restore,valid):
        if (not isinstance(flag,torch.Tensor) or flag.shape!=command_z.shape
                or flag.dtype!=torch.bool or flag.device!=command_z.device):
            raise ValueError('heave flags must be bool [B]')
    if (not bool(torch.isfinite(previous).all()) or bool((previous.abs()>.020000001).any())
            or not bool(torch.isfinite(captured_error).all())
            or not bool((torch.isfinite(dt)&(dt>0)).all())):
        raise ValueError('invalid heave history or dt')
    safe=valid & torch.isfinite(command_z) & torch.isfinite(measured_z)
    error=torch.where(safe,command_z-measured_z-captured_error,torch.zeros_like(command_z))
    target=torch.where(restore,torch.zeros_like(error),(-error).clamp(-.02,.02))
    proposal=previous+torch.maximum(-.02*dt,torch.minimum(.02*dt,target-previous))
    return HeaveProposal(torch.where(safe,proposal,previous),safe)
