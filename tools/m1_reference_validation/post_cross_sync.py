"""Independent CPU tensor state machine for the fixed single-bar candidate.

No simulator or acceptance evaluator is imported. Completed observe(t) packets
may influence prepare(t+1) only. Every diagnostic is an independent CPU copy.
The bridge owns reset notification deduplication and physical-unit validation.
"""

import math
import numbers

import torch


PARAMETERS = {
    "candidate": "post_cross_sync_v1", "dt": 0.02, "tau": 0.20,
    "alpha": 1.0 - math.exp(-0.02 / 0.20), "ki": 0.5,
    "bias_bound": 1.0, "slew_rate": 1.0, "physical_velocity_limit": 20.0,
    "feedforward": [1.0, 1.0, 1.4, 1.4], "ready_samples": 5,
    "wheel_radius": 0.0959, "bar_center": [0.85, -0.2],
    "bar_size": [0.06, 0.16, 0.06], "clearance": 0.005,
    "force_threshold": 1.0, "root_x_min_exclusive": 1.15,
    "height_min": 0.53, "height_max": 0.61, "tilt_max": 0.45,
    "rounding_atol": 1e-12,
}
GATE_REASONS = {
    "no_packet": 1 << 0, "phase11_not_seen": 1 << 1,
    "ordered_touchdown_missing": 1 << 2, "wave_gate": 1 << 3,
    "nonzero_legs": 1 << 4, "wheel_not_past_bar": 1 << 5,
    "wheel_height": 1 << 6, "ground_force": 1 << 7,
    "root_not_past_gate": 1 << 8, "root_height": 1 << 9,
    "tilt": 1 << 10, "reference_collision": 1 << 11,
    "bar_contact": 1 << 12, "episode_ended": 1 << 13,
}
_ATOL = 1e-12
_BOOL = {"wave_gate", "drive_allowed", "terminated", "timeout", "reference_collision"}
_INT = {"phase", "episode_id", "env_id", "episode_length"}
_INT_DTYPES = {torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8}
_PACKET_SHAPES = {
    "root_pos": (3,), "gravity": (3,), "wheel_pos": (4, 3),
    "wheel_contact_force": (4,), "wheel_bar_force_peak": (4,),
    "nonwheel_bar_force_peak": (13,), "reference_collision": (4,),
    "wave_gate": (), "phase": (), "prepared_actions": (12,),
    "terminated": (), "timeout": (), "wheel_velocity": (4,),
    "applied_actions": (16,), "episode_id": (), "env_id": (),
}
_CURRENT_SHAPES = {
    "wheel_velocity": (4,), "root_pos": (3,), "wave_gate": (),
    "drive_allowed": (), "episode_length": (),
}


