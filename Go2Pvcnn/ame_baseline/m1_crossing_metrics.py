"""Episode-level semantic crossing and large-obstacle avoidance accounting."""
from __future__ import annotations

import math
import torch


class CrossingEpisodeAccumulator:
    def __init__(self, num_envs: int, device: torch.device | str):
        self.device = torch.device(device)
        self.candidate = torch.zeros(num_envs, dtype=torch.bool, device=device)
        self.large_candidate = torch.zeros_like(self.candidate)
        self.crossed = torch.zeros_like(self.candidate)
        self.failed = torch.zeros_like(self.candidate)
        self.collision = torch.zeros_like(self.candidate)
        self.avoidance = torch.zeros_like(self.candidate)
        self.counts = {k: 0 for k in ("candidate", "crossed", "failed", "collision", "large_candidate", "avoidance")}

    def update(self, *, candidate, large_candidate, crossing_complete, done, terminated, collision, large_avoided):
        candidate = candidate.bool()
        large_candidate = large_candidate.bool()
        done = done.bool()
        terminated = terminated.bool()
        collision = collision.bool()
        crossing_complete = crossing_complete.bool()
        large_avoided = large_avoided.bool()
        self.candidate |= candidate
        self.large_candidate |= large_candidate
        self.crossed |= crossing_complete
        self.collision |= collision
        self.failed |= terminated & self.candidate & ~self.crossed
        self.avoidance |= large_avoided & self.large_candidate & done & ~terminated
        finished = done
        self.counts["candidate"] += int(self.candidate[finished].sum())
        self.counts["crossed"] += int(self.crossed[finished].sum())
        self.counts["failed"] += int(self.failed[finished].sum())
        self.counts["collision"] += int(self.collision[finished].sum())
        self.counts["large_candidate"] += int(self.large_candidate[finished].sum())
        self.counts["avoidance"] += int(self.avoidance[finished].sum())
        for value in (self.candidate, self.large_candidate, self.crossed, self.failed, self.collision, self.avoidance):
            value[finished] = False

    def snapshot(self) -> dict[str, float]:
        candidates = self.counts["candidate"]
        large = self.counts["large_candidate"]
        return {
            "candidate_episodes": float(candidates),
            "crossing_episodes": float(self.counts["crossed"]),
            "crossing_failure_episodes": float(self.counts["failed"]),
            "crossing_collision_episodes": float(self.counts["collision"]),
            "large_obstacle_candidate_episodes": float(large),
            "large_avoidance_episodes": float(self.counts["avoidance"]),
            "semantic_candidate_rate": float("nan") if candidates == 0 else float(candidates > 0),
            "semantic_crossing_rate": float("nan") if candidates == 0 else self.counts["crossed"] / candidates,
            "crossing_failure_rate": float("nan") if candidates == 0 else self.counts["failed"] / candidates,
            "large_avoidance_rate": float("nan") if large == 0 else self.counts["avoidance"] / large,
        }
