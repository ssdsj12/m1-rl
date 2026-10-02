"""Read-only CPU audit of M1 knee proxy samples versus source USD convex hulls.

This does not launch Isaac, change the asset, or claim that a runtime contact
was a false positive. PhysX cooking/contact offsets require separate checks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from pxr import Usd, UsdGeom, UsdPhysics
from scipy.spatial import ConvexHull

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extension.parallelism.robot_backend import get_robot_backend


def main():
    repo = Path(__file__).resolve().parents[2]
    asset = repo / "m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd"
    stage = Usd.Stage.Open(str(asset))
    if stage is None:
        raise RuntimeError(f"Cannot open {asset}")
    cache = UsdGeom.XformCache()
    backend = get_robot_backend("m1")
    reports = []
    for prefix in ("FBL", "FAR"):
        body = next(p for p in stage.Traverse() if p.GetName() == prefix + "_KNEE_LINK")
        inverse = cache.GetLocalToWorldTransform(body).GetInverse()
        meshes = []
        for prim in Usd.PrimRange(body, Usd.TraverseInstanceProxies()):
            if not (prim.IsA(UsdGeom.Mesh) and prim.HasAPI(UsdPhysics.CollisionAPI)):
                continue
            if prim.GetAttribute("physics:collisionEnabled").Get() is False:
                continue
            approximation = prim.GetAttribute("physics:approximation").Get()
            if approximation != "convexHull":
                raise ValueError(f"Unexpected collision approximation: {approximation}")
            points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), dtype=float)
            transform = np.asarray(cache.GetLocalToWorldTransform(prim) * inverse)
            meshes.append((np.c_[points, np.ones(len(points))] @ transform)[:, :3])
        # Each knee currently has one authored collision mesh. Never combine
        # multiple separate collider pieces into an invented single hull.
        if len(meshes) != 1:
            raise ValueError(f"Expected one knee collider, found {len(meshes)}")
        points = meshes[0]
        hull = ConvexHull(points)
        spec = next(s for s in backend.cfg.official_collision_shapes if s.name == prefix + "_knee_box")
        samples, mask = backend.surface_points_builder(
            (spec,), backend.cfg, dtype=torch.float64, device=torch.device("cpu")
        )
        samples = samples[0, mask[0]].numpy()
        gaps = (samples @ hull.equations[:, :3].T + hull.equations[:, 3]).max(axis=1)
        center, size = np.asarray(spec.center_l), np.asarray(spec.size_l)
        bounds_error = np.abs(np.stack((center - size / 2, center + size / 2)) - np.stack((points.min(0), points.max(0))))
        reports.append({
            "shape": spec.name, "mesh_vertices": len(points),
            "bounds_max_error_m": float(bounds_error.max()),
            "source_convex_hull_volume_m3": float(hull.volume),
            "proxy_volume_m3": float(np.prod(size)),
            "proxy_to_hull_volume_ratio": float(np.prod(size) / hull.volume),
            "production_sample_count": len(samples),
            "samples_outside_source_hull": int((gaps > 1e-5).sum()),
            "max_signed_plane_gap_m": float(gaps.max()),
            "samples_l": samples.tolist(), "signed_plane_gaps_m": gaps.tolist(),
        })
    print(json.dumps({"asset": str(asset), "results": reports}, indent=2))
    print("M1_KNEE_PROXY_AUDIT_COMPLETE")


if __name__ == "__main__":
    main()
