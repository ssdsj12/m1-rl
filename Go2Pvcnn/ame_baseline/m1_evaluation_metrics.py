"""First-episode metrics that do not mistake auto-reset states for outcomes."""
import torch


def collision_from_rewards(step_rewards, names):
    # RewardManager stores these before reset and retains them for this step.
    columns = [names.index(name) for name in ("parallelism_geometry_collision", "undesired_contacts")]
    values = step_rewards[:, columns]
    if not bool(torch.isfinite(values).all()):
        raise ValueError("Nonfinite collision rewards in evaluation")
    return (values != 0).any(-1)


class EpisodeMetrics:
    def __init__(self, num_envs, device, scenario):
        if scenario not in ("flat", "small", "large"):
            raise ValueError("Unknown evaluation scenario")
        self.scenario = scenario
        self.alive = torch.ones(num_envs, dtype=torch.bool, device=device)
        self.collision = torch.zeros_like(self.alive)
        self.invalid = torch.zeros_like(self.alive)
        self.failed = torch.zeros_like(self.alive)
        self.success = torch.zeros_like(self.alive)
        self.route_seen = torch.zeros_like(self.alive)
        self.route_valid = torch.ones_like(self.alive)
        self.max_x = torch.zeros(num_envs, device=device)
        self.max_lateral = torch.zeros_like(self.max_x)
        self.collision_count = 0
        self.active_steps = 0

    def update(self, before, after, done, collision, invalid, terminated=None):
        done = done.bool()
        # In this task all non-timeout terminations are failures. Use the
        # explicit termination mask: failure and timeout can occur together.
        terminated = done if terminated is None else terminated.bool()
        self.failed |= terminated & done & self.alive
        self.collision |= collision & self.alive
        self.invalid |= invalid & done & self.alive
        self.collision_count += int((collision & self.alive).sum())
        self.active_steps += int(self.alive.sum())
        # A done environment's `after` position belongs to a new episode.
        position = torch.where(done[:, None], before, after)
        self.max_x = torch.maximum(self.max_x, torch.where(self.alive, position[:, 0], self.max_x))
        self.max_lateral = torch.maximum(self.max_lateral, torch.where(self.alive, position[:, 1].abs(), self.max_lateral))
        # Gate the whole body passage, not just crossing a finish x coordinate.
        for point in (before, position):
            passage = self.alive & (point[:, 0] >= 1.0) & (point[:, 0] <= 2.2)
            self.route_seen |= passage
            # Small: remain inside a center corridor of the 1.2 m wide box.
            # Large: center clears its half width + M1 half width + margin.
            valid = point[:, 1].abs() <= .30 if self.scenario == "small" else point[:, 1].abs() >= 1.0
            self.route_valid &= ~passage | valid
        # Small-course validation must finish beyond all six fixed obstacles
        # (x=1.20..5.20 m), not merely pass the first 1.2 m block.  Large
        # validation retains its single-box finish gate.
        finish_x = 6.0 if self.scenario == "small" else 2.2
        self.success |= self.alive & ~done & (position[:, 0] > finish_x)
        self.alive &= ~done

    def summary(self):
        safe = self.success & ~self.collision & ~self.invalid & ~self.failed
        result = {
            "goal_reached_rate": float(self.success.float().mean()),
            "collision_free_success_rate": float(safe.float().mean()),
            "body_collision_episode_rate": float(self.collision.float().mean()),
            "body_collision_step_rate": self.collision_count / max(self.active_steps, 1),
            "invalid_state_termination_rate": float(self.invalid.float().mean()),
            "failure_termination_rate": float(self.failed.float().mean()),
            "mean_max_forward_m": float(self.max_x.mean()),
            "mean_max_lateral_m": float(self.max_lateral.mean()),
        }
        if self.scenario != "flat":
            key = "small_crossing_rate" if self.scenario == "small" else "large_avoidance_rate"
            result[key] = float((safe & self.route_seen & self.route_valid).float().mean())
        return result
