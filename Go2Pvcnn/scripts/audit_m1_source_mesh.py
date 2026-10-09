"""Read-only source-wheel topology audit. No simulation, CUDA, or USD writes."""
import hashlib
import json
import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics

stage = Usd.Stage.Open('/home/hexinkun/m1_rl/.worktrees/m1-contact-crossing/m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd')
for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()):
    if not (prim.IsA(UsdGeom.Mesh) and prim.HasAPI(UsdPhysics.CollisionAPI) and 'FOOT_LINK' in str(prim.GetPath())):
        continue
    mesh = UsdGeom.Mesh(prim)
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
    counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get())
    indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get())
    result = dict(path=str(prim.GetPath()), points=len(points), faces=len(counts),
                  triangular=bool(np.all(counts == 3)), finite=bool(np.isfinite(points).all()),
                  sha256=hashlib.sha256(points.tobytes()+indices.tobytes()).hexdigest())
    if result['triangular']:
        triangles = indices.reshape(-1, 3)
        result['weld_audits'] = []
        for decimals in (None, 7):
            coords = points if decimals is None else np.round(points, decimals)
            unique, remap = np.unique(coords, axis=0, return_inverse=True)
            tri = remap[triangles]
            duplicate_faces = len(tri) - len(np.unique(np.sort(tri, axis=1), axis=0))
            edges = np.concatenate((tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]))
            undirected, inverse, edge_counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
            signs = np.where(edges[:, 0] < edges[:, 1], 1, -1)
            balance = np.bincount(inverse, weights=signs)
            xyz = points[triangles]
            area2 = np.linalg.norm(np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0]), axis=1)
            result['weld_audits'].append(dict(decimals=decimals, unique_vertices=len(unique),
                boundary_edges=int(np.sum(edge_counts == 1)), nonmanifold_edges=int(np.sum(edge_counts > 2)),
                duplicate_faces=int(duplicate_faces),
                nonmanifold_edge_endpoints=unique[undirected[edge_counts > 2]].tolist(),
                nonmanifold_edge_incidence=edge_counts[edge_counts > 2].tolist(),
                misoriented_two_face_edges=int(np.sum((edge_counts == 2) & (balance != 0))),
                zero_area_faces=int(np.sum(area2 == 0)), minimum_area2=float(area2.min()),
                signed_volume=float(np.einsum('ij,ij->i', xyz[:, 0], np.cross(xyz[:, 1], xyz[:, 2])).sum()/6)))
    print(json.dumps(result), flush=True)
