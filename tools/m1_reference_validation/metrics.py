"""Frozen, NumPy-only first-episode gates for the reference M1 controller.

Samples must describe pre-reset physical state in environment-local coordinates.
Wheel order is FAR, FBL, RAR, RBL. Own-bar force inputs are bodywise norm peaks
over all physical substeps, not generic ground contact or a final substep only.
"""

import numpy as np


BAR_CENTER = (0.85, -0.2)
BAR_SIZE = (0.06, 0.16, 0.06)
WHEEL_RADIUS = 0.0959
REFERENCE_RADIUS = 0.095
CLEARANCE_MARGIN = 0.005
FORCE_THRESHOLD = 1.0
ROOT_TARGET_DX = 1.5
MAX_TILT = 0.45
HEIGHT_TARGET = 0.57
RECOVERY_START_X = 1.1
MAX_HEIGHT_ERROR = 0.04
MAX_ACTION_DELTA = 2.0
MAX_WHEEL_MEAN_SPREAD = 0.08
# Double-precision arithmetic roundoff only; not a float32/physical tolerance.
_ROUNDING_ATOL = 1e-12
_REQUIRED_WHEELS = ((0, "FAR"), (2, "RAR"))
_EVENT_NAMES = ("prelift_step", "overbar_step", "passed_step", "touchdown_step")
_SHAPES = {
    "root_pos": (3,), "gravity": (3,), "wheel_pos": (4, 3),
    "wheel_contact_force": (4,), "wheel_bar_force_peak": (4,),
    "nonwheel_bar_force_peak": (13,), "wheel_velocity": (4,),
    "raw_actions": (16,), "prepared_actions": (12,),
    "joint_posture_error": (12,), "wave_gate": (), "phase": (),
    "terminated": (), "timeout": (), "reference_collision": (4,),
}
_BOOL_FIELDS = {"wave_gate", "terminated", "timeout", "reference_collision"}


def _number(value):
    return float(value) if np.isfinite(value) else None


def _event(value):
    return int(value) if value >= 0 else None


def _le(value, limit):
    return value <= limit + _ROUNDING_ATOL


def _ge(value, limit):
    return value >= limit - _ROUNDING_ATOL


