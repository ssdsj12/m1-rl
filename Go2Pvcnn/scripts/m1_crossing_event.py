"""Conservative offline +X single-wheel event check, not whole-robot acceptance.

Caller must supply one contiguous swing including loaded approach/touchdown,
one physical obstacle AABB and a conservative wheel horizontal envelope.
Other headings and sparse/interpolated motion require a separate verifier.
"""
import math


def verify_event(rows, box, radius, clearance=.05, stable_frames=3):
    def result(reason):
        return {'success': reason == 'verified', 'reason': reason}
    if not rows:
        return result('missing_samples')
    near, far, left, right, top = box
    if not all(math.isfinite(v) for v in (*box, radius, clearance)) or radius <= 0 or near >= far or left >= right or stable_frames < 1:
        return result('invalid_geometry')
    episode = rows[0]['episode']
    for row in rows:
        if row['episode'] != episode:
            return result('episode_changed')
        if row['collision'] is None or row['contact'] is None:
            return result('missing_contact_evidence')
        if row['collision']:
            return result('collision')
        if not all(math.isfinite(row[k]) for k in ('x', 'y', 'bottom', 'tilt')):
            return result('nonfinite_state')
        if abs(row['tilt']) > .30:
            return result('unstable_attitude')
    # Loaded approach establishes a real unloading transition.
    if not rows[0]['contact'] or rows[0]['x'] + radius >= near:
        return result('missing_loaded_approach')
    lift = next((i for i, r in enumerate(rows) if not r['contact']), None)
    if lift is None or rows[lift]['x'] + radius >= near:
        return result('late_or_missing_liftoff')
    traversed = False
    stable = 0
    for row in rows[lift:]:
        overlap = row['x'] + radius >= near and row['x'] - radius <= far
        if overlap:
            if not left <= row['y'] <= right:
                return result('not_over_obstacle_footprint')
            if row['bottom'] < top + clearance or row['contact']:
                return result('insufficient_overlap_clearance')
            traversed = True
        elif row['x'] - radius > far and traversed:
            stable = stable + 1 if row['contact'] else 0
            if stable >= stable_frames:
                return result('verified')
        else:
            stable = 0
    return result('missing_stable_far_side_touchdown')
