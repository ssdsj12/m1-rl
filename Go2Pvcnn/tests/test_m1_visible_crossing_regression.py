import torch


def test_m1_leg_scale_allows_visible_lift():
    from ame_baseline.m1_ame_contract import M1_LEG_ACTION_SCALE_RAD

    assert M1_LEG_ACTION_SCALE_RAD >= 0.65


def test_crossing_collision_cannot_be_counted_as_success():
    from ame_baseline.m1_crossing_metrics import CrossingEpisodeAccumulator

    metrics = CrossingEpisodeAccumulator(1, "cpu")
    metrics.update(
        candidate=torch.tensor([True]),
        large_candidate=torch.tensor([False]),
        crossing_complete=torch.tensor([False]),
        done=torch.tensor([False]),
        terminated=torch.tensor([False]),
        collision=torch.tensor([True]),
        large_avoided=torch.tensor([False]),
    )
    metrics.update(
        candidate=torch.tensor([False]),
        large_candidate=torch.tensor([False]),
        crossing_complete=torch.tensor([True]),
        done=torch.tensor([True]),
        terminated=torch.tensor([False]),
        collision=torch.tensor([False]),
        large_avoided=torch.tensor([False]),
    )
    snapshot = metrics.snapshot()
    assert snapshot["crossing_collision_episodes"] == 1.0
    assert snapshot["crossing_episodes"] == 0.0
    assert snapshot["crossing_success_rate"] == 0.0
