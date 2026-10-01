from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import Tensor

from extension.parallelism.types import ParallelismReference, ParallelismTrajectory


def resolve_named_indices(
    source_names: Sequence[str],
    selected_names: Sequence[str],
) -> tuple[int, ...]:
    """Resolve an explicit, unambiguous joint-name projection."""
    source = tuple(source_names)
    selected = tuple(selected_names)
    if len(set(source)) != len(source):
        raise ValueError("duplicate source joint names")
    if len(set(selected)) != len(selected):
        raise ValueError("duplicate selected joint names")
    source_index = {name: index for index, name in enumerate(source)}
    missing = tuple(name for name in selected if name not in source_index)
    if missing:
        raise ValueError(f"selected joint names are absent from source: {missing}")
    return tuple(source_index[name] for name in selected)


def select_named_joint_state(
    state: Tensor,
    *,
    source_names: Sequence[str],
    selected_names: Sequence[str],
) -> Tensor:
    """Project the last dimension of a batched joint tensor by joint name."""
    if state.shape[-1] != len(source_names):
        raise ValueError(
            f"state width {state.shape[-1]} does not match {len(source_names)} source joint names"
        )
    indices = resolve_named_indices(source_names, selected_names)
    index = torch.as_tensor(indices, device=state.device, dtype=torch.long)
    return state.index_select(-1, index)


def trajectory_to_reference(trajectory: ParallelismTrajectory) -> ParallelismReference:
    return ParallelismReference(
        root_pos_w=trajectory.root_pos_w,
        root_rpy_w=trajectory.root_rpy_w,
        joint_pos=trajectory.joint_pos,
        foot_pos_w=trajectory.foot_pos_w,
        contact_state=trajectory.contact_state,
        valid=trajectory.valid,
    )
