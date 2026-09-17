from types import SimpleNamespace

import pytest
import torch

from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
from ame_baseline.ame_train_cfg import get_ame_train_cfg


def test_ame_wrapper_flattens_map_before_state():
    wrapper = AmeRslRlEnvWrapper.__new__(AmeRslRlEnvWrapper)
    obs, extras = wrapper._format_observations(
        {
            "policy_elevation_semantic_map": torch.zeros(2, 6, 16, 16),
            "policy_state": torch.ones(2, 45),
            "critic_elevation_semantic_map": torch.zeros(2, 6, 16, 16),
            "critic_state": torch.ones(2, 48),
        }
    )
    assert obs.shape == (2, 6 * 16 * 16 + 45)
    assert extras["observations"]["critic"].shape == (2, 6 * 16 * 16 + 48)


def test_ame_cfg_matches_ppo_baseline():
    cfg = get_ame_train_cfg()
    assert cfg["num_steps_per_env"] == 40
    assert cfg["algorithm"]["num_mini_batches"] == 4
    assert cfg["algorithm"]["desired_kl"] == 0.01


def _wrapper_with_nonfinite_state_mask(mask: torch.Tensor):
    termination_manager = SimpleNamespace(
        active_terms=["nonfinite_robot_state"],
        get_term=lambda name: mask,
    )
    wrapper = AmeRslRlEnvWrapper.__new__(AmeRslRlEnvWrapper)
    wrapper.env = SimpleNamespace(
        unwrapped=SimpleNamespace(
            termination_manager=termination_manager,
            reset_buf=mask.clone(),
        )
    )
    return wrapper


def test_ame_wrapper_zeros_reward_only_for_nonfinite_state_termination():
    wrapper = _wrapper_with_nonfinite_state_mask(torch.tensor([True, False, False]))

    rewards = wrapper._sanitize_rewards(torch.tensor([torch.nan, 2.0, 3.0]))

    torch.testing.assert_close(rewards, torch.tensor([0.0, 2.0, 3.0]))


def test_ame_wrapper_rejects_nonfinite_reward_outside_state_termination():
    wrapper = _wrapper_with_nonfinite_state_mask(torch.tensor([True, False, False]))

    with pytest.raises(RuntimeError, match="non-finite AME reward outside"):
        wrapper._sanitize_rewards(torch.tensor([torch.nan, torch.nan, 3.0]))
