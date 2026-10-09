"""Read-only full floating-base dynamics snapshots for M1 WBC diagnostics.

Preserves the backend's six base coordinates, reorders only named joints.
Compensation sign/frame require independent native physics verification before
control use. This module never initializes simulation or writes actuators.
"""
import torch
import math


def _identity(ids, step, batch, device):
    if type(step) is not int or step < 0:
        raise ValueError('step must be a nonnegative integer')
    if (not isinstance(ids, torch.Tensor) or ids.shape != (batch,)
            or ids.dtype not in (torch.int32, torch.int64)
            or ids.device != device or (ids < 0).any()):
        raise ValueError('episode identity must be a nonnegative integer batch vector')


def generalized_snapshot(view, native_names, ordered_names, episode_ids, step):
    """Read complete M and compensation vectors; reject the whole invalid batch.

    Call immediately after a synchronous physics update. The caller owns
    environment row identity and must use require_current before consumption.
    Missing/full-backend API exceptions propagate; no deprecated fallback.
    """
    native_names, ordered_names = tuple(native_names), tuple(ordered_names)
    if (len(native_names) != 16 or len(ordered_names) != 16
            or any(not isinstance(n, str) or not n for n in native_names+ordered_names)
            or len(set(native_names)) != 16 or len(set(ordered_names)) != 16
            or set(native_names) != set(ordered_names)):
        raise ValueError('16 unique matching named M1 joints required')
    mass = view.get_generalized_mass_matrices()
    gravity = view.get_gravity_compensation_forces()
    coriolis = view.get_coriolis_and_centrifugal_compensation_forces()
    values = (mass, gravity, coriolis)
    if any(not isinstance(v, torch.Tensor) for v in values):
        raise ValueError('torch dynamics tensors required')
    if (mass.ndim != 3 or mass.shape[1:] != (22, 22) or mass.shape[0] == 0
            or gravity.shape != mass.shape[:2] or coriolis.shape != gravity.shape):
        raise ValueError('full floating-base M1 dynamics must have 6+16 coordinates')
    if any(not v.is_floating_point() or v.dtype != mass.dtype
           or v.device != mass.device or not torch.isfinite(v).all() for v in values):
        raise ValueError('finite matching floating dynamics tensors required')
    _identity(episode_ids, step, mass.shape[0], mass.device)
    scale = mass.abs().amax(dim=(1, 2)).clamp_min(1.)
    if ((mass-mass.transpose(1, 2)).abs().amax(dim=(1, 2)) > 1e-5*scale).any():
        raise ValueError('generalized mass matrix must be symmetric')
    # Cholesky reads one triangle; symmetry was checked separately above.
    if (torch.linalg.cholesky_ex(mass.double()).info != 0).any():
        raise ValueError('generalized mass matrix must be positive definite')
    p = torch.tensor(list(range(6)) + [6+native_names.index(n) for n in ordered_names],
                     device=mass.device)
    mass = mass.index_select(1, p).index_select(2, p).clone()
    gravity = gravity.index_select(1, p).clone()
    coriolis = coriolis.index_select(1, p).clone()
    return dict(mass=mass, gravity=gravity, coriolis=coriolis, bias=gravity+coriolis,
                joint_names=ordered_names, episode_ids=episode_ids.clone(), step=step)


def require_current(snapshot, episode_ids, step):
    """Reject a stale step/reset or an incompatible identity contract."""
    stored = snapshot['episode_ids']
    _identity(episode_ids, step, stored.shape[0], stored.device)
    if (episode_ids.dtype != stored.dtype or snapshot['step'] != step
            or not torch.equal(stored, episode_ids)):
        raise ValueError('stale dynamics snapshot')


def mass_from_links(jac, masses, inertia_world, armature):
    """Independent kinetic-energy oracle from world COM spatial Jacobians.

    Linear then angular rows; six base columns then the same16joint columns.
    World inertia must be rotated from each COM frame by the caller.
    """
    values = (jac, masses, inertia_world, armature)
    if any(not isinstance(v, torch.Tensor) for v in values):
        raise ValueError('torch tensors required')
    if (jac.ndim != 4 or jac.shape[2:] != (6, 22)
            or masses.shape != jac.shape[:2]
            or inertia_world.shape != jac.shape[:2]+(3, 3)
            or armature.shape != (jac.shape[0], 16)):
        raise ValueError('invalid full M1 link-energy shapes')
    if any(not v.is_floating_point() or v.dtype != jac.dtype
           or v.device != jac.device or not torch.isfinite(v).all() for v in values):
        raise ValueError('finite matching floating tensors required')
    if (masses <= 0).any() or (armature < 0).any():
        raise ValueError('positive body masses and nonnegative armature required')
    linear, angular = jac[:, :, :3], jac[:, :, 3:]
    matrix = torch.einsum('blci,bl,blcj->bij', linear, masses, linear)
    matrix += torch.einsum('blci,blcd,bldj->bij', angular, inertia_world, angular)
    rotor = torch.cat((torch.zeros_like(armature[:, :6]), armature), dim=1)
    return matrix + torch.diag_embed(rotor)


def free_dynamics_residual(mass, bias, velocity_before, velocity_after, effort, dt):
    """Finite-step free-body residual; no contact or implicit-drive compensation."""
    if not isinstance(dt, (float, int)) or not math.isfinite(dt) or dt <= 0:
        raise ValueError('positive finite dt required')
    values = (mass, bias, velocity_before, velocity_after, effort)
    if any(not isinstance(v, torch.Tensor) for v in values):
        raise ValueError('torch dynamics tensors required')
    if (mass.ndim != 3 or mass.shape[1:] != (22, 22)
            or any(v.shape != (mass.shape[0], 22) for v in values[1:4])
            or effort.shape != (mass.shape[0], 16)):
        raise ValueError('full M1 free-body dimensions required')
    if any(not v.is_floating_point() or v.dtype != mass.dtype
           or v.device != mass.device or not torch.isfinite(v).all() for v in values):
        raise ValueError('finite matching dynamics required')
    force = torch.cat((torch.zeros_like(effort[:, :6]), effort), dim=1)
    acceleration = (velocity_after-velocity_before)/dt
    return (mass @ acceleration.unsqueeze(-1)).squeeze(-1)+bias-force
