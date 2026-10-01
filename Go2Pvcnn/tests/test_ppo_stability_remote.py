import torch


def test_stable_log_ratio_is_finite_and_bounded():
    from rsl_rl.algorithms.ppo import stable_log_ratio

    new_log_prob = torch.tensor([float("inf"), -float("inf"), 100.0, -100.0, 0.5])
    old_log_prob = torch.zeros_like(new_log_prob)
    result = stable_log_ratio(new_log_prob, old_log_prob, limit=5.0)
    assert torch.isfinite(result).all()
    assert result.max().item() <= 5.0
    assert result.min().item() >= -5.0


def test_masked_surrogate_ignores_teacher_outlier():
    from rsl_rl.algorithms.ppo import ppo_surrogate_loss

    # The inactive teacher row has a deliberately absurd log-ratio.  It must
    # not affect the student PPO actor loss.
    new_log_prob = torch.tensor([0.0, 1000.0])
    old_log_prob = torch.zeros_like(new_log_prob)
    advantages = torch.tensor([1.0, -1.0])
    active = torch.tensor([1.0, 0.0])
    loss = ppo_surrogate_loss(
        new_log_prob,
        old_log_prob,
        advantages,
        active,
        clip_param=0.2,
        log_ratio_limit=5.0,
    )
    assert torch.isfinite(loss)
    assert abs(loss.item() + 1.0) < 1.0e-6
