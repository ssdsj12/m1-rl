import torch
from torch import nn
from torch.distributions import Normal

from rsl_rl.algorithms.ppo import PPO


class _DummyActorCritic(nn.Module):
    is_recurrent = False

    def __init__(self):
        super().__init__()
        self.weight = nn.Parameter(torch.tensor(0.0))
        self._distribution = None

    def act(self, observations, **kwargs):
        mean = self.weight.expand(observations.shape[0], 1)
        self._distribution = Normal(mean, torch.ones_like(mean))
        return self._distribution.sample()

    def evaluate(self, observations, **kwargs):
        return self.weight.expand(observations.shape[0], 1)

    def get_actions_log_prob(self, actions):
        return self._distribution.log_prob(actions).sum(dim=-1)

    @property
    def action_mean(self):
        return self._distribution.mean

    @property
    def action_std(self):
        return self._distribution.stddev

    @property
    def entropy(self):
        return self._distribution.entropy().sum(dim=-1)

    def reset(self, dones=None):
        return None

    def clip_std(self, min=None, max=None):
        return None


def test_ppo_update_masks_teacher_outlier_and_keeps_value_update_finite():
    actor = _DummyActorCritic()
    alg = PPO(
        actor,
        num_learning_epochs=1,
        num_mini_batches=1,
        learning_rate=1.0e-3,
        schedule="fixed",
        device="cpu",
    )
    alg.init_storage(2, 1, [1], [1], [1])

    transition = alg.transition
    transition.observations = torch.zeros(2, 1)
    transition.critic_observations = torch.zeros(2, 1)
    # Row 0 emulates a far-tail teacher action; row 1 is policy controlled.
    transition.actions = torch.tensor([[100.0], [0.0]])
    transition.rewards = torch.tensor([0.0, 1.0])
    transition.dones = torch.zeros(2)
    transition.values = torch.zeros(2, 1)
    transition.actions_log_prob = torch.tensor([[-5000.0], [0.0]])
    transition.action_mean = torch.zeros(2, 1)
    transition.action_sigma = torch.ones(2, 1)
    transition.ppo_active = torch.tensor([0.0, 1.0])
    alg.process_env_step(transition.rewards, transition.dones, {})
    alg.storage.returns[:] = torch.tensor([[[0.0,], [1.0,]]])
    alg.storage.advantages[:] = torch.tensor([[[0.0,], [1.0,]]])

    value_loss, surrogate_loss = alg.update()

    assert torch.isfinite(torch.tensor([value_loss, surrogate_loss])).all()
    assert torch.isfinite(actor.weight).all()
