"""Pure measured teacher inputs; no simulator imports or root COM proxies."""
import torch


def mass_weighted_com(body_com_w, masses):
    """Return world COM [B,3] and row validity; bad rows retain NaN evidence."""
    if (not isinstance(body_com_w, torch.Tensor) or body_com_w.ndim != 3
            or body_com_w.shape[-1] != 3 or body_com_w.shape[1] == 0):
        raise ValueError('body_com_w must be floating [B,N,3] with N > 0')
    if (not isinstance(masses, torch.Tensor) or masses.shape != body_com_w.shape[:2]
            or masses.device != body_com_w.device
            or not masses.is_floating_point() or not body_com_w.is_floating_point()):
        raise ValueError('masses/body_com_w have invalid shape, device or dtype')
    total = masses.sum(-1)
    valid = (torch.isfinite(body_com_w).all(dim=(-1, -2))
             & torch.isfinite(masses).all(-1) & (masses >= 0).all(-1)
             & torch.isfinite(total) & (total > 0))
    com = (body_com_w * masses[..., None]).sum(1) / total[:, None]
    valid &= torch.isfinite(com).all(-1)
    return torch.where(valid[:, None], com, torch.full_like(com, float('nan'))), valid
