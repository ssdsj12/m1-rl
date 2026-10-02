import torch
from ame_baseline.m1_crossing_metrics import CrossingEpisodeAccumulator


def test_no_candidate_is_unsampled_and_complete_counts():
    m = CrossingEpisodeAccumulator(1, "cpu")
    s = torch.tensor([True])
    m.update(candidate=s, large_candidate=~s, crossing_complete=s, done=s,
             terminated=~s, collision=~s, large_avoided=~s)
    out = m.snapshot()
    assert out["candidate_episodes"] == 1
    assert out["crossing_episodes"] == 1
    assert out["semantic_crossing_rate"] == 1.0
    n = CrossingEpisodeAccumulator(1, "cpu")
    assert torch.isnan(torch.tensor(n.snapshot()["semantic_crossing_rate"]))

def test_collision_cannot_count_as_successful_crossing():
    m = CrossingEpisodeAccumulator(1, "cpu")
    on = torch.tensor([True])
    m.update(candidate=on, large_candidate=~on, crossing_complete=on, done=on,
             terminated=on, collision=on, large_avoided=~on)
    out = m.snapshot()
    assert out["candidate_episodes"] == 1
    assert out["crossing_episodes"] == 0
    assert out["crossing_collision_episodes"] == 1



def test_snapshot_exposes_explicit_crossing_success_rate_aliases():
    m = CrossingEpisodeAccumulator(2, "cpu")
    on = torch.tensor([True])
    off = torch.tensor([False])
    m.update(candidate=torch.tensor([True, False]), large_candidate=torch.tensor([False, False]),
             crossing_complete=torch.tensor([True, False]), done=torch.tensor([True, True]),
             terminated=torch.tensor([False, False]), collision=torch.tensor([False, False]),
             large_avoided=torch.tensor([False, False]))
    out = m.snapshot()
    assert out["crossing_rate"] == 0.5
    assert out["crossing_success_rate"] == 1.0
    assert out["obstacle_crossing_rate"] == 0.5
    assert out["crossing_attempt_rate"] == 0.5



def test_candidate_rate_uses_all_finished_episodes():
    m = CrossingEpisodeAccumulator(2, "cpu")
    candidate = torch.tensor([True, False])
    done = torch.tensor([True, True])
    off = torch.tensor([False, False])
    m.update(candidate=candidate, large_candidate=off, crossing_complete=off,
             done=done, terminated=off, collision=off, large_avoided=off)
    assert m.snapshot()["semantic_candidate_rate"] == 0.5
