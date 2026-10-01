#  Copyright 2021 ETH Zurich, NVIDIA CORPORATION
#  SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import torch
import torch.nn as nn
import torch.optim as optim

from rsl_rl.modules import ActorCritic
from rsl_rl.storage import RolloutStorage


def _safe_ppo_ratio(
    actions_log_prob: torch.Tensor,
    old_actions_log_prob: torch.Tensor,
    *,
    max_log_ratio: float = 20.0,
) -> torch.Tensor:
    """Return a finite PPO ratio from two log-probability tensors.

    Teacher-controlled actions can be far in the tail of the student's
    Normal distribution.  Computing ``exp(new_log_prob - old_log_prob)``
    directly lets one such sample overflow and poison the actor update.
    Keep the log-ratio finite and bounded before exponentiation so PPO's
    own clipping remains numerically meaningful.
    """
    old = old_actions_log_prob
    if old.ndim > actions_log_prob.ndim:
        old = old.squeeze(-1)
    log_ratio = actions_log_prob - old
    if not bool(torch.isfinite(log_ratio).all().item()):
        raise RuntimeError("non-finite PPO log ratio")
    bound = float(max_log_ratio)
    if not torch.isfinite(torch.as_tensor(bound)) or bound <= 0.0:
        raise ValueError("max_log_ratio must be finite and positive")
    return torch.exp(log_ratio.clamp(min=-bound, max=bound))


def stable_log_ratio(
    actions_log_prob: torch.Tensor,
    old_actions_log_prob: torch.Tensor,
    *,
    limit: float = 5.0,
) -> torch.Tensor:
    """Return a finite, bounded log-ratio for numerical-regression tests.

    ``_safe_ppo_ratio`` is kept as the runtime API used by PPO.  This helper
    exposes the bounded pre-exponential quantity so callers can verify the
    protection without constructing a policy or rollout buffer.
    """
    old = old_actions_log_prob
    if old.ndim > actions_log_prob.ndim:
        old = old.squeeze(-1)
    bound = float(limit)
    if not torch.isfinite(torch.as_tensor(bound)) or bound <= 0.0:
        raise ValueError("limit must be finite and positive")
    raw = actions_log_prob - old
    return torch.nan_to_num(raw, nan=0.0, posinf=bound, neginf=-bound).clamp(
        min=-bound, max=bound
    )


def ppo_surrogate_loss(
    actions_log_prob: torch.Tensor,
    old_actions_log_prob: torch.Tensor,
    advantages: torch.Tensor,
    active_mask: torch.Tensor,
    *,
    clip_param: float,
    log_ratio_limit: float = 5.0,
) -> torch.Tensor:
    """Stable masked PPO actor loss used by unit tests and diagnostics."""
    log_ratio = stable_log_ratio(
        actions_log_prob, old_actions_log_prob, limit=log_ratio_limit
    )
    ratio = torch.exp(log_ratio)
    return _masked_ppo_surrogate_loss(
        advantages,
        ratio,
        clip_param=clip_param,
        active_mask=active_mask,
    )[0]


def _masked_ppo_surrogate_loss(
    advantages: torch.Tensor,
    ratio: torch.Tensor,
    *,
    clip_param: float,
    active_mask: torch.Tensor,
) -> tuple[torch.Tensor, int]:
    """Compute PPO's clipped actor loss only for policy-controlled samples."""
    active = active_mask.reshape(-1) > 0.5
    active_count = int(active.sum().item())
    if active_count == 0:
        return ratio.new_zeros(()), 0
    adv = advantages.reshape(-1)
    ratio_flat = ratio.reshape(-1)
    surrogate = -adv * ratio_flat
    surrogate_clipped = -adv * torch.clamp(
        ratio_flat, 1.0 - clip_param, 1.0 + clip_param
    )
    return torch.max(surrogate[active], surrogate_clipped[active]).mean(), active_count


