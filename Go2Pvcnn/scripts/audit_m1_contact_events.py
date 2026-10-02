"""CPU diagnostic of a source convex hull against an authored obstacle box.

The common-plane LP margin is not a Euclidean distance, contact force, or
PhysX penetration depth; source hulls need not equal cooked PhysX hulls.
"""
import numpy as np
from scipy.optimize import linprog


def source_hull_box_margin(equations, rotation, position_env,
                           lo=(.9, -.6, 0.), hi=(1.1, .6, .05), eps=1e-6):
    eq = np.asarray(equations, dtype=np.float64)
    rotation = np.asarray(rotation, dtype=np.float64)
    position = np.asarray(position_env, dtype=np.float64)
    if (rotation.shape != (3, 3) or position.shape != (3,)
            or not np.isfinite(eq).all() or not np.isfinite(rotation).all()
            or not np.isfinite(position).all()
            or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-5)
            or abs(np.linalg.det(rotation) - 1.) > 1e-5):
        return {"state": "unknown", "reason": "invalid_geometry_or_pose"}
    scale = np.linalg.norm(eq[:, :3], axis=1)
    normals = eq[:, :3] / scale[:, None]
    offsets = eq[:, 3] / scale
    normals_env = normals @ rotation.T
    matrix = np.vstack((normals_env, np.eye(3), -np.eye(3)))
    rhs = np.concatenate((normals_env @ position - offsets, np.asarray(hi), -np.asarray(lo)))
    result = linprog(
        [0., 0., 0., 1.],
        A_ub=np.column_stack((matrix, -np.ones(len(matrix)))), b_ub=rhs,
        bounds=[(None, None)] * 4, method="highs",
        options={"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9},
    )
    if not result.success or not np.isfinite(result.x).all():
        return {"state": "unknown", "reason": result.message}
    witness, margin = result.x[:3], float(result.x[3])
    residual = float((matrix @ witness - rhs - margin).max())
    if residual > 1e-8:
        return {"state": "unknown", "reason": "LP_residual"}
    state = "overlap" if margin < -eps else "separated" if margin > eps else "boundary"
    return {"state": state, "lp_margin_m": margin,
            "lp_witness_env": witness.tolist(), "lp_residual_m": residual}
