from __future__ import annotations

import pytest
import torch
from types import SimpleNamespace

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES,
    M1_PLANNER_JOINT_NAMES,
    M1_WHEEL_JOINT_NAMES,
)
from extension.parallelism.rl_adapter import resolve_named_indices, select_named_joint_state
from extension.parallelism.robot_backend import get_robot_backend
from tracking.managers.parallelism_reference_manager import ParallelismReferenceManager


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


def _m1_manager_env() -> SimpleNamespace:
    joint_names = list(reversed(M1_ASSET_JOINT_NAMES))
    body_names = ["BASE_LINK", "RAR_FOOT_LINK", "RBL_FOOT_LINK", "FAR_FOOT_LINK", "FBL_FOOT_LINK"]
    joint_pos = torch.tensor(
        [[float(M1_ASSET_JOINT_NAMES.index(name)) for name in joint_names]],
        dtype=torch.float32,
    )
    body_pos_w = torch.zeros(1, len(body_names), 3)
    for index, name in enumerate(body_names):
        body_pos_w[0, index, 0] = float(index)

    class Robot:
        def __init__(self):
            self.joint_names = joint_names
            self.body_names = body_names
            self.data = SimpleNamespace(
                root_pos_w=torch.zeros(1, 3),
                root_quat_w=torch.tensor([[1.0, 0.0, 0.0, 0.0]]),
                joint_pos=joint_pos,
                body_pos_w=body_pos_w,
            )

        def find_bodies(self, names, preserve_order=False):
            requested = [names] if isinstance(names, str) else list(names)
            ids = [self.body_names.index(name) for name in requested]
            return ids, [self.body_names[index] for index in ids]

    env = SimpleNamespace(
        unwrapped=None,
        cfg=SimpleNamespace(robot_name="m1", parallelism_plan_batch_size=64),
        device="cpu",
        num_envs=1,
        scene={"robot": Robot()},
    )
    env.unwrapped = env
    return env


def test_m1_reference_manager_uses_backend_and_projects_named_joint_state():
    manager = ParallelismReferenceManager(_m1_manager_env(), autostart=False)
    state = manager._state(torch.tensor([0]))
    assert manager.robot_backend.name == "m1"
    assert state.joint_pos.shape == (1, 12)
    assert state.joint_pos.tolist() == [[float(index) for index in EXPECTED_PLANNER_INDICES]]


def test_m1_reference_manager_orders_support_bodies_by_backend_contract():
    manager = ParallelismReferenceManager(_m1_manager_env(), autostart=False)
    state = manager._state(torch.tensor([0]))
    assert state.foot_pos_w is not None
    assert state.foot_pos_w[0, :, 0].tolist() == [4.0, 3.0, 2.0, 1.0]
