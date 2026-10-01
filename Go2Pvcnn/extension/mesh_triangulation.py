"""Triangulate the convex USD faces used by terrain and primitive meshes."""
import numpy as np


def triangulate_convex_faces(face_vertex_counts, face_vertex_indices):
    counts = np.asarray(face_vertex_counts, dtype=np.int64).reshape(-1)
    indices = np.asarray(face_vertex_indices, dtype=np.int32).reshape(-1)
    if np.any(counts < 3) or counts.sum() != indices.size:
        raise ValueError("Invalid USD mesh topology: face counts do not match indices")
    if np.all(counts == 3):
        return indices.reshape(-1, 3)
    triangles, offset = [], 0
    for count in counts:
        face = indices[offset:offset + count]
        triangles.extend((face[0], face[i], face[i + 1]) for i in range(1, int(count) - 1))
        offset += count
    return np.asarray(triangles, dtype=np.int32).reshape(-1, 3)
