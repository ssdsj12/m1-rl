"""Regression probes for episode-level false-positive success accounting."""
import torch

from ame_baseline.m1_crossing_metrics import CrossingEpisodeAccumulator


def step(acc, *, candidate=False, large=False, crossed=False, done=False,
         terminated=False, collision=False, avoided=False):
    bit = lambda value: torch.tensor([value], dtype=torch.bool)
    acc.update(candidate=bit(candidate), large_candidate=bit(large),
               crossing_complete=bit(crossed), done=bit(done),
               terminated=bit(terminated), collision=bit(collision),
               large_avoided=bit(avoided))


def test_crossing_followed_by_fall_is_not_episode_success():
    acc = CrossingEpisodeAccumulator(1, 'cpu')
    step(acc, candidate=True, crossed=True)
    step(acc, done=True, terminated=True)
    assert acc.snapshot()['crossing_success_rate'] == 0.0
    assert acc.snapshot()['crossing_failure_rate'] == 1.0


def test_prior_collision_invalidates_large_avoidance_success():
    acc = CrossingEpisodeAccumulator(1, 'cpu')
    step(acc, large=True, collision=True)
    step(acc, large=True, avoided=True, done=True)
    assert acc.snapshot()['large_avoidance_rate'] == 0.0
