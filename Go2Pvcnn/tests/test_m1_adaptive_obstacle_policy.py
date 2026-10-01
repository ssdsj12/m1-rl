import torch

from extension.batch_mpc_planner.semantic_policy import crossing_feasibility


def test_crossing_requires_height_and_posture_margin():
    heights = torch.tensor([0.06, 0.24, 0.06])
    rpy = torch.tensor([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.40, 0.0, 0.0]])
    result = crossing_feasibility(heights, rpy, max_height_m=0.18, max_tilt_rad=0.30)
    assert result.tolist() == [True, False, False]