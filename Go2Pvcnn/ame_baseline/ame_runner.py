"""Isolated runner adapter and checkpoint validation for AME."""

from __future__ import annotations

import os
from pathlib import Path
import uuid

import torch

from ame_baseline.actor_critic_ame import ActorCriticAME
from rsl_rl.runners import on_policy_runner


AME_ARCHITECTURE_SIGNATURE = "ame_xyz_semantic_v1_c6_s16_mha64_h16"


def _atomic_torch_save(payload, destination: str | Path) -> None:
    """Durably replace a checkpoint without exposing a partial final file."""

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        torch.save(payload, temporary)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


class AmeOnPolicyRunner(on_policy_runner.OnPolicyRunner):
    def __init__(self, *args, **kwargs):
        on_policy_runner.ActorCriticAME = ActorCriticAME
        super().__init__(*args, **kwargs)

    def save(self, path, infos=None):
        destination = Path(path)
        base_checkpoint = destination.with_name(
            f".{destination.name}.{os.getpid()}.{uuid.uuid4().hex}.base.tmp"
        )
        logger_type = self.logger_type
        external_logger = logger_type in ("neptune", "wandb")
        try:
            if external_logger:
                self.logger_type = "tensorboard"
            try:
                super().save(base_checkpoint, infos=infos)
            finally:
                self.logger_type = logger_type
            checkpoint = torch.load(base_checkpoint, map_location="cpu")
            checkpoint["ame_architecture_signature"] = AME_ARCHITECTURE_SIGNATURE
            checkpoint["ame_num_actor_obs"] = self.alg.actor_critic.map_dim + self.alg.actor_critic.actor_state_dim
            checkpoint["ame_num_critic_obs"] = self.alg.actor_critic.map_dim + self.alg.actor_critic.critic_state_dim
            checkpoint["ame_num_actions"] = int(self.alg.actor_critic.std.numel())
            checkpoint["next_iter"] = self.current_learning_iteration + 1
            _atomic_torch_save(checkpoint, destination)
            if external_logger:
                self.writer.save_model(destination, self.current_learning_iteration)
        finally:
            base_checkpoint.unlink(missing_ok=True)

    def load(self, path, load_optimizer=True, keep_std=True):
        checkpoint = torch.load(path, map_location=self.device)
        actual = checkpoint.get("ame_architecture_signature")
        if actual != AME_ARCHITECTURE_SIGNATURE:
            raise ValueError(
                "Checkpoint is not compatible with this AME baseline: "
                f"expected signature {AME_ARCHITECTURE_SIGNATURE!r}, got {actual!r}"
            )
        expected_dims = (
            self.alg.actor_critic.map_dim + self.alg.actor_critic.actor_state_dim,
            self.alg.actor_critic.map_dim + self.alg.actor_critic.critic_state_dim,
            int(self.alg.actor_critic.std.numel()),
        )
        saved_dims = (
            checkpoint.get("ame_num_actor_obs"),
            checkpoint.get("ame_num_critic_obs"),
            checkpoint.get("ame_num_actions"),
        )
        if saved_dims != expected_dims:
            raise ValueError(f"AME checkpoint dimensions {saved_dims} do not match runtime {expected_dims}")
        state_dict = dict(checkpoint["model_state_dict"])
        if not keep_std:
            state_dict.pop("std", None)
        incompatible = self.alg.actor_critic.load_state_dict(state_dict, strict=keep_std)
        if not keep_std and (incompatible.unexpected_keys or incompatible.missing_keys != ["std"]):
            raise RuntimeError(f"Unexpected AME checkpoint incompatibility: {incompatible}")
        if load_optimizer:
            self.alg.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        completed_iteration = int(checkpoint["iter"])
        next_iteration = int(checkpoint.get("next_iter", completed_iteration + 1))
        if next_iteration != completed_iteration + 1:
            raise ValueError(
                "Invalid AME checkpoint iteration metadata: "
                f"iter={completed_iteration}, next_iter={next_iteration}"
            )
        self.current_learning_iteration = next_iteration
        return checkpoint.get("infos")


__all__ = ["AME_ARCHITECTURE_SIGNATURE", "AmeOnPolicyRunner"]
