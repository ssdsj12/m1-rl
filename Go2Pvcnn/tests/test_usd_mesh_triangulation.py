import numpy as np
import pytest

from extension.mesh_triangulation import triangulate_convex_faces


def test_plane_quad_and_triangle_keep_their_boundaries_and_winding():
    actual = triangulate_convex_faces([4, 3], [0, 1, 2, 3, 4, 5, 6])
    np.testing.assert_array_equal(actual, [[0, 1, 2], [0, 2, 3], [4, 5, 6]])


def test_triangle_fast_path_and_empty_mesh():
    np.testing.assert_array_equal(triangulate_convex_faces([3, 3], [0, 1, 2, 1, 3, 2]), [[0, 1, 2], [1, 3, 2]])
    assert triangulate_convex_faces([], []).shape == (0, 3)


def test_bad_topology_is_rejected_instead_of_grouping_unrelated_vertices():
    with pytest.raises(ValueError, match="topology"):
        triangulate_convex_faces([4], [0, 1, 2])
