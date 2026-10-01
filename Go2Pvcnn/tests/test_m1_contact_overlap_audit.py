import numpy as np
import pytest
from scipy.spatial import ConvexHull


@pytest.mark.parametrize("x,state,margin", [(.95, "overlap", -.025), (.85, "boundary", 0.), (.83, "separated", .01)])
def test_source_hull_box_lp_distinguishes_overlap_contact_and_separation(x, state, margin):
    from scripts.audit_m1_contact_events import source_hull_box_margin
    points = np.array([(i, j, k) for i in [-.05, .05] for j in [-.05, .05] for k in [-.05, .05]])
    result = source_hull_box_margin(ConvexHull(points).equations, np.eye(3), [x, 0., .025])
    assert result["state"] == state
    assert result["lp_margin_m"] == pytest.approx(margin, abs=1e-8)
    assert result["lp_residual_m"] < 1e-8


def test_source_hull_box_lp_preserves_rotated_local_frame():
    from scripts.audit_m1_contact_events import source_hull_box_margin
    points = np.array([(i, j, k) for i in [-.05, .05] for j in [-.05, .05] for k in [-.05, .05]])
    theta = .61
    rotation = np.array([[np.cos(theta), -np.sin(theta), 0.], [np.sin(theta), np.cos(theta), 0.], [0., 0., 1.]])
    result = source_hull_box_margin(ConvexHull(points @ rotation).equations, rotation, [.83, 0., .025])
    assert result["state"] == "separated"
    assert result["lp_margin_m"] == pytest.approx(.01, abs=1e-8)
