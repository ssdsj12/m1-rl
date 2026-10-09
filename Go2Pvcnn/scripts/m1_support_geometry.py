"""Planar projected-center diagnostic, not a dynamic stability certificate."""
from math import hypot, isfinite


def triangle_margin(point, vertices):
    """Signed nearest edge-line distance; None for missing/degenerate data.

    Positive means inside a nondegenerate triangle. Wheel centers are only
    approximations to contacts; slopes, friction and acceleration are omitted.
    """
    if len(vertices) != 3 or len(point) != 2 or any(len(v) != 2 for v in vertices):
        return None
    if not all(isfinite(x) for v in (point, *vertices) for x in v):
        return None
    a, b, c = vertices
    area = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    if abs(area) < 1e-10:
        return None
    sign = 1 if area > 0 else -1
    distances = []
    for u, v in zip(vertices, (*vertices[1:], vertices[0])):
        dx, dy = v[0]-u[0], v[1]-u[1]
        distances.append(sign * (dx*(point[1]-u[1])-dy*(point[0]-u[0])) / hypot(dx,dy))
    return min(distances)