class PostCrossSync:
    """Fixed-parameter synchronizer; all persistent tensors reside on CPU."""

    def __init__(self, num_envs=8):
        if isinstance(num_envs, bool) or not isinstance(num_envs, numbers.Integral) or num_envs <= 0:
            raise ValueError("num_envs must be a positive integer")
        self.num_envs = n = int(num_envs)
        self.episode_id = torch.zeros(n, dtype=torch.int64, device="cpu")
        self.active = torch.zeros(n, dtype=torch.bool, device="cpu")
        self.activation_step = torch.full((n,), -1, dtype=torch.int64, device="cpu")
        self.events = torch.full((n, 2, 4), -1, dtype=torch.int64, device="cpu")
        self.seen_phase11 = torch.zeros(n, dtype=torch.bool, device="cpu")
        self.ready_count = torch.zeros(n, dtype=torch.int64, device="cpu")
        self.gate_reasons = torch.full((n,), GATE_REASONS["no_packet"], dtype=torch.int64, device="cpu")
        self.support_ok = torch.zeros(n, dtype=torch.bool, device="cpu")
        self.filtered_velocity = torch.zeros((n, 4), dtype=torch.float64, device="cpu")
        self.error = torch.zeros((n, 4), dtype=torch.float64, device="cpu")
        self.bias = torch.zeros((n, 4), dtype=torch.float64, device="cpu")
        self.previous_output = torch.zeros((n, 4), dtype=torch.float64, device="cpu")
        self.slew_limited = torch.zeros((n, 4), dtype=torch.bool, device="cpu")
        self.bias_limited = torch.zeros(n, dtype=torch.bool, device="cpu")
        self.physical_limited = torch.zeros((n, 4), dtype=torch.bool, device="cpu")
        self.hold = torch.zeros(n, dtype=torch.bool, device="cpu")
        self.integral_paused = torch.ones(n, dtype=torch.bool, device="cpu")
        self._packet_valid = torch.zeros(n, dtype=torch.bool, device="cpu")
        self._ended = torch.zeros(n, dtype=torch.bool, device="cpu")
        self._previous_episode_length = torch.full((n,), -1, dtype=torch.int64, device="cpu")
        self._prepared_episode_id = torch.full((n,), -1, dtype=torch.int64, device="cpu")
        self._packet = None
        self._prepared_step = -1
        self.last_observed_step = -1
        self._next_step = 0
        self._state_schema = {
            name: (tuple(value.shape), value.dtype)
            for name, value in vars(self).items() if isinstance(value, torch.Tensor)
        }

    def _validate_state(self):
        for name, (shape, dtype) in self._state_schema.items():
            value = getattr(self, name)
            if not isinstance(value, torch.Tensor) or value.device.type != "cpu" or tuple(value.shape) != shape or value.dtype != dtype:
                raise ValueError(f"Invalid controller state {name}: shape/dtype/device")
            if not torch.isfinite(value).all():
                raise ValueError(f"Controller state {name} must be finite")
        if (self.bias.abs() > 1.0 + _ATOL).any() or (self.bias.sum(dim=1).abs() > _ATOL).any():
            raise ValueError("Controller bias state must be bounded and zero-mean")
        if (self.episode_id < 0).any() or (self.ready_count < 0).any() or (self.events < -1).any():
            raise ValueError("Invalid controller integer state")
        if ((self.previous_output[self.active] < 0) | (self.previous_output[self.active] > 20)).any():
            raise ValueError("Controller previous output outside physical bounds")

    def _values(self, inputs, shapes):
        if not isinstance(inputs, dict):
            raise ValueError("Inputs must be a dictionary")
        result = {}
        for name, tail in shapes.items():
            if name not in inputs:
                raise ValueError(f"Missing field {name}")
            try:
                raw = torch.as_tensor(inputs[name], device="cpu").detach()
            except (TypeError, ValueError, RuntimeError) as error:
                raise ValueError(f"{name} must be a numeric tensor") from error
            if tuple(raw.shape) != (self.num_envs,) + tail:
                raise ValueError(f"{name} must have shape {(self.num_envs,) + tail}")
            if name in _BOOL:
                if raw.dtype != torch.bool:
                    raise ValueError(f"{name} must have boolean dtype")
                value = raw.to(device="cpu").clone()
            elif name in _INT:
                if raw.dtype not in _INT_DTYPES:
                    raise ValueError(f"{name} must have integer dtype")
                value = raw.to(device="cpu", dtype=torch.int64).clone()
            else:
                if raw.dtype == torch.bool or raw.is_complex():
                    raise ValueError(f"{name} must contain real numeric values")
                value = raw.to(device="cpu", dtype=torch.float64).clone()
                if not torch.isfinite(value).all():
                    raise ValueError(f"{name} must contain only finite values")
                if "force" in name and (value < 0).any():
                    raise ValueError(f"{name} must contain nonnegative force norms")
            result[name] = value
        return result

    @staticmethod
    def _step(step):
        if isinstance(step, bool) or not isinstance(step, numbers.Integral) or step < 0:
            raise ValueError("step must be a nonnegative integer")
        return int(step)

    def reset(self, env_ids=None):
        """Advance only the explicitly reset rows; the bridge deduplicates notices."""
        if env_ids is None:
            ids = torch.arange(self.num_envs, dtype=torch.int64, device="cpu")
        else:
            try:
                ids = torch.as_tensor(env_ids, device="cpu").detach()
            except (TypeError, ValueError, RuntimeError) as error:
                raise ValueError("env_ids must be a one-dimensional integer sequence") from error
            if ids.numel() == 0 and ids.ndim == 1:
                return
            if ids.ndim != 1 or ids.dtype not in _INT_DTYPES:
                raise ValueError("env_ids must be a one-dimensional integer sequence")
            ids = ids.to(torch.int64)
            if (ids < 0).any() or (ids >= self.num_envs).any() or torch.unique(ids).numel() != ids.numel():
                raise ValueError("env_ids must be unique in-range rows")
        self._validate_state()
        self.episode_id[ids] += 1
        for name in self._state_schema:
            if name in {"episode_id", "_prepared_episode_id"}:
                continue
            value = getattr(self, name)
            fill = -1 if name in {"activation_step", "events", "_previous_episode_length"} else 0
            if name == "gate_reasons": fill = GATE_REASONS["no_packet"]
            if name == "integral_paused": fill = True
            value[ids] = fill
        if self._packet is not None:
            for value in self._packet.values():
                value[ids] = 0

    def _update_events(self, step, values):
        # The strict inequalities in time prohibit observing two stages at once.
        alive = ~self._ended
        for column, wheel in enumerate((0, 2)):
            x, y, z = values["wheel_pos"][:, wheel].unbind(dim=1)
            force = values["wheel_contact_force"][:, wheel]
            lateral = (y + 0.2).abs() <= 0.08 + 0.0959 + _ATOL
            raised = z >= 0.06 + 0.0959 + 0.005 - _ATOL
            events = self.events[:, column]
            prelift = alive & lateral & raised & (x <= 0.85 - 0.03 - 0.0959 + _ATOL)
            overbar = (alive & lateral & raised & ((x - 0.85).abs() <= 0.03 + _ATOL)
                       & (force <= 1.0) & (events[:, 0] >= 0) & (events[:, 0] < step))
            passed = (alive & (x >= 0.9759 - _ATOL)
                      & (events[:, 1] >= 0) & (events[:, 1] < step))
            touchdown = (alive & ((z - 0.0959).abs() <= 0.005 + _ATOL)
                         & (x >= 0.9759 - _ATOL) & (force > 1.0)
                         & (events[:, 2] >= 0) & (events[:, 2] < step))
            for index, mask in enumerate((prelift, overbar, passed, touchdown)):
                first = mask & (events[:, index] < 0)
                self.events[first, column, index] = step

    def observe(self, step, packet):
        """Consume a completed pre-reset sample exactly once, after its prepare."""
        step = self._step(step)
        self._validate_state()
        if step != self._prepared_step or step != self.last_observed_step + 1:
            raise ValueError("observe step must match the pending prepare and be consecutive")
        if not torch.equal(self._prepared_episode_id, self.episode_id):
            raise ValueError("Episode generation changed between prepare and observe")
        values = self._values(packet, _PACKET_SHAPES)
        if "step" in packet:
            packet_step = torch.as_tensor(packet["step"], device="cpu")
            if packet_step.numel() != 1 or packet_step.dtype not in _INT_DTYPES or int(packet_step.item()) != step:
                raise ValueError("packet step does not match observe step")
        if not torch.equal(values["env_id"], torch.arange(self.num_envs, device="cpu")):
            raise ValueError("packet env_id must identify each row in environment order")
        if not torch.equal(values["episode_id"], self.episode_id):
            raise ValueError("packet episode_id does not match current reset generations")
        self._update_events(step, values)
        self.seen_phase11 |= (~self._ended) & (values["phase"] == 11)
        self._ended |= values["terminated"] | values["timeout"]
        position = values["wheel_pos"][:, [0, 2]]
        tilt = torch.acos(torch.clamp(-values["gravity"][:, 2], -1.0, 1.0))
        physical_failures = {
            "wheel_not_past_bar": (position[:, :, 0] < 0.9759 - _ATOL).any(dim=1),
            "wheel_height": ((position[:, :, 2] - 0.0959).abs() > 0.005 + _ATOL).any(dim=1),
            "ground_force": (values["wheel_contact_force"][:, [0, 2]] <= 1.0).any(dim=1),
            "root_not_past_gate": values["root_pos"][:, 0] <= 1.15,
            "root_height": ((values["root_pos"][:, 2] < 0.53 - _ATOL)
                            | (values["root_pos"][:, 2] > 0.61 + _ATOL)),
            "tilt": tilt > 0.45 + _ATOL,
            "reference_collision": values["reference_collision"].any(dim=1),
            "bar_contact": ((values["wheel_bar_force_peak"] > 1.0).any(dim=1)
                            | (values["nonwheel_bar_force_peak"] > 1.0).any(dim=1)),
            "episode_ended": self._ended,
        }
        self.support_ok = ~torch.stack(list(physical_failures.values())).any(dim=0)
        failures = {
            **physical_failures, "phase11_not_seen": ~self.seen_phase11,
            "ordered_touchdown_missing": (self.events[:, :, 3] < 0).any(dim=1),
            "wave_gate": values["wave_gate"],
            "nonzero_legs": (values["prepared_actions"] != 0).any(dim=1),
        }
        self.gate_reasons.zero_()
        for name, failed in failures.items():
            self.gate_reasons |= failed.to(torch.int64) * GATE_REASONS[name]
        qualified = self.gate_reasons == 0
        self.ready_count = torch.where(qualified, self.ready_count + 1, torch.zeros_like(self.ready_count))
        self._packet = values
        self._packet_valid.fill_(True)
        self.last_observed_step = step

    def prepare(self, step, original_actions, current):
        """Return final actions and a self-contained CPU tensor diagnostic snapshot."""
        step = self._step(step)
        self._validate_state()
        if step != self._next_step or self.last_observed_step != step - 1:
            raise ValueError("prepare step must be consecutive with observe of the previous step")
        if not isinstance(original_actions, torch.Tensor) or not original_actions.is_floating_point():
            raise ValueError("original_actions must be a floating point torch tensor")
        original = self._values({"original_actions": original_actions}, {"original_actions": (16,)})["original_actions"]
        values = self._values(current, _CURRENT_SHAPES)
        length = values["episode_length"]
        if (length < 0).any() or ((self._previous_episode_length >= 0) & (length < self._previous_episode_length)).any():
            raise ValueError("episode_length decreased without an explicit reset notification")
        new = ~self.active & self._packet_valid & (self.ready_count >= 5)
        active = self.active | new
        reentry = active & (values["wave_gate"] | ~values["drive_allowed"]
                            | (values["root_pos"][:, 0] <= 1.15) | (original[:, :12] != 0).any(dim=1))
        if reentry.any():
            reasons = {
                "wave_gate": values["wave_gate"], "drive_disallowed": ~values["drive_allowed"],
                "root_not_past_gate": values["root_pos"][:, 0] <= 1.15,
                "nonzero_legs": (original[:, :12] != 0).any(dim=1),
            }
            detail = {name: torch.where(mask & active)[0].tolist() for name, mask in reasons.items() if (mask & active).any()}
            raise ValueError(f"Post-cross applicability failure before action override: {detail}")
        if new.any():
            actual = self._packet["applied_actions"][new, 12:16]
            if ((actual < 0) | (actual > 20)).any():
                raise ValueError("Last actual wheel action is outside forward physical bounds; cannot hold")
        prior_limited = self.hold | self.slew_limited.any(dim=1) | self.physical_limited.any(dim=1)
        ongoing = self.active.clone()
        update = ongoing & self._packet_valid & self.support_ok & ~prior_limited
        velocity = values["wheel_velocity"]
        self.filtered_velocity[ongoing] += PARAMETERS["alpha"] * (velocity[ongoing] - self.filtered_velocity[ongoing])
        self.filtered_velocity[new] = velocity[new]
        self.error[active] = self.filtered_velocity[active].mean(dim=1, keepdim=True) - self.filtered_velocity[active]
        self.bias_limited.zero_()
        if update.any():
            proposed = self.bias[update] + 0.5 * 0.02 * self.error[update]
            centered = proposed - proposed.mean(dim=1, keepdim=True)
            scale = centered.abs().amax(dim=1, keepdim=True).clamp(min=1.0)
            self.bias[update] = centered / scale
            self.bias_limited[update] = scale[:, 0] > 1.0
        self.bias[new] = 0
        desired = torch.tensor([1.0, 1.0, 1.4, 1.4], dtype=torch.float64, device="cpu") + self.bias
        self.slew_limited.zero_()
        self.physical_limited.zero_()
        if ongoing.any():
            delta = desired[ongoing] - self.previous_output[ongoing]
            limited = self.previous_output[ongoing] + delta.clamp(min=-0.02, max=0.02)
            safe = limited.clamp(min=0.0, max=20.0)
            self.slew_limited[ongoing] = delta.abs() > 0.02
            self.physical_limited[ongoing] = safe != limited
            self.previous_output[ongoing] = safe
        if new.any():
            self.previous_output[new] = self._packet["applied_actions"][new, 12:16]
        self.hold = new
        self.integral_paused = ~update
        self.activation_step[new] = step
        self.active = active
        # Finite inputs can still overflow during arithmetic. Fail before any
        # caller can apply the output, even on the first hold sample.
        self._validate_state()
        final = original_actions.detach().clone()
        final[self.active.to(final.device), 12:16] = self.previous_output[self.active].to(device=final.device, dtype=final.dtype)
        self._previous_episode_length = length
        self._prepared_episode_id = self.episode_id.clone()
        self._prepared_step = step
        self._next_step += 1
        diagnostic = {
            key: getattr(self, key).clone() for key in (
                "episode_id", "active", "activation_step", "events", "ready_count",
                "gate_reasons", "support_ok", "filtered_velocity", "error", "bias",
                "slew_limited", "bias_limited", "physical_limited", "hold", "integral_paused",
            )
        }
        diagnostic.update({
            "original_actions": original_actions.detach().cpu().clone(),
            "final_actions": final.detach().cpu().clone(), "velocity": velocity.clone(),
        })
        return final, diagnostic
