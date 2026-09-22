import torch
from m1_crossing_metrics import CrossingEpisodeAccumulator


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
