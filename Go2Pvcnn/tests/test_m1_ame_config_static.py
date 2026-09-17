from __future__ import annotations

from pathlib import Path

import pytest
import torch

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES,
    M1_PLANNER_JOINT_NAMES,
    M1_WHEEL_JOINT_NAMES,
)
from extension.parallelism.rl_adapter import select_named_joint_state


def test_m1_ame_config_wires_nonfinite_robot_state_termination():
    source = (
        Path(__file__).resolve().parents[1] / "ame_baseline" / "m1_ame_env_cfg.py"
    ).read_text(encoding="utf-8")

    assert "class M1AmeTerminationsCfg" in source
    assert "nonfinite_robot_state = DoneTerm(" in source
    assert "func=nonfinite_robot_state" in source
    assert "terminations: M1AmeTerminationsCfg = M1AmeTerminationsCfg()" in source


def test_m1_policy_joint_terms_exclude_wheels():
    asset = torch.arange(16, dtype=torch.float32).reshape(1, 16)
    selected = select_named_joint_state(asset, source_names=M1_ASSET_JOINT_NAMES, selected_names=M1_PLANNER_JOINT_NAMES)
    assert tuple(selected.shape) == (1, 12)
    assert not set((3, 7, 11, 15)) & set(selected.flatten().tolist())


def test_m1_observation_contract_declares_asset_and_planner_widths():
    pytest.importorskip("isaaclab")
    pytest.importorskip("omni.kit.app", reason="Isaac Sim application modules are unavailable in plain pytest")
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_ame_terminations import nonfinite_robot_state
    cfg = M1AmeCrossLargeComplexEnvCfg()
    assert cfg.robot_name == "m1"
    assert tuple(cfg.planner_joint_names) == M1_PLANNER_JOINT_NAMES
    assert tuple(cfg.wheel_joint_names) == M1_WHEEL_JOINT_NAMES
    assert cfg.action_dim == 16
    assert cfg.asset_joint_names == M1_ASSET_JOINT_NAMES
    assert cfg.terminations.nonfinite_robot_state.func is nonfinite_robot_state
