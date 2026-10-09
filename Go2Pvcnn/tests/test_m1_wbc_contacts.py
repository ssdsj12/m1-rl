import importlib.util
from pathlib import Path
import numpy as np
import pytest


def geometry():
    path = Path(__file__).parents[1]/'ame_baseline/m1_wbc_contacts.py'
    assert path.exists(), 'true contact-point geometry adapter missing'
    spec = importlib.util.spec_from_file_location('contacts', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.contact_geometry


def fixture():
    jac = np.zeros((4,6,22)); jac[:,:3,:3] = np.eye(3)
    jac[:,4,6] = 1.
    com = np.zeros((4,3)); com[:,2] = .1
    points = np.array([[0.,0.,0.], [.02,0.,0.]])
    return points, np.tile([0.,0.,1.],(2,1)), np.array([0,0]), jac, com


def test_material_contact_velocity_allows_rolling_not_center_lock():
    fn = geometry(); args = fixture()
    r = fn(*args)
    velocity = np.zeros(22); velocity[0] = .1; velocity[6] = 1.
    np.testing.assert_allclose(r['jac'][0]@velocity, 0., atol=1e-12)
    assert (args[3][0,:3]@velocity)[0] == .1
    # Second point has a distinct moment arm; must not collapse it to wheel center.
    assert r['jac'][1,2,6] == -.02
    assert r['group_ids'].tolist() == [0,0]


def test_geometry_is_translation_invariant_and_frames_right_handed():
    fn = geometry(); p,n,g,j,c = fixture()
    a = fn(p,n,g,j,c); b = fn(p+7,n,g,j,c+7)
    np.testing.assert_allclose(a['jac'], b['jac'], atol=1e-12)
    np.testing.assert_allclose(a['frames'].transpose(0,2,1)@a['frames'], np.tile(np.eye(3),(2,1,1)))
    np.testing.assert_allclose(np.linalg.det(a['frames']), 1.)
    np.testing.assert_allclose(a['frames'][:,:,2],n)


@pytest.mark.parametrize('fault',['normal','owner','nan'])
def test_bad_geometry_is_rejected(fault):
    fn = geometry(); p,n,g,j,c = fixture()
    if fault == 'normal': n[0] = 0
    elif fault == 'owner': g[0] = 4
    else: p[0,0] = np.nan
    with pytest.raises(ValueError): fn(p,n,g,j,c)


def test_exact_repeated_physx_contacts_merge_only_when_owner_geometry_and_gap_match():
    path = Path(__file__).parents[1]/'ame_baseline/m1_wbc_contacts.py'
    spec = importlib.util.spec_from_file_location('contacts_dedup', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    points = np.array([[0.,0.,0.], [0.,0.,0.], [0.,0.,0.], [0.,0.,0.]])
    normals = np.array([[0.,0.,1.], [0.,0.,1.], [0.,0.,1.], [0.,0.,1.]])
    owners = np.array([0, 0, 0, 1])
    gaps = np.array([0., 0., 1e-4, 0.])
    result = mod.deduplicate_contact_points(
        points=points, normals=normals, owners=owners, gaps=gaps)
    assert result['owners'].tolist() == [0, 0, 1]
    assert result['multiplicities'].tolist() == [2, 1, 1]
    assert result['source_indices'] == [[0, 1], [2], [3]]
    np.testing.assert_allclose(result['gaps'], [0., 1e-4, 0.])
