"""Instantaneous measured unload predicate; caller owns fresh-frame streak/reset."""
import torch


def unload_ready(*, force, selected, tilt, rate, effort_error, allocation_valid):
    batch = force.shape[0]
    if (force.shape != (batch, 4) or selected.shape != (batch,)
            or selected.dtype != torch.long or tilt.shape != (batch, 2)
            or rate.shape != (batch, 2) or effort_error.shape != (batch,)
            or allocation_valid.shape != (batch,) or allocation_valid.dtype != torch.bool):
        raise ValueError('invalid unload evidence shapes or masks')
    if any(x.device != force.device for x in (selected, tilt, rate, effort_error, allocation_valid)):
        raise ValueError('unload evidence devices must match')
    finite = torch.isfinite(force).all(-1) & torch.isfinite(tilt).all(-1)
    finite &= torch.isfinite(rate).all(-1) & torch.isfinite(effort_error)
    finite &= (selected >= 0) & (selected < 4) & (force >= 0).all(-1)
    mask = torch.arange(4, device=force.device)[None] == selected[:, None]
    unloaded = ((force <= 5.) | ~mask).all(-1)
    supported = ((force >= 30.) | mask).all(-1)
    return (finite & allocation_valid & unloaded & supported
            & (tilt.abs() <= .15).all(-1) & (rate.abs() <= .20).all(-1)
            & (effort_error >= 0) & (effort_error <= 1.))
