import importlib.util
from pathlib import Path

import pytest
import torch


def module():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_wbc_dynamics.py'
    assert path.exists(), 'full M1 WBC dynamics snapshot is missing'
    spec = importlib.util.spec_from_file_location('m1_wbc_dynamics', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class View:
    # Only full floating-base APIs are available at this boundary.
    def __init__(self):
        a = torch.arange(22*22, dtype=torch.float64).reshape(22, 22) / 1000
        self.mass = (a @ a.T + torch.eye(22)).repeat(2, 1, 1)
        self.gravity = torch.arange(44, dtype=torch.float64).reshape(2, 22)
        self.coriolis = self.gravity * .125 + 3

    def get_generalized_mass_matrices(self):
        return self.mass

    def get_gravity_compensation_forces(self):
        return self.gravity

    def get_coriolis_and_centrifugal_compensation_forces(self):
        return self.coriolis


NAMES = tuple(f'joint_{i}' for i in range(16))


def snapshot(view=None, names=NAMES, ordered=NAMES, step=3, ids=None):
    return module().generalized_snapshot(
        View() if view is None else view, names, ordered,
        torch.tensor([4, 9]) if ids is None else ids, step)


def test_permutation_preserves_base_and_both_matrix_axes():
    v = View()
    result = snapshot(v, ordered=NAMES[::-1])
    p = torch.tensor(list(range(6)) + list(range(21, 5, -1)))
    torch.testing.assert_close(result['mass'], v.mass[:, p][:, :, p])
    torch.testing.assert_close(result['gravity'], v.gravity[:, p])
    torch.testing.assert_close(result['coriolis'], v.coriolis[:, p])
    torch.testing.assert_close(result['bias'], (v.gravity+v.coriolis)[:, p])
    assert result['joint_names'] == NAMES[::-1]


def test_snapshot_does_not_alias_backend_or_episode_buffers():
    v, ids = View(), torch.tensor([4, 9])
    result = snapshot(v, ids=ids)
    mass = result['mass'].clone()
    bias = result['bias'].clone()
    v.mass.zero_(); v.gravity.zero_(); v.coriolis.zero_(); ids.zero_()
    torch.testing.assert_close(result['mass'], mass)
    torch.testing.assert_close(result['bias'], bias)
    assert result['episode_ids'].tolist() == [4, 9]


@pytest.mark.parametrize('names,ordered', [
    (NAMES[:-1], NAMES), (NAMES, NAMES[:-1]),
    (NAMES[:-1]+(NAMES[0],), NAMES), (NAMES, NAMES[:-1]+('unknown',)),
    (NAMES, NAMES[:-1]+(NAMES[0],)),
])
def test_reject_name_contract(names, ordered):
    with pytest.raises(ValueError):
        snapshot(names=names, ordered=ordered)


@pytest.mark.parametrize('fault', ['truncated', 'nan', 'asymmetric', 'indefinite', 'dtype'])
def test_reject_incomplete_or_invalid_dynamics(fault):
    v = View()
    if fault == 'truncated':
        v.mass = v.mass[:, 6:, 6:]
    elif fault == 'nan':
        v.coriolis[0, 3] = float('nan')
    elif fault == 'asymmetric':
        v.mass[0, 1, 2] += 1
    elif fault == 'indefinite':
        v.mass[0] = -torch.eye(22)
    else:
        v.gravity = v.gravity.float()
    with pytest.raises(ValueError):
        snapshot(v)


def test_freshness_rejects_step_or_row_reset():
    m = module()
    result = snapshot()
    m.require_current(result, torch.tensor([4, 9]), 3)
    for ids, step in [(torch.tensor([4, 9]), 4), (torch.tensor([5, 9]), 3),
                      (torch.tensor([4., 9.]), 3), (torch.tensor([4, 9]), True)]:
        with pytest.raises(ValueError):
            m.require_current(result, ids, step)


@pytest.mark.parametrize('ids,step', [
    (torch.tensor([4, 9]), -1), (torch.tensor([4, 9]), True),
    (torch.tensor([4., 9.]), 3), (torch.tensor([4]), 3),
    (torch.tensor([-1, 9]), 3),
])
def test_invalid_identity(ids, step):
    with pytest.raises(ValueError):
        snapshot(ids=ids, step=step)


def test_link_energy_reconstructs_full_coupled_matrix():
    fn = getattr(module(), 'mass_from_links', None)
    assert fn is not None, 'independent link-energy oracle missing'
    torch.manual_seed(11)
    jac = torch.randn(2, 3, 6, 22, dtype=torch.float64)
    mass = torch.tensor([[1., 2., 3.], [4., 5., 6.]], dtype=torch.float64)
    a = torch.randn(2, 3, 3, 3, dtype=torch.float64)
    inertia = a @ a.transpose(-1, -2) + torch.eye(3)
    armature = torch.full((2, 16), .02, dtype=torch.float64)
    matrix = fn(jac, mass, inertia, armature)
    vel = torch.randn(2, 22, dtype=torch.float64)
    link_vel = (jac @ vel[:, None, :, None]).squeeze(-1)
    energy = (mass*link_vel[..., :3].square().sum(-1)).sum(-1)
    energy += torch.einsum('bli,blij,blj->b', link_vel[..., 3:], inertia, link_vel[..., 3:])
    energy += (armature*vel[:, 6:].square()).sum(-1)
    torch.testing.assert_close(torch.einsum('bi,bij,bj->b', vel, matrix, vel), energy)
    torch.testing.assert_close(matrix, matrix.transpose(-1, -2))


@pytest.mark.parametrize('fault', ['shape', 'negative_mass', 'nan', 'negative_armature'])
def test_link_energy_rejects_invalid_inputs(fault):
    fn = getattr(module(), 'mass_from_links', None)
    assert fn is not None, 'independent link-energy oracle missing'
    jac = torch.zeros(1, 2, 6, 22)
    mass = torch.ones(1, 2)
    inertia = torch.eye(3).repeat(1, 2, 1, 1)
    armature = torch.zeros(1, 16)
    if fault == 'shape':
        jac = jac[..., :16]
    elif fault == 'negative_mass':
        mass[0, 0] = -1
    elif fault == 'nan':
        inertia[0, 0, 0, 0] = float('nan')
    else:
        armature[0, 0] = -1
    with pytest.raises(ValueError):
        fn(jac, mass, inertia, armature)
