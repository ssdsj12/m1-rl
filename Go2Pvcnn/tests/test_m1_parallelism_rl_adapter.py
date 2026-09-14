from __future__ import annotations

import pytest
import torch

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES,
    M1_PLANNER_JOINT_NAMES,
    M1_WHEEL_JOINT_NAMES,
)
from extension.parallelism.rl_adapter import resolve_named_indices, select_named_joint_state
from extension.parallelism.robot_backend import get_robot_backend


EXPECTED_ASSET_JOINT_NAMES = (
    "FBL_ABAD_JOINT", "FBL_HIP_JOINT", "FBL_KNEE_JOINT", "FBL_FOOT_JOINT",
    "FAR_ABAD_JOINT", "FAR_HIP_JOINT", "FAR_KNEE_JOINT", "FAR_FOOT_JOINT",
    "RBL_ABAD_JOINT", "RBL_HIP_JOINT", "RBL_KNEE_JOINT", "RBL_FOOT_JOINT",
    "RAR_ABAD_JOINT", "RAR_HIP_JOINT", "RAR_KNEE_JOINT", "RAR_FOOT_JOINT",
)
EXPECTED_PLANNER_INDICES = (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14)


def test_m1_joint_contract_is_explicit_and_disjoint():
    backend = get_robot_backend("m1")
    assert backend.asset_joint_names == EXPECTED_ASSET_JOINT_NAMES
    assert len(backend.planner_joint_names) == 12
    assert len(backend.wheel_joint_names) == 4
    assert set(backend.planner_joint_names).isdisjoint(backend.wheel_joint_names)
    assert backend.planner_joint_names == M1_PLANNER_JOINT_NAMES
    assert backend.wheel_joint_names == M1_WHEEL_JOINT_NAMES


def test_named_asset_to_planner_projection_keeps_only_legs():
    asset_state = torch.arange(16, dtype=torch.float32).reshape(1, 16)
    indices = resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES)
    assert indices == EXPECTED_PLANNER_INDICES
    projected = select_named_joint_state(
        asset_state,
        source_names=M1_ASSET_JOINT_NAMES,
        selected_names=M1_PLANNER_JOINT_NAMES,
    )
    assert projected.tolist() == [[float(index) for index in EXPECTED_PLANNER_INDICES]]


@pytest.mark.parametrize(
    ("source_names", "selected_names", "message"),
    [
        (("a", "a"), ("a",), "duplicate source joint names"),
        (("a", "b"), ("c",), "selected joint names are absent"),
        (("a", "b"), ("a", "a"), "duplicate selected joint names"),
    ],
)
def test_named_projection_rejects_ambiguous_contracts(source_names, selected_names, message):
    with pytest.raises(ValueError, match=message):
        resolve_named_indices(source_names, selected_names)


def test_named_projection_rejects_state_width_mismatch():
    with pytest.raises(ValueError, match="state width"):
        select_named_joint_state(
            torch.zeros(2, 15),
            source_names=M1_ASSET_JOINT_NAMES,
            selected_names=M1_PLANNER_JOINT_NAMES,
        )
