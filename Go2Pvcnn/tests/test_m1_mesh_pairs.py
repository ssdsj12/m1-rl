import numpy as np
import pytest


def fixture():
    points=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[.1,.1,.1],[.2,.1,.1],[.1,.2,.1]])
    faces=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3],[4,5,6],[6,5,4]])
    return points,faces


def test_only_oppositely_wound_coincident_pair_is_removed():
    from ame_baseline.m1_mesh_pairs import clean_opposite_pairs
    p,f=fixture();before=f.copy()
    result=clean_opposite_pairs(p,f.reshape(-1))
    np.testing.assert_array_equal(result,f[:4].reshape(-1))
    np.testing.assert_array_equal(f,before)


def test_same_winding_duplicate_is_not_silently_repaired():
    from ame_baseline.m1_mesh_pairs import clean_opposite_pairs
    p,f=fixture();f[-1]=f[-2]
    with pytest.raises(ValueError):clean_opposite_pairs(p,f.reshape(-1))


def test_open_remaining_surface_is_rejected():
    from ame_baseline.m1_mesh_pairs import clean_opposite_pairs
    p,f=fixture()
    with pytest.raises(ValueError):clean_opposite_pairs(p,f[1:].reshape(-1))
