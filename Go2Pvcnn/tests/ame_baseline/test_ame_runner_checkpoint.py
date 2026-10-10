from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from ame_baseline import ame_runner
from ame_baseline.ame_runner import AME_ARCHITECTURE_SIGNATURE, AmeOnPolicyRunner


class _TinyActorCritic(torch.nn.Module):
    map_dim = 0
    actor_state_dim = 2
    critic_state_dim = 3

    def __init__(self):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor([1.0]))
        self.std = torch.nn.Parameter(torch.tensor([0.5]))


def _bare_runner() -> AmeOnPolicyRunner:
    runner = object.__new__(AmeOnPolicyRunner)
    actor_critic = _TinyActorCritic()
    runner.device = "cpu"
    runner.alg = SimpleNamespace(
        actor_critic=actor_critic,
        optimizer=torch.optim.Adam(actor_critic.parameters()),
    )
    runner.empirical_normalization = False
    runner.current_learning_iteration = 0
    runner.logger_type = "tensorboard"
    return runner


def test_resume_starts_after_the_last_completed_checkpoint_iteration(tmp_path: Path):
    source = _bare_runner()
    checkpoint = tmp_path / "model_7.pt"
    torch.save(
        {
            "model_state_dict": source.alg.actor_critic.state_dict(),
            "optimizer_state_dict": source.alg.optimizer.state_dict(),
            "iter": 7,
            "infos": None,
            "ame_architecture_signature": AME_ARCHITECTURE_SIGNATURE,
            "ame_num_actor_obs": 2,
            "ame_num_critic_obs": 3,
            "ame_num_actions": 1,
        },
        checkpoint,
    )

    resumed = _bare_runner()
    resumed.load(checkpoint)

    assert resumed.current_learning_iteration == 8


def test_resume_rejects_inconsistent_next_iteration_metadata(tmp_path: Path):
    source = _bare_runner()
    checkpoint = tmp_path / "model_7.pt"
    torch.save(
        {
            "model_state_dict": source.alg.actor_critic.state_dict(),
            "optimizer_state_dict": source.alg.optimizer.state_dict(),
            "iter": 7,
            "next_iter": 11,
            "infos": None,
            "ame_architecture_signature": AME_ARCHITECTURE_SIGNATURE,
            "ame_num_actor_obs": 2,
            "ame_num_critic_obs": 3,
            "ame_num_actions": 1,
        },
        checkpoint,
    )

    with pytest.raises(ValueError, match="next_iter"):
        _bare_runner().load(checkpoint)


def test_atomic_torch_save_keeps_previous_checkpoint_when_write_fails(tmp_path: Path, monkeypatch):
    checkpoint = tmp_path / "model_7.pt"
    torch.save({"generation": "previous"}, checkpoint)

    def fail_after_partial_write(_payload, destination):
        Path(destination).write_bytes(b"partial")
        raise OSError("simulated interrupted checkpoint write")

    monkeypatch.setattr(ame_runner.torch, "save", fail_after_partial_write)

    with pytest.raises(OSError, match="interrupted"):
        ame_runner._atomic_torch_save({"generation": "new"}, checkpoint)

    assert torch.load(checkpoint, map_location="cpu")["generation"] == "previous"
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_ame_save_uploads_only_the_final_checkpoint(tmp_path: Path):
    uploads = []
    runner = _bare_runner()
    runner.current_learning_iteration = 7
    runner.logger_type = "neptune"
    runner.writer = SimpleNamespace(
        save_model=lambda path, iteration: uploads.append((Path(path), iteration))
    )
    checkpoint = tmp_path / "model_7.pt"

    runner.save(checkpoint)

    saved = torch.load(checkpoint, map_location="cpu")
    assert saved["iter"] == 7
    assert saved["next_iter"] == 8
    assert saved["ame_architecture_signature"] == AME_ARCHITECTURE_SIGNATURE
    assert uploads == [(checkpoint, 7)]
    assert list(tmp_path.glob("*.tmp")) == []


def test_flat_first_checkpoint_preserves_course_and_rejects_missing_metadata(tmp_path):
    from ame_baseline.m1_learning_curriculum import LearningCurriculumGate
    gate=LearningCurriculumGate(2048,'cpu')
    gate.stage=2
    runner=_bare_runner()
    resets=[]
    runner.env=SimpleNamespace(unwrapped=SimpleNamespace(_m1_learning_gate=gate),reset=lambda:resets.append(True))
    checkpoint=tmp_path/'new.pt'
    runner.save(checkpoint)
    state=torch.load(checkpoint,map_location='cpu')
    assert state['m1_learning_curriculum']['stage']==2
    gate.stage=0
    runner.load(checkpoint)
    assert gate.stage==2 and resets==[True]
    del state['m1_learning_curriculum']
    torch.save(state,checkpoint)
    with pytest.raises(ValueError,match='curriculum'):
        runner.load(checkpoint)
