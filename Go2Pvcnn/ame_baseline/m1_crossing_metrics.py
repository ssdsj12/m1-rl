"""Episode-level semantic crossing and large-obstacle avoidance accounting."""
from __future__ import annotations

import math
import torch


class CrossingEpisodeAccumulator:
    def __init__(self, num_envs: int, device: torch.device | str, *, strict_mode='episode'):
        if strict_mode not in ('episode','encounter'):
            raise ValueError('strict_mode must be episode or encounter')
        self.strict_mode=strict_mode
        self.device = torch.device(device)
        self.candidate = torch.zeros(num_envs, dtype=torch.bool, device=device)
        self.large_candidate = torch.zeros_like(self.candidate)
        self.crossed = torch.zeros_like(self.candidate)
        self.strict_crossed = torch.zeros_like(self.candidate)
        self.strict_obstacle_attempts = torch.zeros(num_envs, dtype=torch.long, device=device)
        self.strict_obstacle_crossings = torch.zeros(num_envs, dtype=torch.long, device=device)
        self.strict_obstacle_recoveries = torch.zeros_like(self.strict_obstacle_crossings)
        self.strict_recovery_frames = torch.zeros_like(self.strict_obstacle_crossings)
        self.failed = torch.zeros_like(self.candidate)
        self.collision = torch.zeros_like(self.candidate)
        self.avoidance = torch.zeros_like(self.candidate)
        self.counts = {k: 0 for k in ("candidate", "crossed", "strict_crossed", "strict_obstacle_attempts", "strict_obstacle_crossings", "strict_obstacle_recoveries", "strict_recovery_frames", "failed", "collision", "large_candidate", "avoidance")}
        self.episodes = 0

    def update(self, *, candidate, large_candidate, crossing_complete, done, terminated, collision, large_avoided, strict_crossing_complete=None, strict_crossing_attempt=None, strict_crossing_event=None, strict_recovery_complete=None, strict_recovery_frames=None):
        candidate = candidate.bool()
        large_candidate = large_candidate.bool()
        done = done.bool()
        terminated = terminated.bool()
        collision = collision.bool()
        crossing_complete = crossing_complete.bool()
        if strict_crossing_complete is None:
            strict_crossing_complete = torch.zeros_like(crossing_complete)
        strict_crossing_complete = strict_crossing_complete.bool()
        if strict_crossing_attempt is None:
            strict_crossing_attempt = torch.zeros_like(crossing_complete)
        strict_crossing_attempt = strict_crossing_attempt.bool()
        if strict_crossing_event is None:
            strict_crossing_event = torch.zeros_like(crossing_complete)
        if strict_recovery_complete is None:
            strict_recovery_complete = torch.zeros_like(crossing_complete)
        strict_crossing_event = strict_crossing_event.bool()
        strict_recovery_complete = strict_recovery_complete.bool()
        if strict_recovery_frames is None:
            strict_recovery_frames = torch.zeros_like(self.strict_recovery_frames)
        else:
            strict_recovery_frames = torch.as_tensor(
                strict_recovery_frames, dtype=torch.long, device=self.device)
        if (strict_crossing_attempt.shape != self.candidate.shape
                or strict_crossing_event.shape != self.candidate.shape
                or strict_recovery_complete.shape != self.candidate.shape
                or strict_recovery_frames.shape != self.strict_recovery_frames.shape
                or (strict_recovery_frames < 0).any()):
            raise ValueError("strict crossing and recovery metrics must be nonnegative [num_envs]")
        large_avoided = large_avoided.bool()
        self.candidate |= candidate
        self.large_candidate |= large_candidate
        self.collision |= collision
        # A collision at any earlier step invalidates the whole episode.  The
        # old code only masked collisions on the same step, so a scrape followed
        # by candidate disappearance was falsely logged as a success.
        self.crossed |= crossing_complete & ~self.collision
        self.strict_crossed |= strict_crossing_complete & ~self.collision
        self.strict_obstacle_attempts += strict_crossing_attempt.to(self.strict_obstacle_attempts.dtype)
        self.strict_obstacle_crossings += strict_crossing_event.to(self.strict_obstacle_crossings.dtype)
        self.strict_obstacle_recoveries += strict_recovery_complete.to(self.strict_obstacle_recoveries.dtype)
        self.strict_recovery_frames += torch.where(
            strict_recovery_complete, strict_recovery_frames,
            torch.zeros_like(strict_recovery_frames))
        # Crossing and recovery are separate outcomes: a post-crossing fall is
        # still a failed recovery, but must not erase the measured crossing.
        self.failed |= terminated & self.candidate
        self.crossed &= ~self.collision & ~self.failed & ~terminated
        self.strict_crossed &= ~self.collision
        self.avoidance |= large_avoided & self.large_candidate & done & ~terminated
        self.avoidance &= ~self.collision & ~terminated
        finished = done
        self.episodes += int(finished.sum())
        self.counts["candidate"] += int(self.candidate[finished].sum())
        self.counts["crossed"] += int(self.crossed[finished].sum())
        self.counts["strict_crossed"] += int(self.strict_crossed[finished].sum())
        self.counts["strict_obstacle_attempts"] += int(self.strict_obstacle_attempts[finished].sum())
        self.counts["strict_obstacle_crossings"] += int(self.strict_obstacle_crossings[finished].sum())
        self.counts["strict_obstacle_recoveries"] += int(self.strict_obstacle_recoveries[finished].sum())
        self.counts["strict_recovery_frames"] += int(self.strict_recovery_frames[finished].sum())
        self.counts["failed"] += int(self.failed[finished].sum())
        self.counts["collision"] += int(self.collision[finished].sum())
        self.counts["large_candidate"] += int(self.large_candidate[finished].sum())
        self.counts["avoidance"] += int(self.avoidance[finished].sum())
        for value in (self.candidate, self.large_candidate, self.crossed, self.strict_crossed, self.failed, self.collision, self.avoidance, self.strict_obstacle_attempts, self.strict_obstacle_crossings, self.strict_obstacle_recoveries, self.strict_recovery_frames):
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
            "strict_crossing_success_rate": ((float("nan") if self.counts["strict_obstacle_attempts"] == 0 else self.counts["strict_obstacle_crossings"] / self.counts["strict_obstacle_attempts"]) if self.strict_mode=='encounter' else (float("nan") if candidates == 0 else self.counts["strict_crossed"] / candidates)),
            "strict_obstacle_attempts": float(self.counts["strict_obstacle_attempts"]),
            "strict_obstacle_crossings": float(self.counts["strict_obstacle_crossings"]),
            "strict_obstacle_crossing_success_rate": (float("nan") if self.counts["strict_obstacle_attempts"] == 0 else self.counts["strict_obstacle_crossings"] / self.counts["strict_obstacle_attempts"]),
            "strict_obstacle_recoveries": float(self.counts["strict_obstacle_recoveries"]),
            "strict_obstacle_recovery_rate": (float("nan") if self.counts["strict_obstacle_crossings"] == 0 else self.counts["strict_obstacle_recoveries"] / self.counts["strict_obstacle_crossings"]),
            "strict_recovery_mean_frames": (float("nan") if self.counts["strict_obstacle_recoveries"] == 0 else self.counts["strict_recovery_frames"] / self.counts["strict_obstacle_recoveries"]),
            "obstacle_crossing_rate": float("nan") if finished == 0 else crossed / finished,
            "crossing_failure_rate": float("nan") if candidates == 0 else self.counts["failed"] / candidates,
            "large_avoidance_rate": float("nan") if large == 0 else self.counts["avoidance"] / large,
        }
