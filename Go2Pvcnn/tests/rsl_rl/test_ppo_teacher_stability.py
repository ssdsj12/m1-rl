import math

import pytest
import torch


def test_safe_ppo_ratio_clamps_extreme_log_ratio():
    from rsl_rl.algorithms.ppo import _safe_ppo_ratio

    ratio = _safe_ppo_ratio(
        torch.tensor([1000.0, -1000.0]),
        torch.zeros(2, 1),
    )

    assert torch.isfinite(ratio).all()
    assert float(ratio.max()) <= math.exp(20.0) * 1.001
    assert float(ratio.min()) >= math.exp(-20.0) * 0.999


def test_masked_surrogate_excludes_teacher_outlier():
    from rsl_rl.algorithms.ppo import _masked_ppo_surrogate_loss

    advantages = torch.tensor([[-1.0], [1.0]])
    ratio = torch.tensor([math.exp(20.0), 1.0])
    active = torch.tensor([[0.0], [1.0]])

    loss, active_count = _masked_ppo_surrogate_loss(
        advantages,
        ratio,
        clip_param=0.2,
        active_mask=active,
    )

    assert active_count == 1
    assert torch.isfinite(loss)
    assert torch.allclose(loss, torch.tensor(-1.0))


def test_safe_ppo_ratio_rejects_nonfinite_log_prob():
    from rsl_rl.algorithms.ppo import _safe_ppo_ratio

    with pytest.raises(RuntimeError, match="non-finite PPO log ratio"):
        _safe_ppo_ratio(torch.tensor([float("nan")]), torch.zeros(1, 1))
