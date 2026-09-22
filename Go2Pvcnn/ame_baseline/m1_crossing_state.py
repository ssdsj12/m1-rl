"""Pure tensor crossing lifecycle for the M1 semantic obstacle task."""
from __future__ import annotations

from dataclasses import dataclass
import torch


NO_OBSTACLE = 0
APPROACH = 1
FRONT_AXLE_CROSSING = 2
REAR_AXLE_CROSSING = 3
COMPLETED = 4
FAILED = 5


@dataclass
class CrossingState:
    phase: torch.Tensor
    candidate: torch.Tensor
    crossed_front: torch.Tensor
    crossed_rear: torch.Tensor
    completed: torch.Tensor
    failed: torch.Tensor

    @classmethod
    def create(cls, num_envs: int, device: torch.device | str) -> "CrossingState":
        z = torch.zeros(num_envs, dtype=torch.bool, device=device)
        return cls(torch.zeros(num_envs, dtype=torch.long, device=device), z.clone(), z.clone(), z.clone(), z.clone(), z.clone())


def update_crossing_state(
    state: CrossingState,
    *,
    candidate: torch.Tensor,
    wheel_x_from_obstacle: torch.Tensor,
    wheel_clearance: torch.Tensor,
    large_obstacle: torch.Tensor,
    done: torch.Tensor,
    terminated: torch.Tensor,
    front_clear_x: float = 0.10,
    rear_clear_x: float = 0.10,
    min_clearance_m: float = 0.05,
) -> dict[str, torch.Tensor]:
    """Advance each environment and return one-shot completion/failure events."""
    candidate = candidate.bool() & ~large_obstacle.bool()
    done = done.bool()
    terminated = terminated.bool()
    x = wheel_x_from_obstacle
    clear = wheel_clearance
    front = (x[:, :2] > front_clear_x).all(-1) & (clear[:, :2] >= min_clearance_m).all(-1)
    rear = (x[:, 2:] > rear_clear_x).all(-1) & (clear[:, 2:] >= min_clearance_m).all(-1)
    start = candidate & (state.phase == NO_OBSTACLE)
    state.candidate |= start
    state.phase = torch.where(start, torch.full_like(state.phase, APPROACH), state.phase)
    state.phase = torch.where((state.phase == APPROACH) & ~front, torch.full_like(state.phase, FRONT_AXLE_CROSSING), state.phase)
    state.crossed_front |= (state.phase >= FRONT_AXLE_CROSSING) & front
    state.phase = torch.where(state.crossed_front & ~state.crossed_rear, torch.full_like(state.phase, REAR_AXLE_CROSSING), state.phase)
    state.crossed_rear |= state.crossed_front & rear
    complete = state.candidate & state.crossed_front & state.crossed_rear & ~done
    state.completed |= complete
    state.phase = torch.where(complete, torch.full_like(state.phase, COMPLETED), state.phase)
    fail = done & terminated & state.candidate & ~state.completed
    state.failed |= fail
    state.phase = torch.where(fail, torch.full_like(state.phase, FAILED), state.phase)
    reset = done
    state.phase = torch.where(reset, torch.zeros_like(state.phase), state.phase)
    state.candidate = torch.where(reset, torch.zeros_like(state.candidate), state.candidate)
    state.crossed_front = torch.where(reset, torch.zeros_like(state.crossed_front), state.crossed_front)
    state.crossed_rear = torch.where(reset, torch.zeros_like(state.crossed_rear), state.crossed_rear)
    state.completed = torch.where(reset, torch.zeros_like(state.completed), state.completed)
    state.failed = torch.where(reset, torch.zeros_like(state.failed), state.failed)
    return {"candidate": start, "completed": complete, "failed": fail}
