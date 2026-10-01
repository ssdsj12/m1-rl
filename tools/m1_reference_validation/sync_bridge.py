"""Isolated wheel-only bridge. No simulator or torch imports before AppLauncher."""

import hashlib
import math
from pathlib import Path

import numpy as np


WHEEL_NAMES = [f"{leg}_FOOT_JOINT" for leg in ("FAR", "FBL", "RAR", "RBL")]
PARAMETERS = {
    "candidate": "post_cross_sync_v1", "dt": .02, "tau": .20,
    "alpha": 1.0 - math.exp(-.02 / .20), "ki": .5,
    "bias_bound": 1., "slew_rate": 1., "physical_velocity_limit": 20.,
    "feedforward": [1., 1., 1.4, 1.4], "ready_samples": 5,
    "wheel_radius": .0959, "bar_center": [.85, -.2], "bar_size": [.06, .16, .06],
    "clearance": .005, "force_threshold": 1., "root_x_min_exclusive": 1.15,
    "height_min": .53, "height_max": .61, "tilt_max": .45, "rounding_atol": 1e-12,
}
GATE_REASONS = {name: 1 << index for index, name in enumerate((
    "no_packet", "phase11_not_seen", "ordered_touchdown_missing", "wave_gate", "nonzero_legs",
    "wheel_not_past_bar", "wheel_height", "ground_force", "root_not_past_gate", "root_height",
    "tilt", "reference_collision", "bar_contact", "episode_ended"))}


def candidate_metadata():
    root = Path(__file__).resolve().parent
    return {"name": "post_cross_sync_v1", "parameters": PARAMETERS.copy(),
            "gate_source": "controller_oracle", "gate_reasons": GATE_REASONS.copy(), "files": {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in ("post_cross_sync.py", "sync_bridge.py", "sync_verdict.py")}}


def _array(value):
    if hasattr(value, "detach"):
        value = value.detach().clone().cpu().numpy()
    return np.array(value, copy=True)


def validate_live_contract(env, sink):
    """Check actual action units and actuator values, not only config defaults."""
    def require(condition, label):
        if not condition:
            raise ValueError(f"sync contract: {label}")

    def equal(value, expected):
        value = _array(value)
        return bool(np.all(np.isfinite(value)) and np.all(value == expected))

    cfg, robot = env.cfg, env.scene["robot"]
    require(abs(cfg.sim.dt * cfg.decimation - .02) < 1e-12, "dt")
    for key, expected in {"wave_wheel_action_signs": 1., "wave_front_wheel_action": 1.,
                          "wave_rear_wheel_action": 1., "wave_rear_wheel_velocity_feedforward": .4,
                          "wave_wheel_equalize_gain": 3., "wave_disable_obstacle_after_root_x": 1.15,
                          "wave_sync_actual_wheel_velocity": True,
                          "wave_forward_only_wheels": True}.items():
        require(equal(getattr(cfg, key), expected), key)
    manager = env.action_manager
    require(list(manager.active_terms) == ["leg_pos", "wheel_vel"] and manager.total_action_dim == 16,
            "action order/dimension")
    term = manager.get_term("wheel_vel")
    require(type(term).__name__ == "JointVelocityAction", "wheel action type")
    ids = [robot.joint_names.index(name) for name in WHEEL_NAMES]
    require(list(term._joint_names) == WHEEL_NAMES and list(term._joint_ids) == ids and
            list(sink.wheel_joint_ids) == ids, "wheel joint order")
    require(term.cfg.preserve_order and term.cfg.use_default_offset and term.cfg.clip is None,
            "action config")
    require(list(term.cfg.joint_names) == WHEEL_NAMES, "configured wheel order")
    require(equal(term.cfg.scale, 1.) and equal(term._scale, 1.), "wheel scale")
    require(equal(term.cfg.offset, 0.) and equal(term._offset, 0.), "actual wheel offset")
    require(equal(robot.data.default_joint_vel[:, ids], 0.), "default wheel velocity")
    actuator = robot.actuators["wheels"]
    require(type(actuator).__name__ == "ImplicitActuator", "wheel actuator type")
    for key, expected in (("velocity_limit_sim", 20.), ("damping", 30.), ("stiffness", 0.)):
        require(equal(getattr(actuator, key), expected), key)
    return {"wheel_scale": 1., "actual_offset": 0., "default_joint_velocity": 0.,
            "wheel_joint_names": WHEEL_NAMES, "wheel_joint_ids": ids,
            "action_columns": [12, 13, 14, 15], "dt": .02,
            "velocity_limit_sim": 20., "damping": 30., "stiffness": 0.}