class FirstEpisodeMetrics:
    """Collect each environment until its first termination/timeout, inclusive.

    Reaching the crossing goal never stops collection. update() validates the
    complete sample before consuming a step. report() is read-only and produces
    JSON-safe Python values; its default cannot claim process completion.
    """

    def __init__(self, num_envs, requested_steps, initial_root_pos):
        for name, value in (("num_envs", num_envs), ("requested_steps", requested_steps)):
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        self.num_envs = int(num_envs)
        self.requested_steps = int(requested_steps)
        self.received_steps = 0
        n = self.num_envs
        try:
            initial = np.asarray(initial_root_pos)
        except (TypeError, ValueError) as error:
            raise ValueError("initial_root_pos must be a finite real [num_envs, 3] array") from error
        if initial.shape != (n, 3) or initial.dtype.kind not in "iuf" or not np.all(np.isfinite(initial)):
            raise ValueError("initial_root_pos must be a finite real [num_envs, 3] array")
        self.initial_root_pos = initial.astype(np.float64, copy=True)
        self.active = np.ones(n, dtype=bool)
        self.count = np.zeros(n, dtype=np.int64)
        self.wave_count = np.zeros(n, dtype=np.int64)
        self.nonwave_count = np.zeros(n, dtype=np.int64)
        self.recovery_count = np.zeros(n, dtype=np.int64)
        self.delta_count = np.zeros(n, dtype=np.int64)
        self.reset_count = np.zeros(n, dtype=np.int64)
        self.first_failure_step = np.full(n, -1, dtype=np.int64)
        self.terminated = np.zeros(n, dtype=bool)
        self.timeout = np.zeros(n, dtype=bool)
        self.reference_collision = np.zeros((n, 4), dtype=bool)
        self.phase_max = np.full(n, -1, dtype=np.int64)
        self.root_max_x = np.full(n, -np.inf)
        self.root_final_x = np.full(n, np.nan)
        self.root_height_min = np.full(n, np.inf)
        self.root_height_max = np.full(n, -np.inf)
        self.root_height_sum = np.zeros(n)
        self.last_height_error = np.full(n, np.nan)
        self.recovery_height_sum = np.zeros(n)
        self.recovery_error_sum = np.zeros(n)
        self.recovery_error_max = np.full(n, -np.inf)
        self.max_tilt = np.full(n, -np.inf)
        self.wheel_max_z = np.full((n, 4), -np.inf)
        self.wheel_bar_max = np.zeros((n, 4))
        self.nonwheel_bar_max = np.zeros((n, 13))
        self.raw_abs_max = np.zeros(n)
        self.wave_prepared_sum = np.zeros(n)
        self.wave_prepared_max = np.full(n, -np.inf)
        self.nonwave_prepared_max = np.zeros(n)
        self.wave_posture_error_max = np.full(n, -np.inf)
        self.wave_delta_max = np.full(n, -np.inf)
        self.previous_prepared = np.zeros((n, 12))
        self.velocity_min = np.full((n, 4), np.inf)
        self.velocity_max = np.full((n, 4), -np.inf)
        self.velocity_sum = np.zeros((n, 4))
        self.source_reference_flags = np.zeros((n, 2, 2), dtype=bool)
        # One independent ordered event chain per radius and required wheel.
        self.clearance_events = {
            "strict": np.full((n, 2, 4), -1, dtype=np.int64),
            "reference": np.full((n, 2, 4), -1, dtype=np.int64),
        }

    def _validate(self, sample):
        if not isinstance(sample, dict):
            raise ValueError("sample must be a dictionary containing all required fields")
        validated = {}
        for name, tail in _SHAPES.items():
            if name not in sample:
                raise ValueError(f"Missing sample field: {name}")
            try:
                value = np.asarray(sample[name])
            except (TypeError, ValueError) as error:
                raise ValueError(f"{name} must be a rectangular numeric array") from error
            expected = (self.num_envs,) + tail
            if value.shape != expected:
                raise ValueError(f"{name} must have shape {expected}, got {value.shape}")
            if name in _BOOL_FIELDS:
                if value.dtype.kind != "b":
                    raise ValueError(f"{name} must have boolean dtype")
            elif name == "phase":
                if value.dtype.kind not in "iu":
                    raise ValueError("phase must have integer dtype")
            else:
                if value.dtype.kind not in "iuf":
                    raise ValueError(f"{name} must contain real numeric values")
                value = value.astype(np.float64, copy=False)
                if not np.all(np.isfinite(value)):
                    raise ValueError(f"{name} must contain only finite values")
                if "force" in name and np.any(value < 0):
                    raise ValueError(f"{name} must contain nonnegative force norms")
            validated[name] = value
        return validated

    def _update_clearance(self, step, values):
        for kind, radius in (("strict", WHEEL_RADIUS), ("reference", REFERENCE_RADIUS)):
            events = self.clearance_events[kind]
            for column, (wheel, _) in enumerate(_REQUIRED_WHEELS):
                position = values["wheel_pos"][:, wheel]
                x, y, z = position.T
                lateral = _le(np.abs(y - BAR_CENTER[1]), BAR_SIZE[1] / 2 + radius)
                raised = _ge(z, BAR_SIZE[2] + radius + CLEARANCE_MARGIN)
                prelift = self.active & lateral & raised & _le(x, BAR_CENTER[0] - BAR_SIZE[0] / 2 - radius)
                source_overbar = (
                    self.active & lateral & raised
                    & _le(np.abs(x - BAR_CENTER[0]), BAR_SIZE[0] / 2)
                    & (values["wheel_contact_force"][:, wheel] <= FORCE_THRESHOLD)
                )
                if kind == "reference":
                    self.source_reference_flags[:, column, 0] |= prelift
                    self.source_reference_flags[:, column, 1] |= source_overbar
                overbar = (
                    source_overbar
                    & (events[:, column, 0] >= 0) & (events[:, column, 0] < step)
                )
                passed = (
                    self.active & _ge(x, BAR_CENTER[0] + BAR_SIZE[0] / 2 + radius)
                    & (events[:, column, 1] >= 0) & (events[:, column, 1] < step)
                )
                touchdown = (
                    self.active & _le(np.abs(z - radius), CLEARANCE_MARGIN)
                    & _ge(x, BAR_CENTER[0] + BAR_SIZE[0] / 2 + radius)
                    & (values["wheel_contact_force"][:, wheel] > FORCE_THRESHOLD)
                    & (events[:, column, 2] >= 0) & (events[:, column, 2] < step)
                )
                for event_index, mask in enumerate((prelift, overbar, passed, touchdown)):
                    first = mask & (events[:, column, event_index] < 0)
                    events[first, column, event_index] = step

    def update(self, step, sample):
        if (
            isinstance(step, (bool, np.bool_)) or not isinstance(step, (int, np.integer))
            or step != self.received_steps or step >= self.requested_steps
        ):
            raise ValueError(f"step must be consecutive {self.received_steps} and below {self.requested_steps}")
        values = self._validate(sample)
        active = self.active.copy()
        wave = active & values["wave_gate"]
        nonwave = active & ~values["wave_gate"]
        recovery = active & (values["root_pos"][:, 0] >= RECOVERY_START_X)
        delta_samples = wave & (self.count > 0)
        prepared_abs = np.abs(values["prepared_actions"])
        raw_max = np.max(np.abs(values["raw_actions"]), axis=1)
        height = values["root_pos"][:, 2]
        height_error = np.abs(height - HEIGHT_TARGET)
        tilt = np.arccos(np.clip(-values["gravity"][:, 2], -1.0, 1.0))
        delta = np.max(np.abs(values["prepared_actions"] - self.previous_prepared), axis=1)
        self._update_clearance(step, values)

        self.count[active] += 1
        self.wave_count[wave] += 1
        self.nonwave_count[nonwave] += 1
        self.recovery_count[recovery] += 1
        self.delta_count[delta_samples] += 1
        self.phase_max[active] = np.maximum(self.phase_max[active], values["phase"][active])
        self.root_max_x[active] = np.maximum(self.root_max_x[active], values["root_pos"][active, 0])
        self.root_final_x[active] = values["root_pos"][active, 0]
        self.root_height_min[active] = np.minimum(self.root_height_min[active], height[active])
        self.root_height_max[active] = np.maximum(self.root_height_max[active], height[active])
        self.root_height_sum[active] += height[active]
        self.last_height_error[active] = height_error[active]
        self.recovery_height_sum[recovery] += height[recovery]
        self.recovery_error_sum[recovery] += height_error[recovery]
        self.recovery_error_max[recovery] = np.maximum(self.recovery_error_max[recovery], height_error[recovery])
        self.max_tilt[active] = np.maximum(self.max_tilt[active], tilt[active])
        self.wheel_max_z[active] = np.maximum(self.wheel_max_z[active], values["wheel_pos"][active, :, 2])
        self.wheel_bar_max[active] = np.maximum(self.wheel_bar_max[active], values["wheel_bar_force_peak"][active])
        self.nonwheel_bar_max[active] = np.maximum(self.nonwheel_bar_max[active], values["nonwheel_bar_force_peak"][active])
        self.reference_collision[active] |= values["reference_collision"][active]
        self.raw_abs_max[active] = np.maximum(self.raw_abs_max[active], raw_max[active])
        self.wave_prepared_sum[wave] += np.mean(prepared_abs[wave], axis=1)
        self.wave_prepared_max[wave] = np.maximum(self.wave_prepared_max[wave], np.max(prepared_abs[wave], axis=1))
        self.nonwave_prepared_max[nonwave] = np.maximum(self.nonwave_prepared_max[nonwave], np.max(prepared_abs[nonwave], axis=1))
        self.wave_posture_error_max[wave] = np.maximum(
            self.wave_posture_error_max[wave], np.max(np.abs(values["joint_posture_error"][wave]), axis=1)
        )
        self.wave_delta_max[delta_samples] = np.maximum(self.wave_delta_max[delta_samples], delta[delta_samples])
        self.previous_prepared[active] = values["prepared_actions"][active]
        self.velocity_min[active] = np.minimum(self.velocity_min[active], values["wheel_velocity"][active])
        self.velocity_max[active] = np.maximum(self.velocity_max[active], values["wheel_velocity"][active])
        self.velocity_sum[active] += values["wheel_velocity"][active]

        ended = active & (values["terminated"] | values["timeout"])
        self.reset_count[ended] += 1
        self.terminated[active] |= values["terminated"][active]
        self.timeout[active] |= values["timeout"][active]
        hard_failure = active & (
            ended | (raw_max != 0) | ~_le(tilt, MAX_TILT)
            | np.any(values["reference_collision"], axis=1)
            | np.any(values["wheel_bar_force_peak"] > FORCE_THRESHOLD, axis=1)
            | np.any(values["nonwheel_bar_force_peak"] > FORCE_THRESHOLD, axis=1)
            | (nonwave & (np.max(prepared_abs, axis=1) > 1e-6))
            | (delta_samples & ~_le(delta, MAX_ACTION_DELTA))
        )
        first = hard_failure & (self.first_failure_step < 0)
        self.first_failure_step[first] = step
        self.active[ended] = False
        self.received_steps += 1

    def _clearance_report(self, kind, env):
        return {
            name: {event: _event(value) for event, value in zip(_EVENT_NAMES, self.clearance_events[kind][env, column])}
            for column, (_, name) in enumerate(_REQUIRED_WHEELS)
        }

    def _environment_report(self, env):
        count = int(self.count[env])
        wave_count = int(self.wave_count[env])
        nonwave_count = int(self.nonwave_count[env])
        recovery_count = int(self.recovery_count[env])
        wave_mean = self.wave_prepared_sum[env] / wave_count if wave_count else np.nan
        recovery_mean_height = self.recovery_height_sum[env] / recovery_count if recovery_count else np.nan
        recovery_abs_mean_error = abs(recovery_mean_height - HEIGHT_TARGET)
        recovery_mae = self.recovery_error_sum[env] / recovery_count if recovery_count else np.nan
        velocity_mean = self.velocity_sum[env] / count if count else np.full(4, np.nan)
        velocity_spread = np.max(velocity_mean) - np.min(velocity_mean)
        flags = {
            "has_samples": count > 0,
            "phase_complete": self.phase_max[env] >= 11,
            "root_progress": _ge(self.root_final_x[env] - self.initial_root_pos[env, 0], ROOT_TARGET_DX),
            "tilt": count > 0 and _le(self.max_tilt[env], MAX_TILT),
            "front_wheel_height": self.wheel_max_z[env, 0] >= 0.13,
            "rear_wheel_height": self.wheel_max_z[env, 2] >= 0.14,
            "no_wheel_bar_contact": np.max(self.wheel_bar_max[env]) <= FORCE_THRESHOLD,
            "no_nonwheel_bar_contact": np.max(self.nonwheel_bar_max[env]) <= FORCE_THRESHOLD,
            "no_reference_collision": not np.any(self.reference_collision[env]),
            "no_termination": not self.terminated[env],
            "no_timeout": not self.timeout[env],
            "height_recovery_mean": recovery_count > 0 and _le(recovery_abs_mean_error, MAX_HEIGHT_ERROR),
            "height_last_active": count > 0 and _le(self.last_height_error[env], MAX_HEIGHT_ERROR),
            "zero_raw_actions": self.raw_abs_max[env] == 0,
            "wave_prepared_activity": wave_count > 0 and _ge(wave_mean, 0.02),
            "wave_posture_activity": wave_count > 0 and _ge(self.wave_posture_error_max[env], 0.05),
            "nonwave_prepared_zero": nonwave_count > 0 and self.nonwave_prepared_max[env] <= 1e-6,
            "wave_action_delta": self.delta_count[env] > 0 and _le(self.wave_delta_max[env], MAX_ACTION_DELTA),
            "wheel_mean_angular_speed_spread": count > 0 and _le(velocity_spread, MAX_WHEEL_MEAN_SPREAD),
        }
        for column, (_, name) in enumerate(_REQUIRED_WHEELS):
            for event, value in zip(_EVENT_NAMES, self.clearance_events["strict"][env, column]):
                flags[f"{name}_{event.removesuffix('_step')}"] = value >= 0
        flags = {name: bool(value) for name, value in flags.items()}
        return {
            "env_id": env, "passed": all(flags.values()), "flags": flags,
            "failed_gates": [name for name, passed in flags.items() if not passed],
            "first_failure_step": _event(self.first_failure_step[env]),
            "failure_latched": bool(self.first_failure_step[env] >= 0),
            "active_sample_count": count, "reset_count": int(self.reset_count[env]),
            "terminated": bool(self.terminated[env]), "timeout": bool(self.timeout[env]),
            "phase_max": int(self.phase_max[env]) if count else None,
            "root_initial_pos": self.initial_root_pos[env].tolist(),
            "root_max_x": _number(self.root_max_x[env]),
            "root_final_x": _number(self.root_final_x[env]),
            "root_max_dx": _number(self.root_max_x[env] - self.initial_root_pos[env, 0]),
            "root_final_dx": _number(self.root_final_x[env] - self.initial_root_pos[env, 0]),
            "root_height": {
                "min": _number(self.root_height_min[env]), "max": _number(self.root_height_max[env]),
                "mean": _number(self.root_height_sum[env] / count) if count else None,
            },
            "max_tilt_rad": _number(self.max_tilt[env]),
            "wheel_max_z": [_number(value) for value in self.wheel_max_z[env]],
            "wheel_bar_force_peak_max": _number(np.max(self.wheel_bar_max[env])) if count else None,
            "nonwheel_bar_force_peak_max": _number(np.max(self.nonwheel_bar_max[env])) if count else None,
            "wheel_bar_force_peaks": self.wheel_bar_max[env].tolist() if count else [None] * 4,
            "nonwheel_bar_force_peaks": self.nonwheel_bar_max[env].tolist() if count else [None] * 13,
            "reference_collision": self.reference_collision[env].tolist(),
            "raw_action_abs_max": _number(self.raw_abs_max[env]) if count else None,
            "wave_sample_count": wave_count,
            "nonwave_sample_count": nonwave_count,
            "wave_prepared_mean_abs": _number(wave_mean),
            "wave_prepared_abs_max": _number(self.wave_prepared_max[env]),
            "wave_posture_error_abs_max": _number(self.wave_posture_error_max[env]),
            "nonwave_prepared_abs_max": _number(self.nonwave_prepared_max[env]) if nonwave_count else None,
            "wave_action_delta_max": _number(self.wave_delta_max[env]),
            "wave_action_delta_count": int(self.delta_count[env]),
            "height_recovery_sample_count": recovery_count,
            "height_recovery_mean_height": _number(recovery_mean_height),
            "height_recovery_abs_mean_error": _number(recovery_abs_mean_error),
            "height_recovery_mean_abs_error": _number(recovery_mae),
            "height_recovery_max_abs_error": _number(self.recovery_error_max[env]),
            "last_active_height_abs_error": _number(self.last_height_error[env]),
            "wheel_mean_angular_speed": {
                "min": [_number(value) for value in self.velocity_min[env]],
                "max": [_number(value) for value in self.velocity_max[env]],
                "mean": [_number(value) for value in velocity_mean],
                "spread": _number(velocity_spread), "count": count,
            },
            "strict_clearance": self._clearance_report("strict", env),
            "reference_radius_ordered_clearance": self._clearance_report("reference", env),
            "source_reference_flags": {
                name: {"prelift": bool(self.source_reference_flags[env, column, 0]),
                       "overbar": bool(self.source_reference_flags[env, column, 1])}
                for column, (_, name) in enumerate(_REQUIRED_WHEELS)
            },
        }

    def report(self, process_finalized=False):
        if not isinstance(process_finalized, (bool, np.bool_)):
            raise ValueError("process_finalized must be boolean")
        per_env = [self._environment_report(env) for env in range(self.num_envs)]
        passed_envs = sum(env["passed"] for env in per_env)
        completed = self.received_steps == self.requested_steps and bool(process_finalized)
        kind = "startup" if self.requested_steps == 32 else "strict" if self.requested_steps == 1600 else "diagnostic"
        return {
            "completed": completed,
            "passed": completed and self.requested_steps == 1600 and passed_envs == self.num_envs,
            "validation_kind": kind, "num_envs": self.num_envs,
            "requested_steps": self.requested_steps, "received_steps": self.received_steps,
            "process_finalized": bool(process_finalized), "passed_envs": passed_envs,
            "success_rate": passed_envs / self.num_envs, "per_env": per_env,
            "diagnostic_definitions": {
                "touchdown": (
                    "new diagnostic: strictly after passed_step and wheel x still beyond bar rear + radius, "
                    "wheel center height within "
                    "radius +/- 0.005 m and generic wheel contact force > 1 N; "
                    "this is not an original reference-controller acceptance threshold"
                ),
                "root_progress": "last active root x minus reset-time initial root x >= 1.50 m",
                "wheel_speed_spread": "max minus min of the four signed first-episode time-mean angular velocities",
                "height_recovery_mean": "gate: abs(mean(recovery height) - 0.57) <= 0.04 m; recovery uses local root x >= 1.1 m",
                "height_recovery_mean_abs_error": "diagnostic MAE: mean(abs(recovery height - 0.57)); not the mean-height acceptance gate",
                "source_reference_flags": "radius 0.095 m; independent cumulative prelift/overbar flags, without ordering",
                "reference_radius_ordered_clearance": "new ordered diagnostic using radius 0.095 m; not source-helper output",
                "numeric_comparison_atol": _ROUNDING_ATOL,
            },
        }
