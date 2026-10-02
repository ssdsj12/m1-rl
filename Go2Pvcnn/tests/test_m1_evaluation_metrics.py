import torch

from ame_baseline.m1_evaluation_metrics import EpisodeMetrics


def test_small_course_requires_passing_all_six_obstacles():
    metrics = EpisodeMetrics(1, "cpu", "small")
    before = torch.tensor([[5.3, 0.0]])
    after = torch.tensor([[5.5, 0.0]])
    done = torch.tensor([False])
    metrics.update(before, after, done, torch.tensor([False]), torch.tensor([False]))
    assert not bool(metrics.success.item())
    before = torch.tensor([[5.9, 0.0]])
    after = torch.tensor([[6.1, 0.0]])
    metrics.update(before, after, done, torch.tensor([False]), torch.tensor([False]))
    assert bool(metrics.success.item())
