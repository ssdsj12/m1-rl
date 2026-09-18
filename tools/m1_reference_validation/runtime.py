"""Isolated reference-run measurement helpers; importing this module starts no simulator."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

import numpy as np


REFERENCE = "/home/hexinkun/m1/Go2Pvcnn"
AMP_PYTHON = "/home/hexinkun/miniconda3/envs/amp/bin/python"
ISAAC_SOURCE = "/home/hexinkun/IsaacLab45/source/isaaclab"
CONTACT_BODY_NAMES = ("BASE_LINK",) + tuple(
    f"{leg}_{part}_LINK" for leg in ("FAR", "FBL", "RAR", "RBL")
    for part in ("ABAD", "HIP", "KNEE", "FOOT")
)
WHEEL_NAMES = tuple(f"{leg}_FOOT_LINK" for leg in ("FAR", "FBL", "RAR", "RBL"))
WHEEL_CONTACT_IDS = (4, 8, 12, 16)
NONWHEEL_CONTACT_IDS = tuple(index for index in range(17) if index not in WHEEL_CONTACT_IDS)
REQUIRED_MODULES = (
    "go2_pvcnn.tasks.m1_pvcnn_small_obstacle_env_cfg", "go2_pvcnn.tasks.m1_rsl_rl_wrapper",
    "go2_pvcnn.tasks.m1_curriculum", "go2_pvcnn.assets", "extension.semantic_course",
    "extension.mdp.observations", "rsl_rl.env",
)
_ALLOWED_CFG = {
    "scene.num_envs", "sim.device", "scene.robot.spawn.usd_path",
    "scene.terrain.terrain_generator.num_rows", "scene.terrain.terrain_generator.num_cols",
    "scene.terrain.terrain_generator.size", "scene.terrain.max_init_terrain_level",
    "terminations.crossing_success", "episode_length_s", "recorders", "scene.diagnostic_bar_contacts",
}
SCANNER_BBOX_ATOL = 2e-5


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Independent M1 reference-controller validation")
    parser.add_argument("--num-envs", type=int, choices=(8, 1024), required=True)
    parser.add_argument("--steps", type=int, choices=(32, 1600), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", choices=(REFERENCE,), default=REFERENCE)
    parser.add_argument("--device", choices=("cuda:4",), default="cuda:4")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--kit_args", default="--/renderer/multiGpu/enabled=false --/renderer/multiGpu/autoEnable=false")
    return parser.parse_args(argv)


def create_output(path):
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=False)
    return path


def interpreter_evidence(executable, version):
    actual = Path(executable).resolve()
    expected = Path(AMP_PYTHON).resolve()
    if actual != expected:
        raise ValueError(f"Expected amp interpreter {expected}, got {actual}")
    return {"sys_executable": str(executable), "sys_executable_resolved": str(actual),
            "python_version": str(version), "expected_amp_executable_resolved": str(expected)}


def jsonable(value):
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if callable(value):
        return f"{value.__module__}.{value.__qualname__}"
    if hasattr(value, "to_dict"):
        return jsonable(value.to_dict())
    return str(value)


def write_json(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(jsonable(data), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_source_bindings(reference, modules=None, required=()):
    modules = sys.modules if modules is None else modules
    root = Path(reference).resolve()
    result = {}
    for name in required:
        if name not in modules or not getattr(modules[name], "__file__", None):
            raise ValueError(f"Required source module is not loaded: {name}")
    for name, module in list(modules.items()):
        if not (name.split(".")[0] in {"go2_pvcnn", "extension", "rsl_rl", "agent"}
                or name.startswith("isaaclab.managers")):
            continue
        filename = getattr(module, "__file__", None)
        if filename is None:
            continue
        path = Path(filename).resolve()
        expected = Path(ISAAC_SOURCE).resolve() if name.startswith("isaaclab.managers") else root
        if not path.is_relative_to(expected):
            raise ValueError(f"Module {name} is outside reference/source boundary: {path}")
        result[name] = {"path": str(path), "sha256": file_hash(path)}
    return result


def validate_cfg_diff(before, after):
    changes = []
    def compare(left, right, prefix):
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(left.keys() | right.keys()):
                name = f"{prefix}.{key}" if prefix else key
                if key not in left or key not in right:
                    changes.append(name)
                else:
                    compare(left[key], right[key], name)
        elif left != right:
            changes.append(prefix)
    compare(jsonable(before), jsonable(after), "")
    forbidden = [path for path in changes if not any(path == allowed or path.startswith(allowed + ".") for allowed in _ALLOWED_CFG)]
    if forbidden:
        raise ValueError(f"Unauthorized configuration changes: {forbidden}")
    return changes


def validate_acceptance_cfg(cfg):
    frozen = {
        "acceptance_max_tilt_rad": 0.45, "wave_max_action_delta_acceptance": 2.0,
        "acceptance_min_front_wheel_height_m": 0.13, "acceptance_min_rear_wheel_height_m": 0.14,
        "base_height_target": 0.57, "base_height_recovery_start_x": 1.1,
        "base_height_recovery_tolerance": 0.04, "acceptance_clearance_contact_force_limit_n": 1.0,
        "acceptance_wheel_radius_m": 0.095, "acceptance_wheel_clearance_margin_m": 0.005,
    }
    for name, expected in frozen.items():
        if not hasattr(cfg, name) or not np.isclose(float(getattr(cfg, name)), expected, atol=1e-12, rtol=0):
            raise ValueError(f"Reference acceptance configuration mismatch: {name}")
    if cfg.seed != 20260711 or cfg.decimation != 4:
        raise ValueError("Reference seed/decimation changed")
    if not cfg.wave_task_space_ik or not cfg.wave_sequential_crossing_reference or cfg.wave_reference_actions:
        raise ValueError("Reference controller ownership flags changed")
    return frozen


def adapt_cfg(cfg, num_envs, steps, overlay, sensor_cfg, recorder_cfg):
    before = jsonable(cfg.to_dict())
    validate_acceptance_cfg(cfg)
    cfg.scene.num_envs = num_envs
    cfg.sim.device = "cuda:4"
    cfg.scene.robot.spawn.usd_path = str(overlay)
    generator = cfg.scene.terrain.terrain_generator
    generator.num_rows, generator.num_cols, generator.size = 1, num_envs, (8.0, 8.0)
    cfg.scene.terrain.max_init_terrain_level = 0
    cfg.terminations.crossing_success = None
    cfg.episode_length_s = max(cfg.episode_length_s, (steps + 1) * cfg.sim.dt * cfg.decimation)
    cfg.scene.diagnostic_bar_contacts = sensor_cfg
    cfg.recorders = recorder_cfg
    after = jsonable(cfg.to_dict())
    changes = validate_cfg_diff(before, after)
    return before, after, changes


def own_bar_indices(paths, num_envs):
    mapping = {}
    for index, path in enumerate(paths):
        match = re.search(r"/row_(\d+)/col_(\d+)/slot_(\d+)$", str(path))
        if not match or int(match[1]) != 0 or int(match[3]) != 0:
            raise ValueError(f"Unexpected bar filter path: {path}")
        column = int(match[2])
        if column in mapping:
            raise ValueError("Duplicate own-bar column")
        mapping[column] = index
    if set(mapping) != set(range(num_envs)) or len(paths) != num_envs:
        raise ValueError("Missing or extra own-bar mapping")
    return np.array([mapping[index] for index in range(num_envs)], dtype=np.int64)


def sensor_rows(paths, body_names, num_envs):
    names = tuple(body_names)
    if len(paths) != num_envs * len(names):
        raise ValueError("Sensor body path count mismatch")
    rows = {}
    for row in range(num_envs):
        group = list(map(str, paths[row * len(names):(row + 1) * len(names)]))
        matches = [re.search(r"/env_(\d+)/Robot/([^/]+)$", path) for path in group]
        if any(match is None for match in matches):
            raise ValueError("Unrecognized sensor body path")
        env_ids = {int(match[1]) for match in matches}
        if len(env_ids) != 1 or tuple(match[2] for match in matches) != names:
            raise ValueError("Sensor body order/identity mismatch")
        env_id = env_ids.pop()
        if env_id in rows:
            raise ValueError("Duplicate sensor environment body group")
        rows[env_id] = row
    if set(rows) != set(range(num_envs)):
        raise ValueError("Missing sensor environment body group")
    return np.array([rows[index] for index in range(num_envs)], dtype=np.int64)


def validate_contact_view_paths(actual_sensors, actual_filters, expected_sensors, expected_filters):
    if list(map(str, actual_sensors)) != list(map(str, expected_sensors)):
        raise ValueError("Actual PhysX contact sensor path order mismatch")
    filters = list(actual_filters)
    expected = list(map(str, expected_filters))
    if filters and isinstance(filters[0], str):
        if filters == expected:
            form = "shared_flat"
        elif len(filters) == len(expected_sensors) * len(expected) and all(
            filters[start:start + len(expected)] == expected for start in range(0, len(filters), len(expected))
        ):
            form = "repeated_flat"
        else:
            raise ValueError("Actual PhysX contact filter path order mismatch")
    elif len(filters) == len(expected_sensors) and all(list(map(str, row)) == expected for row in filters):
        form = "per_sensor_nested"
    else:
        raise ValueError("Unknown/mismatched actual PhysX contact filter paths")
    return {"sensor_count": len(expected_sensors), "filter_count": len(expected), "actual_filter_path_layout": form,
            "filter_order_sha256": hashlib.sha256(json.dumps(expected).encode()).hexdigest()}


def reduce_bar_forces(matrix, own_indices, row_for_env):
    values = np.asarray(matrix)
    n = len(own_indices)
    if values.shape != (n, 17, n, 3) or not np.all(np.isfinite(values)):
        raise ValueError("Invalid diagnostic force matrix")
    norms = np.linalg.norm(values[row_for_env], axis=-1)
    own = norms[np.arange(n), :, own_indices].copy()
    norms[np.arange(n), :, own_indices] = 0.0
    return own, norms.max(axis=(1, 2))


class SubstepAccumulator:
    def __init__(self, num_envs, decimation):
        self.num_envs, self.decimation = num_envs, decimation
        self.armed = False

    def arm(self, step):
        if self.armed:
            raise ValueError("Previous substep evidence was not consumed")
        self.step, self.armed = step, True
        self.counts = np.zeros(self.num_envs, dtype=np.int64)
        self.own_peak = np.zeros((self.num_envs, 17))
        self.foreign_peak = np.zeros(self.num_envs)

    def record(self, own, foreign):
        if not self.armed:
            raise ValueError("Physical substep sample without arm")
        own, foreign = np.asarray(own), np.asarray(foreign)
        if own.shape != (self.num_envs, 17) or foreign.shape != (self.num_envs,):
            raise ValueError("Partial substep sample")
        if not np.all(np.isfinite(own)) or not np.all(np.isfinite(foreign)):
            raise ValueError("Non-finite substep force sample")
        self.own_peak = np.maximum(self.own_peak, own)
        self.foreign_peak = np.maximum(self.foreign_peak, foreign)
        self.counts += 1

    def consume(self):
        if not self.armed or not np.all(self.counts == self.decimation):
            raise ValueError("Missing/extra physical substep samples")
        self.armed = False
        return self.own_peak.copy(), self.foreign_peak.copy(), self.counts.copy()


class RecorderBridge:
    def __init__(self, sink_supplier):
        self.sink_supplier = sink_supplier

    def pre_step(self, env):
        sink = self.sink_supplier()
        if sink is None or sink.expected_step is None:
            raise RuntimeError("Recorder is not armed with a validation step")
        env.scene["diagnostic_bar_contacts"].accumulator.arm(sink.expected_step)
        return None, None

    def post_step(self, env):
        sink = self.sink_supplier()
        if sink is None:
            raise RuntimeError("Recorder post-step without sink")
        peaks = env.scene["diagnostic_bar_contacts"].accumulator.consume()
        sink.sample(env, peaks)
        return None, None


def step_once(wrapped, sink, step, zeros, is_running):
    if not is_running():
        raise RuntimeError(f"Simulation stopped prematurely before step {step}")
    if wrapped.num_actions != 16 or tuple(zeros.shape) != (wrapped.num_envs, 16):
        raise ValueError("Reference wrapper requires exactly 16 raw actions")
    sink.expected_step = step
    before = sink.received_steps
    wrapped.step(zeros)
    if sink.received_steps != before + 1:
        raise RuntimeError("Expected exactly one pre-reset recorder sample per wrapper step")


def scanner_ownership_bounds(own_bboxes):
    """Include source scanner float32 world-vertex quantization, not physics slack."""
    boxes = np.asarray(own_bboxes, dtype=np.float64)
    if boxes.ndim != 3 or boxes.shape[1:] != (2, 3) or not np.all(np.isfinite(boxes)):
        raise ValueError("Invalid scanner own-bar bounding boxes")
    quantized = boxes.astype(np.float32).astype(np.float64)
    if not np.all(np.isfinite(quantized)) or np.any(boxes[:, 0] > boxes[:, 1]):
        raise ValueError("Invalid scanner float32 world bounds")
    return np.stack((np.minimum(boxes[:, 0], quantized[:, 0]) - SCANNER_BBOX_ATOL,
                     np.maximum(boxes[:, 1], quantized[:, 1]) + SCANNER_BBOX_ATOL), axis=1)


def check_scanner_hits(semantic_map, ray_hits, own_bboxes):
    n = len(own_bboxes)
    semantic = np.asarray(semantic_map).reshape(n, -1)
    hits = np.asarray(ray_hits)
    if hits.shape != (n, semantic.shape[1], 3):
        raise ValueError("Scanner semantic/ray-hit shape mismatch")
    small = semantic == 1
    finite = np.all(np.isfinite(hits), axis=-1)
    ownership_bounds = scanner_ownership_bounds(own_bboxes)
    inside = np.all((hits >= ownership_bounds[:, None, 0])
                    & (hits <= ownership_bounds[:, None, 1]), axis=-1)
    return {"own_counts": np.sum(small & finite & inside, axis=1),
            "foreign_counts": np.sum(small & finite & ~inside, axis=1),
            "invalid_counts": np.sum(small & ~finite, axis=1)}


def write_cleanup_marker(output, run_id, pid, steps):
    output = Path(output)
    write_json(output / "POST_CLEANUP.json", {
        "run_id": run_id, "pid": pid, "steps": steps,
        "candidate_sha256": file_hash(output / "candidate_report.json"),
    })


def cleanup_run(output, start, candidate, sink, env, simulation_app, restore_ik, exit_code,
                writer=write_json, marker_writer=write_cleanup_marker, emit=print):
    """Attempt every cleanup independently, even when report persistence fails."""
    output = Path(output)
    failures = []
    received = sink.received_steps if sink is not None else 0

    def attempt(label, operation):
        try:
            operation()
            return True
        except BaseException as error:
            failures.append(f"{label}: {type(error).__name__}: {error}")
            try:
                emit("M1_REFERENCE_CLEANUP_ERROR", failures[-1], flush=True)
            except BaseException:
                pass
            return False

    attempt("candidate report write", lambda: writer(output / "candidate_report.json", candidate))
    attempt("cleanup status write", lambda: writer(output / "status.json", {
        **start, "status": "cleanup_pending", "received_steps": received}))
    attempt("cleanup begin log", lambda: emit("M1_REFERENCE_CLEANUP_BEGIN", flush=True))
    if env is not None:
        if attempt("environment close", env.close):
            attempt("environment close log", lambda: emit("M1_REFERENCE_ENV_CLOSED", flush=True))
    if restore_ik is not None:
        attempt("restore original IK binding", restore_ik)
    if simulation_app is not None:
        if attempt("application close", simulation_app.close):
            attempt("application close log", lambda: emit("M1_REFERENCE_APP_CLOSED", flush=True))
    if not failures and simulation_app is not None:
        attempt("post-cleanup status write", lambda: writer(output / "status.json", {
            **start, "status": "post_cleanup_waiting_native_exit", "received_steps": received}))
        if not failures:
            attempt("post-cleanup marker write", lambda: marker_writer(output, start["run_id"], start["pid"], received))
        if not failures:
            attempt("post-cleanup marker log", lambda: emit("POST_CLEANUP", flush=True))
    return 1 if failures else exit_code


def finalize(output, native_exit_code):
    output = Path(output)
    errors = []
    candidate, start, marker = {}, {}, {}
    for filename, destination in (("run_start.json", start), ("candidate_report.json", candidate), ("POST_CLEANUP.json", marker)):
        try:
            value = json.loads((output / filename).read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("expected JSON object")
            destination.update(value)
        except (OSError, ValueError) as error:
            errors.append(f"{filename}: {error}")
    metrics = candidate.get("metrics", {})
    records = metrics.get("per_env", [])
    n, steps = start.get("num_envs"), start.get("requested_steps")
    if native_exit_code != 0:
        errors.append(f"native simulation exit code {native_exit_code}")
    if n not in (8, 1024) or steps not in (32, 1600):
        errors.append("invalid requested budget")
    if metrics.get("received_steps") != steps or metrics.get("requested_steps") != steps or metrics.get("num_envs") != n:
        errors.append("candidate budget mismatch")
    if not isinstance(records, list) or len(records) != n or [item.get("env_id") for item in records] != list(range(n or 0)):
        errors.append("missing/duplicate per-environment records")
    if any(not isinstance(row.get("active_sample_count"), int)
           or not 0 < row["active_sample_count"] <= (steps or 0) for row in records):
        errors.append("missing/invalid first-episode samples")
    if not marker or marker.get("run_id") != start.get("run_id") or candidate.get("run_id") != start.get("run_id"):
        errors.append("run identity/cleanup marker mismatch")
    if marker.get("pid") != start.get("pid") or marker.get("steps") != steps:
        errors.append("cleanup PID/budget mismatch")
    if marker:
        try:
            if marker.get("candidate_sha256") != file_hash(output / "candidate_report.json"):
                errors.append("post-cleanup candidate hash mismatch")
        except OSError:
            errors.append("missing hashed candidate")
    completed = not errors
    scanner = candidate.get("scanner", {})
    common = (candidate.get("scene", {}).get("valid") is True
              and scanner.get("valid") is True and candidate.get("source_bindings_valid") is True
              and candidate.get("measurement_issues") == [])
    startup_ok = completed and common and all(
        row.get("active_sample_count") == steps and row.get("reset_count") == 0
        and row.get("first_failure_step") is None for row in records
    )
    strict_ok = completed and common and steps == 1600 and scanner.get("seen_by_env") == [True] * n and all(
        bool(row.get("flags")) and all(value is True for value in row["flags"].values())
        and row.get("active_sample_count") == steps for row in records
    )
    report = {**candidate, "completed": completed, "passed": bool(strict_ok),
              "metrics": {**metrics, "completed": completed, "passed": bool(strict_ok), "process_finalized": completed},
              "candidate_process_finalized": False,
              "startup_passed": bool(startup_ok) if steps == 32 else False,
              "validation_kind": "startup" if steps == 32 else "strict",
              "native_exit_code": native_exit_code, "finalization_errors": errors}
    code = 2 if not completed else 0 if (strict_ok or (steps == 32 and startup_ok)) else 3
    report["wrapper_return_code"] = code
    write_json(output / "report.json", report)
    return report, code


def snapshot_array(value, name, shape=None):
    """Own the snapshot before the environment/wrapper can reset storage in-place."""
    if hasattr(value, "detach"):
        value = value.detach().clone().cpu().numpy()
    array = np.array(value, copy=True)
    if shape is not None and array.shape != shape:
        raise ValueError(f"{name} shape {array.shape}, expected {shape}")
    if array.dtype.kind not in "biuf" or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite/non-numeric state")
    return array


def make_diagnostic_cfgs(filter_expressions, sink_holder, decimation=4):
    """Import only after AppLauncher; the recorder constructor touches no managers."""
    import torch
    from isaaclab.managers import RecorderTerm, RecorderTermCfg, RecorderManagerBaseCfg, DatasetExportMode
    from isaaclab.sensors import ContactSensorCfg
    from isaaclab.utils import configclass
    from go2_pvcnn.sensor.semantic_contacter.semantic_global_contact_sensor import M1SemanticGlobalContactSensor

    class DiagnosticBarSensor(M1SemanticGlobalContactSensor):
        CONTACT_BODY_NAMES = CONTACT_BODY_NAMES

        def _initialize_impl(self):
            super()._initialize_impl()
            actual_paths = list(self._body_physx_view.prim_paths)
            if actual_paths != self._sensor_paths:
                raise ValueError("PhysX body view does not preserve requested diagnostic sensor paths")
            self.row_for_env = sensor_rows(actual_paths, self.body_names, self._num_envs)
            self.own_indices = own_bar_indices(self.semantic_filter_paths, self._num_envs)
            self._verified_filter_paths = tuple(self.semantic_filter_paths)
            self.contact_path_evidence = validate_contact_view_paths(
                self.contact_physx_view.sensor_paths, self.contact_physx_view.filter_paths,
                self._sensor_paths, self.semantic_filter_paths,
            )
            self._row_index = torch.tensor(self.row_for_env, dtype=torch.long, device=self._device)
            self._own_index = torch.tensor(self.own_indices, dtype=torch.long, device=self._device)
            self._env_index = torch.arange(self._num_envs, device=self._device)
            self.accumulator = SubstepAccumulator(self._num_envs, decimation)
            self._physical_update = False
            self.sample_seconds = 0.0
            self.physical_update_count = 0

        def update(self, dt, force_recompute=False):
            started = time.perf_counter()
            self._physical_update = bool(dt > 0 and hasattr(self, "accumulator") and self.accumulator.armed)
            try:
                # InteractiveScene calls this exactly once after each physics substep.
                # .data access can refresh buffers but never arms this physics-only flag.
                super().update(dt, force_recompute=True)
            finally:
                if self._physical_update:
                    self.sample_seconds += time.perf_counter() - started
                self._physical_update = False

        def _update_buffers_impl(self, env_ids):
            super()._update_buffers_impl(env_ids)
            if not getattr(self, "_physical_update", False):
                return
            if len(env_ids) != self._num_envs:
                raise ValueError("Partial diagnostic sensor substep update")
            if tuple(self.semantic_filter_paths) != self._verified_filter_paths:
                raise ValueError("Diagnostic bar filter mapping changed during run")
            matrix = self._data.force_matrix_w
            if tuple(matrix.shape) != (self._num_envs, 17, self._num_envs, 3):
                raise ValueError(f"Diagnostic force matrix shape mismatch: {tuple(matrix.shape)}")
            norms = torch.linalg.vector_norm(matrix, dim=-1).index_select(0, self._row_index)
            own = norms[self._env_index, :, self._own_index].clone()
            norms[self._env_index, :, self._own_index] = 0.0
            foreign = norms.amax(dim=(1, 2))
            self.accumulator.record(snapshot_array(own, "own bar forces"), snapshot_array(foreign, "foreign bar forces"))
            self.physical_update_count += 1

    bridge = RecorderBridge(lambda: sink_holder.get("sink"))

    class DiagnosticRecorder(RecorderTerm):
        def record_pre_step(self):
            return bridge.pre_step(self._env)

        def record_post_step(self):
            return bridge.post_step(self._env)

        def record_pre_reset(self, env_ids):
            return None, None

        def record_post_reset(self, env_ids):
            return None, None

    @configclass
    class DiagnosticRecorderCfg(RecorderManagerBaseCfg):
        dataset_export_mode = DatasetExportMode.EXPORT_NONE
        export_in_record_pre_reset = False
        diagnostic = RecorderTermCfg(class_type=DiagnosticRecorder)

    sensor_cfg = ContactSensorCfg(
        class_type=DiagnosticBarSensor, prim_path="{ENV_REGEX_NS}/Robot/.*",
        update_period=0.0, history_length=0, track_pose=False, track_air_time=False,
        track_contact_points=False, debug_vis=False, filter_prim_paths_expr=list(filter_expressions),
    )
    return sensor_cfg, DiagnosticRecorderCfg()


def instrument_reference_wrapper(wrapper_class, wrapper_module, counters):
    """Count original calls without changing inputs, outputs, or control branches."""
    original_ik = wrapper_module.build_stabilized_task_space_wheel_actions
    def counted_ik(*args, **kwargs):
        counters["ik_calls"] += 1
        return original_ik(*args, **kwargs)
    wrapper_module.build_stabilized_task_space_wheel_actions = counted_ik

    class MeasuredWrapper(wrapper_class):
        def _prepare_actions(self, actions):
            counters["prepare_calls"] += 1
            return super()._prepare_actions(actions)

    return MeasuredWrapper, lambda: setattr(wrapper_module, "build_stabilized_task_space_wheel_actions", original_ik)


def ground_surface_evidence(stage, root_path="/World/ground"):
    """Measure referenced terrain triangles in world space; unused points are not faces."""
    from pxr import Usd, UsdGeom

    root = stage.GetPrimAtPath(root_path)
    if not root.IsValid():
        raise ValueError(f"Missing ground primitive {root_path}")
    transforms = UsdGeom.XformCache(Usd.TimeCode.Default())
    meshes = []
    for prim in Usd.PrimRange(root):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(prim)
        points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
        counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get())
        indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get())
        holes = mesh.GetHoleIndicesAttr().Get()
        label = str(prim.GetPath())
        if holes is not None and len(holes):
            raise ValueError(f"Ground mesh has authored holes: {label}")
        if points.ndim != 2 or points.shape[1] != 3 or not np.all(np.isfinite(points)):
            raise ValueError(f"Invalid/non-finite ground points: {label}")
        if (counts.ndim != 1 or not len(counts) or not np.all(counts == 3)
                or indices.ndim != 1 or indices.size != int(counts.sum())
                or not np.issubdtype(indices.dtype, np.integer)
                or np.any(indices < 0) or np.any(indices >= len(points))):
            raise ValueError(f"Ground must have valid referenced triangle faces: {label}")
        matrix = np.asarray(transforms.GetLocalToWorldTransform(prim), dtype=np.float64)
        if not np.all(np.isfinite(matrix)):
            raise ValueError(f"Non-finite ground world transform: {label}")
        referenced = np.unique(indices)
        world = np.column_stack((points, np.ones(len(points)))) @ matrix
        triangles = world[indices.reshape(-1, 3), :3]
        xy = triangles[:, :, :2]
        edge1, edge2 = xy[:, 1] - xy[:, 0], xy[:, 2] - xy[:, 0]
        twice_area = edge1[:, 0] * edge2[:, 1] - edge1[:, 1] * edge2[:, 0]
        if not np.all(np.isfinite(world)) or np.any(np.abs(twice_area) <= 1e-12):
            raise ValueError(f"Non-finite or degenerate ground triangle: {label}")
        z = world[referenced, 2]
        meshes.append({"path": label, "face_count": len(counts), "vertex_count": len(points),
                       "referenced_vertex_count": len(referenced),
                       "unreferenced_vertex_count": len(points) - len(referenced),
                       "surface_z_min_m": float(z.min()), "surface_z_max_m": float(z.max())})
    if not meshes:
        raise ValueError("Ground has no descendant Mesh surfaces")
    low = min(mesh["surface_z_min_m"] for mesh in meshes)
    high = max(mesh["surface_z_max_m"] for mesh in meshes)
    if high - low > 1e-5:
        raise ValueError(f"Ground referenced surface is not horizontal/planar: z=[{low}, {high}]")
    return {"method": "world_transformed_face_referenced_triangle_vertices",
            "surface_height_m": (low + high) / 2, "surface_z_min_m": low, "surface_z_max_m": high,
            "planarity_atol_m": 1e-5, "authored_holes_allowed": False, "meshes": meshes}


def validate_scene(env, output):
    from pxr import Usd, UsdGeom
    from isaaclab.sim import utils as sim_utils
    from extension.semantic_course import DEFAULT_GROUNDING_EMBED_DEPTH_M

    n = env.num_envs
    robot, sensor = env.scene["robot"], env.scene["diagnostic_bar_contacts"]
    origins = snapshot_array(env.scene.env_origins, "env origins", (n, 3))
    if len(np.unique(origins, axis=0)) != n:
        raise ValueError("Environment origins are not unique")
    distance = np.linalg.norm(origins[:, None, :2] - origins[None, :, :2], axis=-1)
    np.fill_diagonal(distance, np.inf)
    minimum_spacing = float(distance.min())
    if minimum_spacing < 8.0 - 1e-5:
        raise ValueError(f"Environment spacing is below 8 m: {minimum_spacing}")
    if robot.is_fixed_base or len(robot.body_names) != 17 or len(robot.joint_names) != 16:
        raise ValueError("Expected floating 17-body/16-joint M1")
    if set(robot.body_names) != set(CONTACT_BODY_NAMES):
        raise ValueError("Robot body identity differs from diagnostic body contract")
    root_paths = list(robot.root_physx_view.prim_paths)
    root_ids = []
    for path in root_paths:
        match = re.search(r"/env_(\d+)/Robot(?:/|$)", str(path))
        if match is None:
            raise ValueError(f"Unrecognized articulation root path: {path}")
        root_ids.append(int(match[1]))
    if root_ids != list(range(n)):
        raise ValueError("Articulation/root-state order does not match environment-origin order")
    body_ids = [robot.body_names.index(name) for name in CONTACT_BODY_NAMES]
    body_positions = snapshot_array(robot.data.body_pos_w[:, body_ids], "articulation body poses", (n, 17, 3))
    sensor_poses = snapshot_array(sensor._body_physx_view.get_transforms(), "diagnostic PhysX poses").reshape(n, 17, 7)
    position_error = float(np.max(np.abs(sensor_poses[sensor.row_for_env, :, :3] - body_positions)))
    if position_error > 1e-4:
        raise ValueError(f"Diagnostic body view/robot body pose mismatch: {position_error}")
    generic = env.scene["contact_forces"]
    generic_paths = list(generic._body_physx_view.prim_paths)
    generic_rows = sensor_rows(generic_paths, generic.body_names, n)

    stage = sim_utils.get_current_stage()
    up_axis, units = str(UsdGeom.GetStageUpAxis(stage)), float(UsdGeom.GetStageMetersPerUnit(stage))
    if up_axis != "Z" or not np.isclose(units, 1.0):
        raise ValueError("Scene must use Z-up and metersPerUnit=1")
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy])
    def bounds(path):
        prim = stage.GetPrimAtPath(path)
        if not prim.IsValid():
            raise ValueError(f"Missing scene primitive {path}")
        extent = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        result = np.asarray([tuple(extent.GetMin()), tuple(extent.GetMax())], dtype=np.float64)
        if not np.all(np.isfinite(result)):
            raise ValueError(f"Non-finite scene bound: {path}")
        return result
    ground = bounds("/World/ground")
    ground_surface = ground_surface_evidence(stage)
    ground_z = ground_surface["surface_height_m"]
    paths = sensor.semantic_filter_paths
    bboxes = np.stack([bounds(paths[index]) for index in sensor.own_indices])
    centers = bboxes.mean(axis=1)
    dimensions = bboxes[:, 1] - bboxes[:, 0]
    write_json(Path(output) / "scene_geometry_measurements.json", {
        "bar_world_bboxes": bboxes, "actual_ground_height_m": ground_z,
        "ground_world_bbox_diagnostic_only": ground, "ground_surface_evidence": ground_surface,
        "dimensions": dimensions, "local_centers_xy": centers[:, :2] - origins[:, :2],
        "actual_exposed_bar_height_m": bboxes[:, 1, 2] - ground_z,
    })
    if not np.allclose(dimensions, [0.06, 0.16, 0.06], atol=2e-5, rtol=0):
        raise ValueError("Actual crossbar bounding-box dimensions differ from nominal cuboid")
    if not np.allclose(centers[:, :2] - origins[:, :2], [0.85, -0.2], atol=2e-5, rtol=0):
        raise ValueError("Actual own-bar position does not match local (.85,-.2)")
    if float(DEFAULT_GROUNDING_EMBED_DEPTH_M) != 0.015:
        raise ValueError("Reference grounding embed depth changed")
    manifest = {
        "valid": True, "num_envs": n, "env_origins": origins,
        "min_environment_spacing_m": minimum_spacing, "bar_paths": [paths[index] for index in sensor.own_indices],
        "own_filter_indices": sensor.own_indices, "sensor_row_for_env": sensor.row_for_env,
        "actual_contact_view_path_evidence": sensor.contact_path_evidence,
        "generic_sensor_row_for_env": generic_rows, "sensor_body_names": sensor.body_names,
        "sensor_paths": sensor._sensor_paths, "articulation_paths": root_paths,
        "robot_body_names": robot.body_names, "robot_joint_names": robot.joint_names,
        "body_view_position_error_m": position_error, "stage_up_axis": up_axis, "meters_per_unit": units,
        "nominal_bar_size_m": [0.06, 0.16, 0.06], "bar_world_bboxes": bboxes,
        "actual_ground_height_m": ground_z, "source_grounding_embed_depth_m": 0.015,
        "ground_world_bbox_diagnostic_only": ground, "ground_surface_evidence": ground_surface,
        "bar_bottom_m": bboxes[:, 0, 2], "bar_top_m": bboxes[:, 1, 2],
        "actual_exposed_bar_height_m": bboxes[:, 1, 2] - ground_z,
        "nominal_60mm_is_not_exposed_60mm": not bool(np.allclose(bboxes[:, 1, 2] - ground_z, 0.06, atol=2e-5, rtol=0)),
        "strict_clearance_center_height_m": 0.1609,
        "scanner_bbox_atol_m": SCANNER_BBOX_ATOL,
        "scanner_ownership_bound_policy": "union_actual_bbox_and_float32_world_quantized_bbox_plus_base_atol",
        "scanner_world_vertex_dtype": "float32",
        "scanner_ownership_world_bounds": scanner_ownership_bounds(bboxes),
        "scanner_max_float32_boundary_shift_m": float(np.max(np.abs(bboxes.astype(np.float32).astype(np.float64) - bboxes))),
        "diagnostic_force_matrix_bytes": n * 17 * n * 3 * 4,
    }
    write_json(Path(output) / "scene_manifest.json", manifest)
    return jsonable(manifest), bboxes, generic_rows


class RuntimeSink:
    def __init__(self, env, steps, output, bboxes, generic_rows, counters):
        from metrics import FirstEpisodeMetrics
        from go2_pvcnn.assets import M1_LEG_JOINT_NAMES, M1_WHEEL_JOINT_NAMES
        self.env, self.output, self.bboxes = env, Path(output), bboxes
        self.generic_rows, self.counters = generic_rows, counters
        self.expected_step = None
        self.num_envs = env.num_envs
        self.robot = env.scene["robot"]
        n = self.num_envs
        self.origins = snapshot_array(env.scene.env_origins, "origins", (n, 3))
        initial_root = snapshot_array(self.robot.data.root_pos_w, "initial root", (n, 3)) - self.origins
        self.metrics = FirstEpisodeMetrics(n, steps, initial_root)
        self.wheel_body_ids = [self.robot.body_names.index(name) for name in WHEEL_NAMES]
        self.leg_joint_ids = [self.robot.joint_names.index(name) for name in M1_LEG_JOINT_NAMES]
        self.wheel_joint_ids = [self.robot.joint_names.index(name) for name in M1_WHEEL_JOINT_NAMES]
        if len(self.leg_joint_ids) != 12 or len(self.wheel_joint_ids) != 4:
            raise ValueError("Invalid named M1 leg/wheel joint mapping")
        self.generic_wheel_ids = [env.scene["contact_forces"].body_names.index(name) for name in WHEEL_NAMES]
        self.wheel_signs = snapshot_array(env.cfg.wave_wheel_action_signs, "wheel action signs", (4,))
        self.scanner_own = np.zeros(n, dtype=np.int64)
        self.scanner_foreign = np.zeros(n, dtype=np.int64)
        self.scanner_invalid = np.zeros(n, dtype=np.int64)
        self.foreign_bar_peak = np.zeros(n)
        self.chunks = []
        self.chunk_count = 0
        self.npz_write_seconds = 0.0
        self.ik_sample_count = 0
        self.measurement_issues = []
        self.started = time.perf_counter()
        randomized = {
            "root_state_w": snapshot_array(self.robot.data.root_state_w, "initial root state", (n, 13)),
            "joint_pos": snapshot_array(self.robot.data.joint_pos, "initial joint positions", (n, 16)),
            "joint_vel": snapshot_array(self.robot.data.joint_vel, "initial joint velocities", (n, 16)),
            "masses": snapshot_array(self.robot.root_physx_view.get_masses(), "realized masses"),
            "material_properties": snapshot_array(self.robot.root_physx_view.get_material_properties(), "realized materials"),
            "env_origins": self.origins,
        }
        np.savez_compressed(self.output / "initial_randomization.npz", **randomized)
        write_json(self.output / "initial_randomization.json", {
            "seed": env.cfg.seed, "arrays": {key: list(value.shape) for key, value in randomized.items()},
            "leg_joint_order": list(M1_LEG_JOINT_NAMES), "wheel_joint_order": list(M1_WHEEL_JOINT_NAMES),
            "wheel_velocity_signs": self.wheel_signs, "gate_source": "controller_oracle",
            "randomization_events": jsonable(env.cfg.events.to_dict()),
            "commands": jsonable(env.cfg.commands.to_dict()),
        })

    @property
    def received_steps(self):
        return self.metrics.received_steps

    def sample(self, env, peaks):
        n, robot = self.num_envs, self.robot
        if self.expected_step != self.received_steps:
            raise ValueError("Recorder step identity mismatch")
        own, foreign, counts = peaks
        root_state = snapshot_array(robot.data.root_state_w, "complete root_state_w", (n, 13))
        joint_pos = snapshot_array(robot.data.joint_pos, "all joint positions including wheel angles", (n, 16))
        joint_vel = snapshot_array(robot.data.joint_vel, "all joint velocities", (n, 16))
        actual_actions = snapshot_array(env.action_manager.action, "actual action-manager actions", (n, 16))
        def attribute(name, shape):
            if not hasattr(env, name):
                raise ValueError(f"Missing required reference attribute: {name}")
            return snapshot_array(getattr(env, name), name, shape)
        joint_ids = attribute("m1_task_space_ik_joint_ids", (4, 3))
        if joint_ids.dtype.kind not in "iu" or joint_ids.reshape(-1).tolist() != self.leg_joint_ids:
            raise ValueError("Task-space IK joint order differs from named leg order")
        jacobians = attribute("m1_task_space_ik_jacobians", (n, 4, 3, 3))
        full_jacobians = attribute("m1_task_space_ik_full_jacobians", (n, 17, 6, 22))
        ik_actions = attribute("m1_task_space_ik_actions", (n, 12))
        generic_forces = snapshot_array(env.scene["contact_forces"].data.net_forces_w, "generic body contact forces")
        generic_forces = generic_forces[self.generic_rows][:, self.generic_wheel_ids]
        sample = {
            "root_pos": root_state[:, :3] - self.origins,
            "gravity": snapshot_array(robot.data.projected_gravity_b, "gravity", (n, 3)),
            "wheel_pos": snapshot_array(robot.data.body_pos_w[:, self.wheel_body_ids], "wheel positions", (n, 4, 3)) - self.origins[:, None],
            "wheel_contact_force": np.linalg.norm(generic_forces, axis=-1),
            "wheel_bar_force_peak": own[:, WHEEL_CONTACT_IDS],
            "nonwheel_bar_force_peak": own[:, NONWHEEL_CONTACT_IDS],
            "wheel_velocity": joint_vel[:, self.wheel_joint_ids] * self.wheel_signs,
            "raw_actions": attribute("m1_raw_policy_actions", (n, 16)),
            "prepared_actions": attribute("m1_prepared_leg_actions", (n, 12)),
            "joint_posture_error": joint_pos[:, self.leg_joint_ids] - snapshot_array(robot.data.default_joint_pos[:, self.leg_joint_ids], "default leg posture", (n, 12)),
            "wave_gate": attribute("m1_wave_gate", (n,)),
            "phase": attribute("m1_sequential_crossing_phase", (n,)),
            "terminated": snapshot_array(env.reset_terminated, "pre-reset terminated", (n,)),
            "timeout": snapshot_array(env.reset_time_outs, "pre-reset timeouts", (n,)),
            "reference_collision": attribute("m1_crossbar_collision_mask", (n, 4)),
        }
        scanner = env.scene["semantic_height_scanner"].data
        scanner_result = check_scanner_hits(
            snapshot_array(scanner.semantic_map, "scanner semantic map"),
            # Ray misses legitimately contain inf; check_scanner_hits handles semantic1 misses explicitly.
            scanner.ray_hits_w.detach().clone().cpu().numpy(), self.bboxes,
        )
        self.scanner_own += scanner_result["own_counts"]
        self.scanner_foreign += scanner_result["foreign_counts"]
        self.scanner_invalid += scanner_result["invalid_counts"]
        self.foreign_bar_peak = np.maximum(self.foreign_bar_peak, foreign)
        self.metrics.update(self.expected_step, sample)
        self.ik_sample_count += 1
        compact = {**sample, "root_state_w": root_state, "joint_pos": joint_pos, "joint_vel": joint_vel,
                   "applied_actions": actual_actions, "ik_joint_ids": joint_ids, "ik_jacobians": jacobians,
                   "ik_actions": ik_actions, "full_jacobian_shape": np.asarray(full_jacobians.shape),
                   "substep_counts": counts, "foreign_bar_peak": foreign,
                   "scanner_own_counts": scanner_result["own_counts"],
                   "scanner_foreign_counts": scanner_result["foreign_counts"],
                   "step": np.asarray(self.expected_step), "elapsed_seconds": np.asarray(time.perf_counter() - self.started)}
        self.chunks.append(compact)
        if len(self.chunks) == 32:
            self.flush()

    def flush(self):
        if not self.chunks:
            return
        started = time.perf_counter()
        stacked = {key: np.stack([sample[key] for sample in self.chunks]) for key in self.chunks[0]}
        name = f"samples_{int(stacked['step'][0]):04d}_{int(stacked['step'][-1]):04d}.npz"
        np.savez_compressed(self.output / name, **stacked)
        self.chunk_count += 1
        self.chunks.clear()
        self.npz_write_seconds += time.perf_counter() - started

    def scanner_report(self):
        return {"valid": bool(not np.any(self.scanner_foreign) and not np.any(self.scanner_invalid) and not np.any(self.foreign_bar_peak > 0)),
                "seen_by_env": (self.scanner_own > 0).tolist(), "own_hit_counts": self.scanner_own.tolist(),
                "foreign_hit_counts": self.scanner_foreign.tolist(), "invalid_hit_counts": self.scanner_invalid.tolist(),
                "foreign_bar_force_peak_by_env": self.foreign_bar_peak.tolist(), "bbox_atol_m": SCANNER_BBOX_ATOL}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("finalize",))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native-exit-code", type=int, required=True)
    parser.add_argument("--expected-pid", type=int, required=True)
    arguments = parser.parse_args()
    start_path = arguments.output / "run_start.json"
    if not start_path.is_file() or json.loads(start_path.read_text())["pid"] != arguments.expected_pid:
        raise SystemExit("Finalizer refuses missing or foreign run ownership")
    final_report, return_code = finalize(arguments.output, arguments.native_exit_code)
    if final_report["completed"]:
        print("M1_REFERENCE_VALIDATION_COMPLETE", json.dumps({key: final_report[key] for key in ("completed", "passed", "startup_passed", "native_exit_code", "wrapper_return_code")}), flush=True)
    else:
        print("M1_REFERENCE_VALIDATION_INCOMPLETE", json.dumps(final_report["finalization_errors"]), flush=True)
    raise SystemExit(return_code)
