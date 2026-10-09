"""PREPARE readiness only; not a controller or a crossing-success metric.

Call on consecutive pre-action samples while all four wheels remain grounded.
The caller supplies a conservative planar support margin for the three wheels
other than the selected leg. Runtime geometry and physics need separate validation.
"""
import torch


class PrepareGate:
    def __init__(self, num_envs, device='cpu'):
        self.episode = torch.full((num_envs,), -1, dtype=torch.long, device=device)
        self.obstacle = self.episode.clone()
        self.leg = self.episode.clone()
        self.step = self.episode.clone()
        self.count = torch.zeros_like(self.episode)
        self.poisoned = torch.zeros(num_envs, dtype=torch.bool, device=device)

    def update(self, *, episode, obstacle, leg, step, force, tilt, tilt_rate,
               margin, ik_valid, collision):
        batch = self.count.shape[0]
        fields = {
            'episode': (episode, (batch,), torch.long),
            'obstacle': (obstacle, (batch,), torch.long),
            'leg': (leg, (batch,), torch.long),
            'step': (step, (batch,), torch.long),
            'force': (force, (batch, 4), None),
            'tilt': (tilt, (batch, 2), None),
            'tilt_rate': (tilt_rate, (batch, 2), None),
            'margin': (margin, (batch,), None),
            'ik_valid': (ik_valid, (batch,), torch.bool),
            'collision': (collision, (batch,), torch.bool),
        }
        for name, (value, shape, dtype) in fields.items():
            if (not isinstance(value, torch.Tensor) or value.shape != shape
                    or value.device != self.count.device
                    or (dtype is not None and value.dtype != dtype)
                    or (dtype is None and not value.is_floating_point())):
                raise ValueError(f'{name}: invalid shape, dtype or device')
        same_event = (episode == self.episode) & (obstacle == self.obstacle)
        consecutive = same_event & (leg == self.leg) & (step == self.step + 1)
        self.poisoned = (self.poisoned & same_event) | collision
        finite = (torch.isfinite(force).all(-1) & torch.isfinite(tilt).all(-1)
                  & torch.isfinite(tilt_rate).all(-1) & torch.isfinite(margin))
        safe = (finite & (force > 10.).all(-1) & (tilt.abs() <= .15).all(-1)
                & (tilt_rate.abs() <= .20).all(-1) & (margin >= .02)
                & ik_valid & ~self.poisoned & (episode >= 0) & (obstacle >= 0)
                & (leg >= 0) & (leg < 4) & (step >= 0))
        self.count = torch.where(
            safe, torch.where(consecutive, self.count + 1, 1), 0
        ).clamp(max=5)
        self.episode, self.obstacle, self.leg, self.step = [
            x.clone() for x in (episode, obstacle, leg, step)
        ]
        return self.count >= 5
