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
        self.strict_crossed = torch.zeros_like(self.candidate)
        self.failed = torch.zeros_like(self.candidate)
        self.collision = torch.zeros_like(self.candidate)
        self.avoidance = torch.zeros_like(self.candidate)
        self.counts = {k: 0 for k in ("candidate", "crossed", "strict_crossed", "failed", "collision", "large_candidate", "avoidance")}
        self.episodes = 0

    def update(self, *, candidate, large_candidate, crossing_complete, done, terminated, collision, large_avoided, strict_crossing_complete=None):
        candidate = candidate.bool()
        large_candidate = large_candidate.bool()
        done = done.bool()
        terminated = terminated.bool()
        collision = collision.bool()
        crossing_complete = crossing_complete.bool()
        if strict_crossing_complete is None:
            strict_crossing_complete = torch.zeros_like(crossing_complete)
        strict_crossing_complete = strict_crossing_complete.bool()
        large_avoided = large_avoided.bool()
        self.candidate |= candidate
        self.large_candidate |= large_candidate
        self.collision |= collision
        # A collision at any earlier step invalidates the whole episode.  The
        # old code only masked collisions on the same step, so a scrape followed
        # by candidate disappearance was falsely logged as a success.
        self.crossed |= crossing_complete & ~self.collision
        self.strict_crossed |= strict_crossing_complete & ~self.collision
        # Episode success requires remaining safe after the crossing event.
        # A later fall must revoke the latched success instead of hiding the
        # failure simply because crossing_complete was seen earlier.
        self.failed |= terminated & self.candidate
        self.crossed &= ~self.collision & ~self.failed & ~terminated
        self.strict_crossed &= ~self.collision & ~self.failed & ~terminated
        self.avoidance |= large_avoided & self.large_candidate & done & ~terminated
        self.avoidance &= ~self.collision & ~terminated
        finished = done
        self.episodes += int(finished.sum())
        self.counts["candidate"] += int(self.candidate[finished].sum())
        self.counts["crossed"] += int(self.crossed[finished].sum())
        self.counts["strict_crossed"] += int(self.strict_crossed[finished].sum())
        self.counts["failed"] += int(self.failed[finished].sum())
        self.counts["collision"] += int(self.collision[finished].sum())
        self.counts["large_candidate"] += int(self.large_candidate[finished].sum())
        self.counts["avoidance"] += int(self.avoidance[finished].sum())
        for value in (self.candidate, self.large_candidate, self.crossed, self.strict_crossed, self.failed, self.collision, self.avoidance):
            value[finished] = False

    def snapshot(self) -> dict[str, float]:
        candidates = self.counts["candidate"]
        large = self.counts["large_candidate"]
        finished = self.episodes
        crossed = self.counts["crossed"]
        return {
            "candidate_episodes": float(candidates),
            "crossing_episodes": float(self.counts["crossed"]),
            "strict_crossing_episodes": float(self.counts["strict_crossed"]),
            "crossing_failure_episodes": float(self.counts["failed"]),
            "crossing_collision_episodes": float(self.counts["collision"]),
            "large_obstacle_candidate_episodes": float(large),
            "large_avoidance_episodes": float(self.counts["avoidance"]),
            "semantic_candidate_rate": float("nan") if self.episodes == 0 else candidates / self.episodes,
            # Global rate answers: "what fraction of finished episodes crossed?"
            # The conditional success rate answers: "when an obstacle was
            # encountered, how often did the robot cross it?"  These must not
            # be aliases or TensorBoard cannot distinguish exposure from skill.
            "semantic_crossing_rate": float("nan") if finished == 0 else crossed / finished,
            "crossing_rate": float("nan") if finished == 0 else crossed / finished,
            "crossing_attempt_rate": float("nan") if finished == 0 else candidates / finished,
            "crossing_success_rate": float("nan") if candidates == 0 else crossed / candidates,
            "strict_crossing_success_rate": float("nan") if candidates == 0 else self.counts["strict_crossed"] / candidates,
            "obstacle_crossing_rate": float("nan") if finished == 0 else crossed / finished,
            "crossing_failure_rate": float("nan") if candidates == 0 else self.counts["failed"] / candidates,
            "large_avoidance_rate": float("nan") if large == 0 else self.counts["avoidance"] / large,
        }