class SyncBridge:
    def __init__(self, env, sink, output):
        # This constructor only runs after AppLauncher and scene construction.
        from post_cross_sync import PostCrossSync
        from post_cross_sync import PARAMETERS as core_parameters
        from post_cross_sync import GATE_REASONS as core_reasons
        from runtime import write_json
        if core_parameters != PARAMETERS or core_reasons != GATE_REASONS:
            raise ValueError("sync contract: core parameters/reasons differ from candidate metadata")
        self.env, self.sink, self.output = env, sink, Path(output)
        self.contract = validate_live_contract(env, sink)
        write_json(self.output / "sync_live_contract.json", self.contract)
        self.core = PostCrossSync(num_envs=env.num_envs)
        self.pending = None
        self.chunks = []

    def prepare(self, wrapped, raw, original):
        if np.any(_array(raw) != 0):
            raise ValueError("sync contract: raw policy residual must be zero")
        if self.pending is not None:
            raise ValueError("sync packet missing before next prepare")
        env, robot = self.env, self.env.scene["robot"]
        current = {"wheel_velocity": _array(robot.data.joint_vel[:, self.sink.wheel_joint_ids]),
                   "root_pos": _array(robot.data.root_pos_w) - _array(env.scene.env_origins),
                   "wave_gate": _array(env.m1_wave_gate),
                   "drive_allowed": _array(wrapped._sequential_drive_allowed),
                   "episode_length": _array(env.episode_length_buf)}
        step = self.sink.expected_step
        final, diagnostics = self.core.prepare(step, original, current)
        self.pending = {key: _array(value) for key, value in diagnostics.items()}
        self.pending.update({"step": np.asarray(step), "env_id": np.arange(env.num_envs),
                             "episode_length": current["episode_length"],
                             "current_root_pos": current["root_pos"],
                             "current_wave_gate": current["wave_gate"],
                             "current_drive_allowed": current["drive_allowed"]})
        return final

    def sample(self, step, compact):
        if self.pending is None or int(self.pending["step"]) != step:
            raise ValueError("sync pre-reset sample identity mismatch")
        actual = _array(compact["applied_actions"])
        processed = _array(self.env.action_manager.get_term("wheel_vel").processed_actions)
        if not np.array_equal(actual, self.pending["final_actions"]):
            raise ValueError("sync actual action-manager actions differ from final")
        if not np.array_equal(processed, self.pending["final_actions"][:, 12:16]):
            raise ValueError("sync processed wheel targets differ from final rad/s")
        packet = {key: _array(value) for key, value in compact.items()}
        packet.update({"episode_id": _array(self.core.episode_id), "env_id": np.arange(self.env.num_envs)})
        self.core.observe(step, packet)
        self.pending.update({"actual_actions": actual, "processed_wheel_targets": processed})
        self.chunks.append(self.pending)
        self.pending = None
        if len(self.chunks) == 32:
            self.flush()

    def on_reset(self, env_ids):
        if self.pending is not None:
            raise ValueError("sync reset before pre-reset packet was observed")
        self.core.reset(env_ids)

    def flush(self):
        if self.chunks:
            stacked = {key: np.stack([row[key] for row in self.chunks]) for key in self.chunks[0]}
            name = f"sync_{int(stacked['step'][0]):04d}_{int(stacked['step'][-1]):04d}.npz"
            np.savez_compressed(self.output / name, **stacked)
            self.chunks.clear()


def make_sync_wrapper(measured_type):
    class PostCrossWrapper(measured_type):
        def __init__(self, *args, **kwargs):
            self._sync_bridge = None
            super().__init__(*args, **kwargs)

        def bind_post_cross(self, output, sink):
            if self._sync_bridge is not None:
                raise ValueError("sync observer already bound")
            self._sync_bridge = SyncBridge(self.env.unwrapped, sink, output)
            sink.sync_observer = self._sync_bridge

        def _prepare_actions(self, raw):
            original = super()._prepare_actions(raw)
            if self._sync_bridge is None:
                return original
            return self._sync_bridge.prepare(self, raw, original)

        def step(self, raw):
            bridge = self._sync_bridge
            before = bridge.core.episode_id.clone() if bridge is not None else None
            result = super().step(raw)
            if bridge is not None:
                done = _array(result[2]).astype(bool)
                unchanged = _array(bridge.core.episode_id == before)
                ids = np.flatnonzero(done & unchanged).tolist()
                if ids:
                    bridge.on_reset(ids)
            return result

        def reset(self):
            bridge = self._sync_bridge
            before = bridge.core.episode_id.clone() if bridge is not None else None
            result = super().reset()
            if bridge is not None:
                ids = np.flatnonzero(_array(bridge.core.episode_id == before)).tolist()
                if ids:
                    bridge.on_reset(ids)
            return result

    return PostCrossWrapper