class PPO:
    actor_critic: ActorCritic

    def __init__(
        self,
        actor_critic,
        num_learning_epochs=1,
        num_mini_batches=1,
        clip_param=0.2,
        gamma=0.998,
        lam=0.95,
        value_loss_coef=1.0,
        entropy_coef=0.0,
        learning_rate=1e-3,
        max_grad_norm=1.0,
        use_clipped_value_loss=True,
        schedule="fixed",
        desired_kl=0.01,
        device="cpu",
        clip_min_std=1e-15,
        pvcnn_model=None,
        replay_buffer=None,
        shared_state_dict=None,
        # Multi-GPU settings
        distributed=False,
        rank=0,
        world_size=1,
        imitation_coef=0.0,
        ppo_log_ratio_clip=5.0,
    ):
        self.device = device
        
        # Multi-GPU settings
        self.distributed = distributed
        self.rank = rank
        self.world_size = world_size
        
        if self.distributed:
            import torch.distributed as dist
            self.dist = dist
            print(f"[PPO Rank {self.rank}] Distributed training enabled (world_size={self.world_size})")

        self.desired_kl = desired_kl
        self.schedule = schedule
        self.learning_rate = learning_rate

        # PPO components
        self.actor_critic = actor_critic
        self.actor_critic.to(self.device)
        self.storage = None  # initialized later
        
        # PVCNN semantic segmentation (optional)
        self.pvcnn_model = pvcnn_model
        self.pvcnn_learning_rate = 1e-4  # Separate learning rate for PVCNN
        self.pvcnn_optimizer = None
        
        if pvcnn_model is not None:
            self.pvcnn_model.to(self.device)
            # PVCNN starts in eval mode for feature extraction
            self.pvcnn_model.eval()
            # Create separate optimizer for PVCNN
            self.pvcnn_optimizer = optim.Adam(self.pvcnn_model.parameters(), lr=self.pvcnn_learning_rate)
            if self.rank == 0:
                print(f"[PPO] PVCNN model integrated for separate training")
                print(f"[PPO] Synchronous training: PPO update -> PVCNN update -> repeat")
        
        # Optimizer only for actor_critic
        self.optimizer = optim.Adam(self.actor_critic.parameters(), lr=learning_rate)
        
        self.transition = RolloutStorage.Transition()

        # PPO parameters
        self.clip_param = clip_param
        self.num_learning_epochs = num_learning_epochs
        self.num_mini_batches = num_mini_batches
        self.value_loss_coef = value_loss_coef
        self.entropy_coef = entropy_coef
        self.gamma = gamma
        self.lam = lam
        self.max_grad_norm = max_grad_norm
        self.use_clipped_value_loss = use_clipped_value_loss
        self.clip_min_std = (
            torch.tensor(clip_min_std, device=self.device) if isinstance(clip_min_std, (tuple, list)) else clip_min_std
        )
        self.imitation_coef = float(imitation_coef)
        self.ppo_log_ratio_clip = float(ppo_log_ratio_clip)
        if self.imitation_coef < 0.0:
            raise ValueError("imitation_coef must be non-negative")
        if not torch.isfinite(torch.as_tensor(self.ppo_log_ratio_clip)) or self.ppo_log_ratio_clip <= 0.0:
            raise ValueError("ppo_log_ratio_clip must be finite and positive")
        self.last_skipped_updates = 0
        self.last_imitation_loss = 0.0

    def init_storage(self, num_envs, num_transitions_per_env, actor_obs_shape, critic_obs_shape, action_shape):
        self.storage = RolloutStorage(
            num_envs, num_transitions_per_env, actor_obs_shape, critic_obs_shape, action_shape, self.device
        )

    def test_mode(self):
        self.actor_critic.test()

    def train_mode(self):
        self.actor_critic.train()

    def act(self, obs, critic_obs, env=None):
        if self.actor_critic.is_recurrent:
            self.transition.hidden_states = self.actor_critic.get_hidden_states()
        # Compute the actions and values
        self.transition.actions = self.actor_critic.act(obs).detach()
        self.transition.values = self.actor_critic.evaluate(critic_obs).detach()
        self.transition.actions_log_prob = self.actor_critic.get_actions_log_prob(self.transition.actions).detach()
        self.transition.action_mean = self.actor_critic.action_mean.detach()
        self.transition.action_sigma = self.actor_critic.action_std.detach()
        # need to record obs and critic_obs before env.step()
        self.transition.observations = obs
        self.transition.critic_observations = critic_obs
        
        # Get point cloud and semantic labels from environment (if available)
        if env is not None and hasattr(env.unwrapped, 'last_point_cloud'):
            self.transition.point_cloud = env.unwrapped.last_point_cloud
            self.transition.semantic_labels = env.unwrapped.last_semantic_labels
        else:
            self.transition.point_cloud = None
            self.transition.semantic_labels = None
        
        return self.transition.actions

    def update_transitions(self, transitions):
        self.transition.transitions = transitions

    def process_env_step(self, rewards, dones, infos):
        self.transition.rewards = rewards.clone()
        self.transition.dones = dones
        # Bootstrapping on time outs
        if "time_outs" in infos:
            self.transition.rewards += self.gamma * torch.squeeze(
                self.transition.values * infos["time_outs"].unsqueeze(1).to(self.device), 1
            )

        # Record the transition
        self.storage.add_transitions(self.transition)
        self.transition.clear()
        self.actor_critic.reset(dones)
    
    def train_pvcnn_on_collected_data(self, num_epochs=5):
        """Train PVCNN on collected point clouds and semantic labels (synchronous)."""
        if self.pvcnn_model is None or self.pvcnn_optimizer is None:
            return 0.0
        
        # Check if we have point cloud data
        if not hasattr(self.storage, 'point_clouds') or self.storage.point_clouds is None:
            return 0.0
        
        if self.storage.semantic_labels is None:
            return 0.0
        
        # Switch PVCNN to training mode
        self.pvcnn_model.train()
        
        # Get all point clouds and labels from storage
        # storage.point_clouds: (num_envs, num_steps, num_points, 3)
        # storage.semantic_labels: (num_envs, num_steps, num_points)
        num_envs, num_steps = self.storage.point_clouds.shape[:2]
        point_clouds = self.storage.point_clouds.view(-1, *self.storage.point_clouds.shape[2:])  # (batch, num_points, 3)
        semantic_labels = self.storage.semantic_labels.view(-1, *self.storage.semantic_labels.shape[2:])  # (batch, num_points)
        
        total_samples = point_clouds.shape[0]
        batch_size = min(64, total_samples)
        
        total_loss = 0.0
        num_batches = 0
        
        # Train for multiple epochs
        for epoch in range(num_epochs):
            # Shuffle data
            indices = torch.randperm(total_samples, device=self.device)
            
            for i in range(0, total_samples, batch_size):
                batch_indices = indices[i:i+batch_size]
                batch_point_clouds = point_clouds[batch_indices]  # (batch, num_points, 3)
                batch_labels = semantic_labels[batch_indices]  # (batch, num_points)
                
                # Skip if invalid data
                if torch.isnan(batch_point_clouds).any() or torch.isinf(batch_point_clouds).any():
                    continue
                
                # Forward pass: PVCNN expects (batch, 3, num_points)
                point_clouds_input = batch_point_clouds.transpose(1, 2)
                
                self.pvcnn_optimizer.zero_grad()
                output = self.pvcnn_model(point_clouds_input)
                
                # Extract logits
                if isinstance(output, dict):
                    logits = output['logits']  # (batch, num_classes, num_points)
                else:
                    logits = output
                
                # Compute loss
                num_classes = logits.shape[1]
                num_points = logits.shape[2]
                
                # Reshape: (batch*num_points, num_classes) and (batch*num_points,)
                logits_flat = logits.permute(0, 2, 1).reshape(-1, num_classes)
                labels_flat = batch_labels.reshape(-1)
                
                # Filter valid labels (>= 0)
                valid_mask = labels_flat >= 0
                if valid_mask.sum() == 0:
                    continue
                
                loss = nn.CrossEntropyLoss()(logits_flat[valid_mask], labels_flat[valid_mask])
                
                # Backward，计算梯度
                loss.backward()
                
                # 🔧 Multi-GPU: All-reduce PVCNN gradients
                if self.distributed:
                    for param in self.pvcnn_model.parameters():
                        if param.grad is not None:
                            #发送并平均梯度
                            self.dist.all_reduce(param.grad.data, op=self.dist.ReduceOp.SUM)
                            param.grad.data /= self.world_size
                #更新参数
                self.pvcnn_optimizer.step()
                
                total_loss += loss.item()
                num_batches += 1
        
        # Switch PVCNN back to eval mode
        self.pvcnn_model.eval()
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        
        # 🔧 Multi-GPU: Synchronize loss for consistent logging
        if self.distributed:
            loss_tensor = torch.tensor([avg_loss], device=self.device)
            self.dist.all_reduce(loss_tensor, op=self.dist.ReduceOp.SUM)
            avg_loss = (loss_tensor / self.world_size).item()
        
        return avg_loss

    def compute_returns(self, last_critic_obs):
        last_values = self.actor_critic.evaluate(last_critic_obs).detach()
        self.storage.compute_returns(last_values, self.gamma, self.lam)

    def update(self):
        self.last_skipped_updates = 0
        mean_value_loss = 0
        mean_surrogate_loss = 0
        if self.actor_critic.is_recurrent:
            generator = self.storage.reccurent_mini_batch_generator(self.num_mini_batches, self.num_learning_epochs)
            include_ppo_mask = False
        else:
            generator = self.storage.mini_batch_generator(
                self.num_mini_batches,
                self.num_learning_epochs,
                include_privileged_actions=True,
                include_ppo_mask=True,
                include_imitation_context=True,
            )
            include_ppo_mask = True
        for batch in generator:
            (
                obs_batch,
                critic_obs_batch,
                actions_batch,
                target_values_batch,
                advantages_batch,
                returns_batch,
                old_actions_log_prob_batch,
                old_mu_batch,
                old_sigma_batch,
                hid_states_batch,
                masks_batch,
                point_cloud_batch,
                semantic_labels_batch,
                *optional_batches,
            ) = batch
            # Optional fields are ordered by RolloutStorage's generator:
            # privileged action target, PPO actor mask, imitation weight and
            # plan-valid mask.  Recurrent legacy callers do not provide them.
            optional_index = 0
            privileged_actions_batch = torch.zeros_like(actions_batch)
            if not include_ppo_mask:
                ppo_active_mask_batch = torch.ones_like(advantages_batch)
                imitation_weight_batch = torch.zeros_like(advantages_batch)
                plan_valid_batch = torch.zeros_like(advantages_batch)
            else:
                privileged_actions_batch = optional_batches[optional_index]
                optional_index += 1
                ppo_active_mask_batch = optional_batches[optional_index]
                optional_index += 1
                imitation_weight_batch = optional_batches[optional_index]
                optional_index += 1
                plan_valid_batch = optional_batches[optional_index]
            self.actor_critic.act(obs_batch, masks=masks_batch, hidden_states=hid_states_batch[0])
            actions_log_prob_batch = self.actor_critic.get_actions_log_prob(actions_batch)
            value_batch = self.actor_critic.evaluate(
                critic_obs_batch, masks=masks_batch, hidden_states=hid_states_batch[1]
            )
            mu_batch = self.actor_critic.action_mean
            sigma_batch = self.actor_critic.action_std
            entropy_batch = self.actor_critic.entropy

            # KL
            if self.desired_kl is not None and self.schedule == "adaptive":
                with torch.inference_mode():
                    kl = torch.sum(
                        torch.log(sigma_batch / old_sigma_batch + 1.0e-5)
                        + (torch.square(old_sigma_batch) + torch.square(old_mu_batch - mu_batch))
                        / (2.0 * torch.square(sigma_batch))
                        - 0.5,
                        axis=-1,
                    )
                    kl_mean = torch.mean(kl)
                    
                    # 🔧 Multi-GPU: Synchronize KL divergence for consistent LR adjustment
                    if self.distributed:
                        kl_tensor = torch.tensor([kl_mean], device=self.device)
                        self.dist.all_reduce(kl_tensor, op=self.dist.ReduceOp.SUM)
                        kl_mean = (kl_tensor / self.world_size).item()

                    if kl_mean > self.desired_kl * 2.0:
                        self.learning_rate = max(1e-5, self.learning_rate / 1.5)
                    elif kl_mean < self.desired_kl / 2.0 and kl_mean > 0.0:
                        self.learning_rate = min(1e-2, self.learning_rate * 1.5)

                    for param_group in self.optimizer.param_groups:
                        param_group["lr"] = self.learning_rate

            # Surrogate loss
            ratio = _safe_ppo_ratio(
                actions_log_prob_batch,
                old_actions_log_prob_batch,
                max_log_ratio=self.ppo_log_ratio_clip,
            )
            surrogate_loss, _ppo_active_count = _masked_ppo_surrogate_loss(
                advantages_batch,
                ratio,
                clip_param=self.clip_param,
                active_mask=ppo_active_mask_batch,
            )

            # Value function loss
            if self.use_clipped_value_loss:
                value_clipped = target_values_batch + (value_batch - target_values_batch).clamp(
                    -self.clip_param, self.clip_param
                )
                value_losses = (value_batch - returns_batch).pow(2)
                value_losses_clipped = (value_clipped - returns_batch).pow(2)
                value_loss = torch.max(value_losses, value_losses_clipped).mean()
            else:
                value_loss = (returns_batch - value_batch).pow(2).mean()

            # Compute PPO loss
            active = ppo_active_mask_batch.reshape(-1) > 0.5
            entropy_loss = (
                entropy_batch.reshape(-1)[active].mean()
                if bool(active.any().item())
                else entropy_batch.new_zeros(())
            )
            # Teacher rows are value-learning data and can optionally provide
            # a bounded behavior-cloning target.  The target is detached in
            # storage; only the policy mean receives this gradient.
            imitation_weight = (
                imitation_weight_batch.reshape(-1)
                * plan_valid_batch.reshape(-1)
            ).clamp(min=0.0, max=1.0)
            if self.imitation_coef > 0.0 and bool((imitation_weight > 0.0).any().item()):
                target = torch.nan_to_num(
                    privileged_actions_batch,
                    nan=0.0,
                    posinf=1.0,
                    neginf=-1.0,
                ).clamp(-1.0, 1.0)
                imitation_per_sample = (mu_batch - target).pow(2).mean(dim=-1)
                weight_sum = imitation_weight.sum().clamp_min(1.0)
                imitation_loss = (imitation_per_sample * imitation_weight).sum() / weight_sum
            else:
                imitation_loss = mu_batch.new_zeros(())
            loss = (
                surrogate_loss
                + self.value_loss_coef * value_loss
                - self.entropy_coef * entropy_loss
                + self.imitation_coef * imitation_loss
            )

            # A bad batch must never write NaNs into the optimizer state.  The
            # rollout remains usable for value learning on the next update.
            if not bool(torch.isfinite(loss).item()):
                self.optimizer.zero_grad(set_to_none=True)
                self.last_skipped_updates += 1
                continue

            # Gradient step
            self.optimizer.zero_grad()
            loss.backward()
            
            # 🔧 Multi-GPU: All-reduce gradients across all processes
            if self.distributed:
                # Average gradients across all GPUs
                for param in self.actor_critic.parameters():
                    if param.grad is not None:
                        self.dist.all_reduce(param.grad.data, op=self.dist.ReduceOp.SUM)
                        param.grad.data /= self.world_size
            
            # Clip gradients (only actor_critic, PVCNN not trained)
            grad_norm = nn.utils.clip_grad_norm_(
                self.actor_critic.parameters(), self.max_grad_norm
            )
            gradients_finite = bool(torch.isfinite(grad_norm).item()) and all(
                parameter.grad is None or bool(torch.isfinite(parameter.grad).all().item())
                for parameter in self.actor_critic.parameters()
            )
            if not gradients_finite:
                self.optimizer.zero_grad(set_to_none=True)
                self.last_skipped_updates += 1
                continue
            
            self.optimizer.step()

            mean_value_loss += value_loss.item()
            mean_surrogate_loss += surrogate_loss.item()
            self.last_imitation_loss = float(imitation_loss.detach().item())

        num_updates = max(self.num_learning_epochs * self.num_mini_batches - self.last_skipped_updates, 1)
        mean_value_loss /= num_updates
        mean_surrogate_loss /= num_updates
        
        # 🔧 Multi-GPU: Synchronize losses for consistent logging
        if self.distributed:
            loss_tensor = torch.tensor(
                [mean_value_loss, mean_surrogate_loss], 
                device=self.device
            )
            self.dist.all_reduce(loss_tensor, op=self.dist.ReduceOp.SUM)
            loss_tensor /= self.world_size
            mean_value_loss = loss_tensor[0].item()
            mean_surrogate_loss = loss_tensor[1].item()
        
        self.storage.clear()

        if hasattr(self.actor_critic, "clip_std"):
            self.actor_critic.clip_std(min=self.clip_min_std)

        return mean_value_loss, mean_surrogate_loss
