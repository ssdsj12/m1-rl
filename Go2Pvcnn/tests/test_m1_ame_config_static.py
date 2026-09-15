from __future__ import annotations

import torch

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES,
    M1_PLANNER_JOINT_NAMES,
    M1_WHEEL_JOINT_NAMES,
)
from extension.parallelism.rl_adapter import select_named_joint_state


def test_m1_policy_joint_terms_exclude_wheels():
    asset = torch.arange(16, dtype=torch.float32).reshape(1, 16)
    selected = select_named_joint_state(asset, source_names=M1_ASSET_JOINT_NAMES, selected_names=M1_PLANNER_JOINT_NAMES)
    assert tuple(selected.shape) == (1, 12)
    assert not set((3, 7, 11, 15)) & set(selected.flatten().tolist())


def test_m1_observation_contract_declares_asset_and_planner_widths():
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    cfg = M1AmeCrossLargeComplexEnvCfg()
    assert cfg.robot_name == "m1"
    assert tuple(cfg.planner_joint_names) == M1_PLANNER_JOINT_NAMES
    assert tuple(cfg.wheel_joint_names) == M1_WHEEL_JOINT_NAMES
    assert cfg.action_dim == 16
    assert cfg.asset_joint_names == M1_ASSET_JOINT_NAMES
