"""Reject ambiguous checkpoint requests before launching Isaac or allocating GPU memory."""
import importlib.util
import sys
import types
from pathlib import Path
from argparse import Namespace

import pytest


def test_checkpoint_without_resume_is_rejected_before_simulator(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/train_m1_cross_large_complex_ame.py"
    spec = importlib.util.spec_from_file_location("m1_train_guard_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_parse_args", lambda: Namespace(
        num_envs=2, max_iterations=2, resume=False, checkpoint="model_499.pt"))
    def forbidden_launcher(*args, **kwargs):
        pytest.fail("Ambiguous checkpoint reached simulator startup instead of being rejected")
    monkeypatch.setitem(sys.modules, "isaaclab.app", types.SimpleNamespace(AppLauncher=forbidden_launcher))
    with pytest.raises(ValueError, match="--checkpoint requires --resume"):
        module.main()
