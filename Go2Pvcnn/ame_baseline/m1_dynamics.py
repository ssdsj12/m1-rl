"""Verified M1 dynamics coordinate utilities; no efforts are applied here."""
import torch


def point_linear_jacobian(com_jacobian, com_position, point_position):
    """Map world COM spatial Jacobian [B,L,6,D] to a world point [B,L,3].

    PhysX floating-base columns are six base coordinates followed by named
    articulation joints. This function preserves their order. The measured
    local runtime convention is COM-linear then world-angular velocity.
    Missing geometry raises rather than silently producing an effort target.
    """
    if com_jacobian.ndim != 4 or com_jacobian.shape[2] != 6:
        raise ValueError('expected COM Jacobian [B,L,6,D]')
    shape = com_jacobian.shape[:2] + (3,)
    if com_position.shape != shape or point_position.shape != shape:
        raise ValueError('point positions must match Jacobian batch and link axes')
    values = (com_jacobian, com_position, point_position)
    if any(not v.is_floating_point() or v.device != com_jacobian.device
           or v.dtype != com_jacobian.dtype or not torch.isfinite(v).all() for v in values):
        raise ValueError('finite matching floating tensors required')
    angular = com_jacobian[:, :, 3:].transpose(-1, -2)
    offset = (point_position-com_position)[:, :, None].expand_as(angular)
    return com_jacobian[:, :, :3] + torch.cross(angular, offset, dim=-1).transpose(-1, -2)
