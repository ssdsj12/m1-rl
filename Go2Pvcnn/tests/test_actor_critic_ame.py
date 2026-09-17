import pytest
import torch

from ame_baseline.actor_critic_ame import ActorCriticAME


def test_ame_forward_shapes_and_finite_distribution():
    net = ActorCriticAME(1581, 1584, 12, map_channels=6, map_size=16)
    actions = net.act(torch.randn(8, 1581))
    assert actions.shape == (8, 12)
    assert net.evaluate(torch.randn(8, 1584)).shape == (8, 1)
    assert torch.isfinite(net.action_std).all()


def test_ame_has_expected_encoder_channels_and_attention():
    net = ActorCriticAME(1581, 1584, 12, map_channels=6, map_size=16)
    assert net.map_cnn[0].in_channels == 6
    assert net.map_cnn[0].out_channels == 16
    assert net.mha.embed_dim == 64 and net.mha.num_heads == 16


def test_ame_rejects_nonfinite_actor_observation_with_clear_error():
    net = ActorCriticAME(1581, 1584, 12, map_channels=6, map_size=16)
    observations = torch.randn(2, 1581)
    observations[1, -1] = torch.nan

    with pytest.raises(RuntimeError, match="non-finite AME actor observation"):
        net.act(observations)


def test_ame_rejects_nonfinite_action_mean_with_clear_error():
    net = ActorCriticAME(1581, 1584, 12, map_channels=6, map_size=16)
    with torch.no_grad():
        net.actor[-1].bias[0] = torch.nan

    with pytest.raises(RuntimeError, match="non-finite AME action mean"):
        net.act(torch.randn(2, 1581))
