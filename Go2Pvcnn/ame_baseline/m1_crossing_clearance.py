"""Wheel-bottom clearance contract; unload alone never establishes a lift.

The controller may use wheel-center coordinates internally. Its height target
is the obstacle world top plus wheel radius plus the requested bottom gap.
Measured crossing acceptance uses the bottom gap, independently of the target.
"""
import math

MIN_BOTTOM_CLEARANCE_M = 0.03
TARGET_BOTTOM_CLEARANCE_M = 0.04
MAX_TARGET_BOTTOM_CLEARANCE_M = 0.05


def wheel_center_target_z(obstacle_top_z, *, wheel_radius,
                          bottom_clearance=TARGET_BOTTOM_CLEARANCE_M):
    radius, gap = float(wheel_radius), float(bottom_clearance)
    if (not math.isfinite(radius) or radius <= 0 or not math.isfinite(gap)
            or not MIN_BOTTOM_CLEARANCE_M <= gap <= MAX_TARGET_BOTTOM_CLEARANCE_M):
        raise ValueError('positive wheel radius and 0.03--0.05 m bottom clearance required')
    return obstacle_top_z + radius + gap


def wheel_bottom_from_vertices(body_pos_w, body_quat_wxyz, vertices_b):
    """Lowest authored collision-mesh point using measured rigid-body poses.

    Vertices include mesh transforms/offsets in each wheel body frame, not its
    COM frame. This measures mesh geometry, not PhysX contact/SDF offsets.
    """
    import torch
    pos, quat = body_pos_w, body_quat_wxyz
    if (pos.ndim != 3 or pos.shape[1:] != (4, 3)
            or quat.shape != pos.shape[:-1] + (4,)
            or not pos.is_floating_point() or not quat.is_floating_point()
            or pos.device != quat.device):
        raise ValueError('measured wheel body poses must be aligned [B,4,3/4]')
    vertices = torch.as_tensor(vertices_b, dtype=pos.dtype, device=pos.device)
    if vertices.ndim != 3 or vertices.shape[0] != 4 or vertices.shape[2] != 3 or vertices.shape[1] == 0:
        raise ValueError('wheel mesh vertices must be nonempty [4,N,3]')
    if not all(torch.isfinite(x).all() for x in (pos, quat, vertices)):
        raise ValueError('wheel bottom geometry must be finite')
    norm = torch.linalg.vector_norm(quat, dim=-1, keepdim=True)
    if (norm < 1.e-8).any():
        raise ValueError('wheel quaternion must be nonzero')
    w, x, y, z = (quat / norm).unbind(-1)
    # Third row of the body-to-world rotation: compute only world Z.
    row_z = torch.stack((2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)), -1)
    point_z = torch.einsum('bli,lni->bln', row_z, vertices)
    return pos[..., 2] + point_z.amin(-1)


def wheel_extreme_vertices(vertices):
    """Exact linear extrema need only convex-hull vertices, not mesh interiors.

    This reduces a measurement representation; it does not change colliders.
    No Qhull jitter/approximate simplification is permitted.
    """
    import numpy as np
    from scipy.spatial import ConvexHull, QhullError
    points = np.unique(np.asarray(vertices, dtype=np.float64), axis=0)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points) or not np.isfinite(points).all():
        raise ValueError('finite nonempty wheel vertices [N,3] required')
    if len(points) < 4:
        return points.tolist()
    try:
        return points[ConvexHull(points).vertices].tolist()
    except QhullError:
        # Degenerate geometry remains exact, albeit not compressed.
        return points.tolist()


def load_wheel_collision_vertices(stage, robot_path, wheel_body_names):
    """Read static authored meshes once from the replicated M1 asset.

    Fail closed for missing/unsupported geometry. No prim or physics edit.
    Recreate the wrapper if collision geometry is changed at runtime.
    """
    from pxr import Usd, UsdGeom, UsdPhysics, Gf
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    all_vertices = []
    if len(wheel_body_names) != 4:
        raise ValueError('exactly four named wheel bodies required')
    for name in wheel_body_names:
        body = stage.GetPrimAtPath(str(robot_path) + '/' + name)
        if not body:
            raise ValueError('missing wheel body: ' + name)
        world_to_body = cache.GetLocalToWorldTransform(body).GetInverse()
        vertices = []
        for prim in Usd.PrimRange(body, Usd.TraverseInstanceProxies()):
            if not prim.HasAPI(UsdPhysics.CollisionAPI):
                continue
            if not UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get():
                continue
            if not prim.IsA(UsdGeom.Mesh):
                raise ValueError('unsupported wheel collider: ' + str(prim.GetPath()))
            local_to_body = cache.GetLocalToWorldTransform(prim) * world_to_body
            for point in UsdGeom.Mesh(prim).GetPointsAttr().Get() or []:
                vertices.append(tuple(local_to_body.Transform(Gf.Vec3d(*point))))
        if not vertices:
            raise ValueError('missing wheel collision mesh: ' + name)
        all_vertices.append(wheel_extreme_vertices(vertices))
    count = max(map(len, all_vertices))
    return [v + [v[-1]] * (count-len(v)) for v in all_vertices]
