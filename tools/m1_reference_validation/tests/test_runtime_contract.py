"""CPU contracts for the isolated reference runner and its measurement boundary."""

import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import weakref
from types import SimpleNamespace
from types import ModuleType

import numpy as np
import pytest


def runtime():
    path = Path(__file__).resolve().parents[1] / "runtime.py"
    assert path.is_file(), "Missing reference runtime implementation"
    spec = importlib.util.spec_from_file_location("reference_runtime_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("args", [[], ["--num-envs", "1", "--steps", "32", "--output", "out"],
    ["--num-envs", "8", "--steps", "33", "--output", "out"],
    ["--num-envs", "8", "--steps", "32", "--device", "cuda:0", "--output", "out"],
    ["--num-envs", "8", "--steps", "32", "--device", "cuda:4", "--output", "out"]])
def test_invalid_arguments_are_rejected(args):
    with pytest.raises(SystemExit):
        runtime().parse_args(args)


def test_valid_arguments_and_exclusive_output(tmp_path):
    rt = runtime()
    args = rt.parse_args(["--num-envs", "8", "--steps", "32", "--output", str(tmp_path / "new")])
    assert args.device == "cuda:7" and args.headless is True
    explicit = rt.parse_args(["--num-envs", "8", "--steps", "32", "--device", "cuda:7", "--output", str(tmp_path / "new")])
    assert explicit.device == args.device
    rt.create_output(args.output)
    with pytest.raises(FileExistsError):
        rt.create_output(args.output)


def test_path_stat_cache_disabled_in_both_default_and_shell_launch_contract():
    rt = runtime()
    args = rt.parse_args(["--num-envs", "8", "--steps", "32", "--output", "unused"])
    expected = {"--/app/extensions/pathStatCacheEnabled=false", "--/renderer/multiGpu/enabled=false",
                "--/renderer/multiGpu/autoEnable=false"}
    assert set(args.kit_args.split()) == expected
    shell = (Path(__file__).resolve().parents[1] / "run.sh").read_text()
    for flag in expected:
        assert shell.count(flag) == 1


@pytest.mark.parametrize("fault", [None, "setting_true", "setting_missing", "effective_true", "sdk_hook"])
def test_path_stat_cache_guard_checks_actual_setting_effective_cache_and_hook(monkeypatch, fault):
    import importlib._bootstrap_external as bootstrap
    rt = runtime()
    original = bootstrap._path_stat
    queried = []
    def get_setting(key):
        queried.append(key)
        return True if fault == "setting_true" else None if fault == "setting_missing" else False
    def sdk_cached_hook(path):
        return os.stat(path)
    # Identity must reject even an alias whose name does not expose SDK origin.
    sdk = SimpleNamespace(_os_stat_cached=sdk_cached_hook)
    carb = ModuleType("carb")
    settings = ModuleType("carb.settings")
    settings.get_settings = lambda: SimpleNamespace(get=get_setting)
    carb.settings = settings
    monkeypatch.setitem(sys.modules, "carb", carb)
    monkeypatch.setitem(sys.modules, "carb.settings", settings)
    monkeypatch.setitem(sys.modules, "omni.ext._impl.stat_cache", sdk)
    monkeypatch.setitem(sys.modules, "omni.ext._impl.ext_settings",
                        SimpleNamespace(_is_path_stat_cache_enabled=lambda: fault == "effective_true"))
    if fault == "sdk_hook":
        monkeypatch.setattr(bootstrap, "_path_stat", sdk_cached_hook)
    if fault is None:
        evidence = rt.validate_path_stat_cache_disabled()
        assert evidence["actual_setting"] is False and evidence["effective_cache_enabled"] is False
        assert evidence["path_stat_module"] == original.__module__
        assert evidence["path_stat_qualname"] == original.__qualname__
        assert evidence["path_stat_code_filename"] == original.__code__.co_filename
        assert evidence["sdk_cached_hook_active"] is False
        assert evidence["non_physics_runtime_difference"] is True and evidence["reason"]
    else:
        with pytest.raises(ValueError, match="path-stat cache"):
            rt.validate_path_stat_cache_disabled()
    assert queried == ["/app/extensions/pathStatCacheEnabled"]


def test_source_binding_rejects_editable_production_module(tmp_path):
    rt = runtime()
    reference = tmp_path / "reference"
    reference.mkdir()
    file = reference / "module.py"
    file.write_text("value=1\n")
    modules = {"go2_pvcnn.test": SimpleNamespace(__file__=str(file))}
    assert rt.validate_source_bindings(reference, modules)["go2_pvcnn.test"]["sha256"]
    modules["go2_pvcnn.test"].__file__ = str(tmp_path / "m1_rl/module.py")
    with pytest.raises(ValueError, match="outside reference"):
        rt.validate_source_bindings(reference, modules)


def test_cfg_diff_allows_only_the_isolation_and_measurement_fields():
    rt = runtime()
    before = {"scene": {"num_envs": 1}, "rewards": {"x": {"weight": 3}}, "seed": 20260711}
    after = {"scene": {"num_envs": 8}, "rewards": {"x": {"weight": 3}}, "seed": 20260711}
    assert rt.validate_cfg_diff(before, after) == ["scene.num_envs"]
    after["rewards"]["x"]["weight"] = 9
    with pytest.raises(ValueError, match="rewards.x.weight"):
        rt.validate_cfg_diff(before, after)


def test_104_own_bar_mapping_uses_numeric_column_not_lexical_index():
    rt = runtime()
    paths = sorted(f"/World/semantic_course/small/row_00/col_{i:02d}/slot_00" for i in range(104))
    mapping = rt.own_bar_indices(paths, 104)
    assert paths[mapping[9]].endswith("col_09/slot_00")
    assert paths[mapping[100]].endswith("col_100/slot_00")
    assert mapping[100] != 100
    with pytest.raises(ValueError):
        rt.own_bar_indices(paths[:-1], 104)


def test_sensor_rows_are_proven_from_actual_paths_and_reordered():
    rt = runtime()
    env_order = [1, 0]
    paths = [f"/World/envs/env_{e}/Robot/{name}" for e in env_order for name in rt.CONTACT_BODY_NAMES]
    assert rt.sensor_rows(paths, rt.CONTACT_BODY_NAMES, 2).tolist() == [1, 0]
    paths[-1] = paths[-2]
    with pytest.raises(ValueError, match="body"):
        rt.sensor_rows(paths, rt.CONTACT_BODY_NAMES, 2)


def test_own_and_foreign_bar_forces_are_not_conflated():
    rt = runtime()
    matrix = np.zeros((2, 17, 2, 3))
    matrix[0, 4, 1, 0] = 7.0  # sensor row 0 is env 1, own filter index 1
    matrix[1, 0, 1, 0] = 3.0  # foreign contact in env 0
    own, foreign = rt.reduce_bar_forces(matrix, np.array([0, 1]), np.array([1, 0]))
    assert own[1, 4] == 7 and own[0, 0] == 0
    assert foreign.tolist() == [3.0, 0.0]


def test_four_substeps_capture_transient_contact_and_reject_missing_samples():
    rt = runtime()
    accumulator = rt.SubstepAccumulator(2, 4)
    accumulator.arm(0)
    for index in range(4):
        own = np.zeros((2, 17))
        own[0, 3] = 9 if index == 1 else 0
        accumulator.record(own, np.zeros(2))
    own, foreign, counts = accumulator.consume()
    assert own[0, 3] == 9 and counts.tolist() == [4, 4]
    assert foreign.tolist() == [0, 0]
    accumulator.arm(1)
    accumulator.record(np.zeros((2, 17)), np.zeros(2))
    with pytest.raises(ValueError, match="substep"):
        accumulator.consume()


def test_recorder_bridge_samples_before_fake_auto_reset_and_wrapper_is_called():
    rt = runtime()
    events = []
    accumulator = rt.SubstepAccumulator(8, 4)
    class Sink:
        expected_step = None
        received_steps = 0
        def sample(self, env, peaks):
            events.append("sample")
            assert env.terminated and env.phase == 11
            assert peaks[2].tolist() == [4] * 8
            self.received_steps += 1
    sink = Sink()
    sensor = SimpleNamespace(accumulator=accumulator)
    env = SimpleNamespace(scene={"diagnostic_bar_contacts": sensor}, terminated=False, phase=0)
    bridge = rt.RecorderBridge(lambda: sink)
    class Wrapper:
        num_actions = 16
        num_envs = 8
        def step(self, actions):
            events.append("prepare_actions")
            assert actions.shape == (8, 16) and not np.any(actions)
            bridge.pre_step(env)
            for _ in range(4):
                accumulator.record(np.zeros((8, 17)), np.zeros(8))
            env.phase, env.terminated = 11, True
            bridge.post_step(env)
            events.append("auto_reset")
            env.phase, env.terminated = -1, False
    rt.step_once(Wrapper(), sink, 0, np.zeros((8, 16)), lambda: True)
    assert events == ["prepare_actions", "sample", "auto_reset"]
    with pytest.raises(RuntimeError, match="premature"):
        rt.step_once(Wrapper(), sink, 1, np.zeros((8, 16)), lambda: False)


def candidate_fixture(rt, output, steps=32):
    start = {"run_id": "test", "pid": 123, "num_envs": 8, "requested_steps": steps}
    rt.write_json(output / "run_start.json", start)
    candidate = {"run_id": "test", "scene": {"valid": True},
        "scanner": {"valid": True, "seen_by_env": [True] * 8},
        "source_bindings_valid": True, "measurement_issues": [],
        "metrics": {"received_steps": steps, "requested_steps": steps, "num_envs": 8,
            "completed": False, "passed": False,
            "per_env": [{"env_id": i, "active_sample_count": steps, "reset_count": 0,
                "first_failure_step": None, "flags": {"physical": True}, "passed": True} for i in range(8)]}}
    rt.write_json(output / "candidate_report.json", candidate)
    rt.write_cleanup_marker(output, "test", 123, steps)
    return candidate


@pytest.mark.parametrize("bad", ["candidate", "marker", "native", "budget", "missing_env", "zero_samples"])
def test_finalizer_cannot_complete_without_exact_process_evidence(tmp_path, bad):
    rt = runtime()
    candidate = candidate_fixture(rt, tmp_path)
    native = 0
    if bad in ("candidate", "marker"):
        (tmp_path / ("candidate_report.json" if bad == "candidate" else "POST_CLEANUP.json")).unlink()
    elif bad == "native":
        native = 9
    elif bad == "budget":
        candidate["metrics"]["received_steps"] = 31
        rt.write_json(tmp_path / "candidate_report.json", candidate)
        rt.write_cleanup_marker(tmp_path, "test", 123, 31)
    elif bad == "missing_env":
        candidate["metrics"]["per_env"].pop()
        rt.write_json(tmp_path / "candidate_report.json", candidate)
        rt.write_cleanup_marker(tmp_path, "test", 123, 32)
    else:
        candidate["metrics"]["per_env"][-1]["active_sample_count"] = 0
        rt.write_json(tmp_path / "candidate_report.json", candidate)
        rt.write_cleanup_marker(tmp_path, "test", 123, 32)
    report, code = rt.finalize(tmp_path, native)
    assert report["completed"] is False and report["passed"] is False and code != 0


def test_startup_is_distinct_from_strict_acceptance(tmp_path):
    rt = runtime()
    candidate_fixture(rt, tmp_path)
    report, code = rt.finalize(tmp_path, 0)
    assert report["completed"] is True and report["startup_passed"] is True
    assert report["passed"] is False and code == 0


def test_strict_finalizer_requires_every_environment_and_scanner_evidence(tmp_path):
    rt = runtime()
    candidate = candidate_fixture(rt, tmp_path, 1600)
    candidate["scanner"]["seen_by_env"][-1] = False
    rt.write_json(tmp_path / "candidate_report.json", candidate)
    rt.write_cleanup_marker(tmp_path, "test", 123, 1600)
    report, code = rt.finalize(tmp_path, 0)
    assert report["completed"] is True and report["passed"] is False and code == 3


def test_scanner_foreign_hit_is_rejected_by_actual_own_bbox():
    rt = runtime()
    boxes = np.array([[[0.82, -0.28, -0.015], [0.88, -0.12, 0.045]],
                      [[8.82, -0.28, -0.015], [8.88, -0.12, 0.045]]])
    hit = np.array([[[0.85, -0.2, 0.045]], [[0.85, -0.2, 0.045]]])
    result = rt.check_scanner_hits(np.ones((2, 1)), hit, boxes)
    assert result["own_counts"].tolist() == [1, 0]
    assert result["foreign_counts"].tolist() == [0, 1]


def test_scanner_accepts_float32_world_edge_but_rejects_neighbor_bar():
    rt = runtime()
    boxes = np.array([[[0.82, 4091.72, -0.015], [0.88, 4091.88, 0.045]]])
    hits = np.array([[[0.85, 4091.72, 0.045], [0.85, 4091.88, 0.045],
                      [0.85, 4099.72, 0.045]]], dtype=np.float32)
    result = rt.check_scanner_hits(np.ones((1, 3)), hits, boxes)
    assert result["own_counts"].tolist() == [2]
    assert result["foreign_counts"].tolist() == [1]


def ground_stage():
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.CreateInMemory()
    parent = UsdGeom.Xform.Define(stage, "/World/ground/nested")
    parent.AddTranslateOp().Set((4.0, 5.0, 0.2))
    mesh = UsdGeom.Mesh.Define(stage, "/World/ground/nested/mesh")
    # The actual terrain border retains bottom points after deleting bottom faces.
    mesh.GetPointsAttr().Set([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, -1)])
    mesh.GetFaceVertexCountsAttr().Set([3, 3])
    mesh.GetFaceVertexIndicesAttr().Set([0, 1, 2, 0, 2, 3])
    return stage, mesh


def test_ground_surface_uses_referenced_faces_and_world_transform_not_bbox():
    from pxr import Usd, UsdGeom
    rt = runtime()
    stage, mesh = ground_stage()
    bbox = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(
        stage.GetPrimAtPath("/World/ground")).ComputeAlignedRange()
    assert bbox.GetMax()[2] - bbox.GetMin()[2] == pytest.approx(1.0)
    evidence = rt.ground_surface_evidence(stage)
    assert evidence["surface_height_m"] == pytest.approx(0.2)
    assert evidence["meshes"][0]["unreferenced_vertex_count"] == 1
    assert evidence["meshes"][0]["face_count"] == 2


@pytest.mark.parametrize("invalid", ["missing", "no_faces", "holes", "nonplanar", "nonfinite", "bad_index"])
def test_ground_surface_rejects_missing_or_invalid_surface(invalid):
    rt = runtime()
    stage, mesh = ground_stage()
    if invalid == "missing":
        stage.RemovePrim("/World/ground/nested/mesh")
    elif invalid == "no_faces":
        mesh.GetFaceVertexCountsAttr().Set([])
        mesh.GetFaceVertexIndicesAttr().Set([])
    elif invalid == "holes":
        mesh.GetHoleIndicesAttr().Set([0])
    elif invalid in ("nonplanar", "nonfinite"):
        points = list(mesh.GetPointsAttr().Get())
        points[1] = (1, 0, 0.01 if invalid == "nonplanar" else float("nan"))
        mesh.GetPointsAttr().Set(points)
    else:
        mesh.GetFaceVertexIndicesAttr().Set([0, 1, 99, 0, 2, 3])
    with pytest.raises(ValueError, match="ground|Ground"):
        rt.ground_surface_evidence(stage)


def test_scripts_do_not_import_runtime_simulator_early_or_restart():
    rt = runtime()
    folder = Path(__file__).resolve().parents[1]
    runner = (folder / "run.py").read_text()
    shell = (folder / "run.sh").read_text()
    assert runner.index("audit_provenance(") < runner.index("from isaaclab.app import AppLauncher")
    assert "fast_shutdown=False" in runner
    assert "unset CUDA_VISIBLE_DEVICES" in shell
    assert "--device cuda:7" in shell
    assert "cuda:4" not in runner
    assert 'device=DEVICE' in runner
    for function in ("set_device", "reset_peak_memory_stats", "get_device_properties", "max_memory_allocated"):
        assert f"torch.cuda.{function}(PHYSICAL_GPU)" in runner
    assert shell.count('"${PYTHON_BIN}" "${SCRIPT_DIR}/run.py"') == 1
    assert '"${SCRIPT_DIR}/runtime.py" finalize' in shell
    assert "restart" not in shell.lower()


def test_real_factory_bridge_only_counts_physical_updates(monkeypatch):
    import torch
    rt = runtime()
    filters = [f"/World/semantic_course/small/row_00/col_{i:02d}/slot_00" for i in range(2)]
    paths = [f"/World/envs/env_{i}/Robot/{name}" for i in range(2) for name in rt.CONTACT_BODY_NAMES]
    class FakeParentSensor:
        def _initialize_impl(self):
            self._num_envs, self._device = 2, "cpu"
            self._sensor_paths = paths
            self._body_physx_view = SimpleNamespace(prim_paths=paths)
            self._data = SimpleNamespace(force_matrix_w=torch.zeros(2, 17, 2, 3))
            self.contact_physx_view = SimpleNamespace(sensor_paths=paths, filter_paths=[filters] * len(paths),
                sensor_count=len(paths), filter_count=2)
            self.force = 0.0
        @property
        def body_names(self): return list(self.CONTACT_BODY_NAMES)
        @property
        def semantic_filter_paths(self): return filters
        def _update_buffers_impl(self, env_ids):
            self._data.force_matrix_w.zero_()
            self._data.force_matrix_w[0, 4, 0, 0] = self.force
        def update(self, dt, force_recompute=False):
            assert force_recompute is True
            self._update_buffers_impl(torch.arange(2))
        @property
        def data(self):
            self._update_buffers_impl(torch.arange(2))
            return self._data
    class FakeRecorder:
        def __init__(self, cfg, env): self._env = env
    names = ["isaaclab", "isaaclab.managers", "isaaclab.sensors", "isaaclab.utils",
             "go2_pvcnn", "go2_pvcnn.sensor", "go2_pvcnn.sensor.semantic_contacter",
             "go2_pvcnn.sensor.semantic_contacter.semantic_global_contact_sensor"]
    modules = {name: ModuleType(name) for name in names}
    for name, module in modules.items():
        module.__path__ = []
        monkeypatch.setitem(sys.modules, name, module)
    managers = modules["isaaclab.managers"]
    managers.RecorderTerm = FakeRecorder
    managers.RecorderTermCfg = SimpleNamespace
    managers.RecorderManagerBaseCfg = object
    managers.DatasetExportMode = SimpleNamespace(EXPORT_NONE=0)
    modules["isaaclab.sensors"].ContactSensorCfg = SimpleNamespace
    modules["isaaclab.utils"].configclass = lambda cls: cls
    modules[names[-1]].M1SemanticGlobalContactSensor = FakeParentSensor
    sampled = []
    sink = SimpleNamespace(expected_step=0, sample=lambda env, peaks: sampled.append(peaks))
    sensor_cfg, recorder_cfg = rt.make_diagnostic_cfgs(["/World/semantic_course/small/.*"], {"sink": sink})
    sensor = sensor_cfg.class_type()
    sensor._initialize_impl()
    env = SimpleNamespace(scene={"diagnostic_bar_contacts": sensor})  # no termination manager during construction
    recorder = recorder_cfg.diagnostic.class_type(recorder_cfg.diagnostic, env)
    assert recorder_cfg.dataset_export_mode == 0
    assert recorder_cfg.export_in_record_pre_reset is False
    assert recorder.record_pre_reset(None) == (None, None)
    assert recorder.record_pre_step() == (None, None)
    for index in range(4):
        sensor.force = 5.0 if index == 1 else 0.0
        sensor.update(0.005)
        sensor.data
        sensor.data
    assert recorder.record_post_step() == (None, None)
    assert sampled[0][0][0, 4] == 5.0
    assert sampled[0][2].tolist() == [4, 4]
    assert sensor.physical_update_count == 4


def test_actual_contact_view_order_is_checked_independently():
    rt = runtime()
    expected_sensors = ["/env_0/body", "/env_1/body"]
    filters = ["/bar_0", "/bar_1"]
    assert rt.validate_contact_view_paths(expected_sensors, [filters, filters], expected_sensors, filters)["filter_count"] == 2
    with pytest.raises(ValueError, match="filter"):
        rt.validate_contact_view_paths(expected_sensors, [filters, filters[::-1]], expected_sensors, filters)
    with pytest.raises(ValueError, match="sensor"):
        rt.validate_contact_view_paths(expected_sensors[::-1], filters, expected_sensors, filters)


def test_complete_robot_state_snapshot_rejects_nan_wheel_angle():
    rt = runtime()
    joints = np.zeros((8, 16))
    joints[0, 15] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        rt.snapshot_array(joints, "all joint positions including wheel angles", (8, 16))


def test_adapt_cfg_executes_only_authorized_changes():
    rt = runtime()
    ns = SimpleNamespace
    def dictionary(value):
        if isinstance(value, SimpleNamespace):
            return {key: dictionary(item) for key, item in vars(value).items()}
        if isinstance(value, dict):
            return {key: dictionary(item) for key, item in value.items()}
        return value
    class FakeCfg(SimpleNamespace):
        def to_dict(self): return dictionary(self)
    cfg = FakeCfg(seed=20260711, decimation=4, sim=ns(dt=0.005, device="cuda:0"),
        scene=ns(num_envs=1, replicate_physics=True, filter_collisions=True,
                 robot=ns(spawn=ns(usd_path="original.usda")),
                 terrain=ns(terrain_generator=ns(num_rows=1, num_cols=1, size=(4, 4)), max_init_terrain_level=0)),
        terminations=ns(crossing_success={"function": "original"}), episode_length_s=20,
        acceptance_max_tilt_rad=0.45, wave_max_action_delta_acceptance=2.0,
        acceptance_min_front_wheel_height_m=0.13, acceptance_min_rear_wheel_height_m=0.14,
        base_height_target=0.57, base_height_recovery_start_x=1.1, base_height_recovery_tolerance=0.04,
        acceptance_clearance_contact_force_limit_n=1.0, acceptance_wheel_radius_m=0.095,
        acceptance_wheel_clearance_margin_m=0.005, wave_task_space_ik=True,
        wave_sequential_crossing_reference=True, wave_reference_actions=False,
        commands={"standing_ratio": 0, "lin_vel_x": [0.03, 0.08]}, events={"mass": "randomize"})
    before, after, changes = rt.adapt_cfg(cfg, 8, 1600, "portable.usda", ns(class_type="sensor"), ns(mode="none"))
    assert cfg.scene.terrain.terrain_generator.size == (8.0, 8.0)
    assert cfg.scene.terrain.terrain_generator.num_cols == 8
    assert cfg.sim.device == "cuda:7"
    assert cfg.scene.robot.spawn.usd_path == "portable.usda"
    assert cfg.episode_length_s == pytest.approx(32.02)
    assert cfg.terminations.crossing_success is None
    assert before["commands"] == after["commands"] and before["events"] == after["events"]
    assert before["scene"]["replicate_physics"] is True
    assert after["scene"]["replicate_physics"] is False and cfg.scene.replicate_physics is False
    assert before["scene"]["filter_collisions"] is after["scene"]["filter_collisions"] is True
    assert set(changes) == {
        "episode_length_s", "recorders", "scene.diagnostic_bar_contacts", "scene.num_envs",
        "scene.replicate_physics", "scene.robot.spawn.usd_path",
        "scene.terrain.terrain_generator.num_cols", "scene.terrain.terrain_generator.size",
        "sim.device", "terminations.crossing_success",
    }


def test_actual_interpreter_metadata_requires_the_amp_executable():
    rt = runtime()
    evidence = rt.interpreter_evidence(sys.executable, sys.version)
    assert evidence["sys_executable"] == sys.executable
    assert evidence["python_version"] == sys.version
    assert evidence["sys_executable_resolved"] == str(Path(rt.AMP_PYTHON).resolve())
    with pytest.raises(ValueError, match="amp interpreter"):
        rt.interpreter_evidence("/not/the/amp/python", sys.version)


@pytest.mark.parametrize("failed_file", ["candidate_report.json", "status.json"])
def test_cleanup_still_closes_everything_after_report_write_failure(tmp_path, failed_file):
    rt = runtime()
    events = []
    def writer(path, data):
        events.append("write:" + path.name)
        if path.name == failed_file:
            raise OSError("injected disk failure")
    env = SimpleNamespace(close=lambda: events.append("env.close"))
    app = SimpleNamespace(close=lambda: events.append("app.close"))
    code = rt.cleanup_run(tmp_path, {"run_id": "test", "pid": 123}, {},
        {"sink": SimpleNamespace(received_steps=32), "env": env, "restore_ik": lambda: events.append("restore")}, app, 0,
        writer=writer, marker_writer=lambda *args: events.append("marker"), emit=lambda *args, **kwargs: events.append(str(args[0])))
    assert code != 0
    assert "env.close" in events and "app.close" in events and "restore" in events
    assert events.index("env.close") < events.index("app.close")
    assert "marker" not in events and "POST_CLEANUP" not in events


def test_cleanup_marker_is_written_only_after_every_close_and_report(tmp_path):
    rt = runtime()
    events = []
    code = rt.cleanup_run(tmp_path, {"run_id": "test", "pid": 123}, {},
        {"sink": SimpleNamespace(received_steps=32), "env": SimpleNamespace(close=lambda: events.append("env.close")),
         "restore_ik": lambda: events.append("restore")}, SimpleNamespace(close=lambda: events.append("app.close")), 0,
        writer=lambda path, data: events.append("write:" + path.name),
        marker_writer=lambda *args: events.append("marker"), emit=lambda *args, **kwargs: None)
    assert code == 0
    assert events[-1] == "marker"
    assert events.index("env.close") < events.index("app.close") < events.index("marker")


@pytest.mark.parametrize("failure", [None, "candidate_report.json", "status.json", "env.close", "restore"])
def test_cleanup_releases_caller_and_helper_cyclic_owners_before_app_close(tmp_path, failure):
    rt = runtime()
    events, refs = [], []
    class Owner:
        def __init__(self, name):
            self.name, self.cycle = name, self
            self.received_steps = 32
            refs.append(weakref.ref(self))
        def close(self):
            operation("env.close")
        def __del__(self):
            events.append("destroy:" + self.name)
    def operation(name):
        events.append(name)
        if name == failure:
            raise OSError("injected " + name)
    env, sink, wrapped, sensor, zeros = (Owner(name) for name in ("env", "sink", "wrapped", "sensor", "zeros"))
    sink.env, wrapped.env, sink.robot = env, env, sensor
    holder = {"sink": sink}
    def release():
        nonlocal env, sink, wrapped, sensor, zeros
        holder.clear()
        env = sink = wrapped = sensor = zeros = None
        events.append("caller.release")
    def app_close():
        events.append("app.close")
        assert all(ref() is None for ref in refs), "Runtime owners survived until plugin unload"
    code = rt.cleanup_run(tmp_path, {"run_id": "test", "pid": 123}, {},
        {"sink": sink, "env": env, "restore_ik": lambda: operation("restore")}, SimpleNamespace(close=app_close), 0,
        writer=lambda path, data: operation(path.name), marker_writer=lambda *args: events.append("marker"),
        emit=lambda *args, **kwargs: None, release_runtime_owners=release)
    assert code == (0 if failure is None else 1)
    assert all(ref() is None for ref in refs)
    assert events.index("env.close") < events.index("restore") < events.index("caller.release")
    assert max(events.index("destroy:" + name) for name in ("env", "sink", "wrapped", "sensor", "zeros")) < events.index("app.close")
    assert ("marker" in events) is (failure is None)


@pytest.mark.parametrize("unsubscribe_failure", [None, "hide", "unhide"])
def test_main_partial_initialization_releases_native_owners_before_app_close(tmp_path, monkeypatch, unsubscribe_failure):
    rt = runtime()
    events, refs = [], []
    subscriptions = []
    close_evidence = []
    previous_term = signal.getsignal(signal.SIGTERM)
    class Owner(SimpleNamespace):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.cycle = self
            refs.append(weakref.ref(self))
        def __del__(self):
            events.append("destroy")
        def signal_callback(self, signum, frame):
            pass
    class Subscription:
        def __init__(self, name, callback):
            self.name, self.callback = name, callback
            subscriptions.append(self)  # stand-in for the C timeline registry
        def unsubscribe(self):
            events.append("unsubscribe:" + self.name)
            if self.name == unsubscribe_failure:
                raise RuntimeError("injected unsubscribe failure")
            self.callback = None
            subscriptions.remove(self)
    def app_close():
        events.append("app.close")
        events.append(all(ref() is None for ref in refs))
        close_evidence.append((sum(ref() is not None for ref in refs),
                               signal.getsignal(signal.SIGTERM) is previous_term))
        assert all(getattr(ref(), name, None) is None for ref in refs
                   for name in ("_hide_play_button_callback", "_unhide_play_button_callback"))
    def launcher(*args, **kwargs):
        events.append("launcher")
        owner = Owner(app=SimpleNamespace(close=app_close))
        owner._hide_play_button_callback = Subscription("hide", lambda: owner)
        owner._unhide_play_button_callback = Subscription("unhide", lambda: owner)
        signal.signal(signal.SIGTERM, owner.signal_callback)
        return owner
    def fail_cfg():
        events.append("cfg")
        raise RuntimeError("injected partial initialization failure")
    names = ("isaaclab", "isaaclab.app", "isaaclab.utils", "isaaclab.utils.io", "gymnasium", "torch",
             "go2_pvcnn", "go2_pvcnn.tasks", "go2_pvcnn.tasks.m1_pvcnn_small_obstacle_env_cfg",
             "go2_pvcnn.tasks.m1_rsl_rl_wrapper")
    modules = {name: ModuleType(name) for name in names}
    for name, module in modules.items():
        module.__path__ = []
        monkeypatch.setitem(sys.modules, name, module)
    modules["isaaclab.app"].AppLauncher = launcher
    modules["isaaclab.utils.io"].dump_yaml = lambda *args: None
    modules["go2_pvcnn.tasks.m1_pvcnn_small_obstacle_env_cfg"].M1PvcnnCrossing60mmContactFreePlayEnvCfg = fail_cfg
    modules["go2_pvcnn.tasks.m1_rsl_rl_wrapper"].M1RslRlEnvWrapper = object
    modules["torch"].cuda = SimpleNamespace(set_device=lambda *args: None, reset_peak_memory_stats=lambda *args: None,
        get_device_properties=lambda *args: Owner(name="fake GPU", uuid="fake UUID"))
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    monkeypatch.setitem(sys.modules, "runtime", rt)
    monkeypatch.setitem(sys.modules, "provenance", SimpleNamespace(audit_provenance=lambda *args: {}))
    path = Path(__file__).resolve().parents[1] / "run.py"
    spec = importlib.util.spec_from_file_location("reference_runner_cleanup_test", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    monkeypatch.setattr(runner, "validate_source_bindings", lambda *args, **kwargs: {})
    monkeypatch.setattr(runner, "enable_fatal_diagnostics", lambda: events.append("fatal-diagnostics"))
    cache_evidence = {"actual_setting": False, "non_physics_runtime_difference": True, "reason": "test reason"}
    monkeypatch.setattr(runner, "validate_path_stat_cache_disabled", lambda: events.append("cache-guard") or cache_evidence)
    original_path = list(sys.path)
    try:
        code = runner.main(["--num-envs", "8", "--steps", "32", "--output", str(tmp_path / "partial")])
    finally:
        sys.path[:] = original_path
        signal.signal(signal.SIGTERM, previous_term)
        subscriptions.clear()
    assert code != 0
    assert events.index("launcher") < events.index("fatal-diagnostics") < events.index("cache-guard") < events.index("cfg")
    assert json.loads((tmp_path / "partial" / "runtime_metadata.json").read_text())["path_stat_cache"] == cache_evidence
    assert "unsubscribe:hide" in events and "unsubscribe:unhide" in events
    assert events[-2:] == ["app.close", unsubscribe_failure is None]
    assert close_evidence == [(0 if unsubscribe_failure is None else 1, True)]
    if unsubscribe_failure is not None:
        assert not (tmp_path / "partial" / "POST_CLEANUP.json").exists()


def test_launcher_detach_preserves_third_party_signals_and_handles_absent_attributes():
    rt = runtime()
    class Launcher:
        def handler(self, signum, frame):
            pass
    launcher, third_party = Launcher(), Launcher()
    previous_term = signal.getsignal(signal.SIGTERM)
    fatal_before = {signum: signal.getsignal(signum) for signum in (signal.SIGABRT, signal.SIGSEGV)}
    try:
        signal.signal(signal.SIGTERM, third_party.handler)
        current = signal.getsignal(signal.SIGTERM)
        rt.detach_launcher_owners(None, previous_term)
        rt.detach_launcher_owners(launcher, previous_term)
        assert signal.getsignal(signal.SIGTERM) is current
        assert all(signal.getsignal(signum) is handler for signum, handler in fatal_before.items())
        signal.signal(signal.SIGTERM, launcher.handler)
        rt.detach_launcher_owners(launcher, previous_term)
        assert signal.getsignal(signal.SIGTERM) is previous_term
    finally:
        signal.signal(signal.SIGTERM, previous_term)


@pytest.mark.parametrize("fatal_signal", ["SIGABRT", "SIGSEGV"])
@pytest.mark.parametrize("saved_sdk_handler", [False, True])
def test_fatal_diagnostics_rearm_native_trace_and_preserve_real_exit(tmp_path, fatal_signal, saved_sdk_handler):
    path = Path(__file__).resolve().parents[1] / "runtime.py"
    script = f'''
import faulthandler, importlib.util, os, resource, signal, sys, threading
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
faulthandler.disable()
def sdk_handler(signum, frame):
    print("SDK_PYTHON_HANDLER_CALLED", flush=True)
def terminate_handler(signum, frame):
    pass
signal.signal(signal.SIGTERM, terminate_handler)
if not {saved_sdk_handler!r}:
    faulthandler.enable(file=sys.stderr, all_threads=True)
signal.signal(signal.SIGABRT, sdk_handler)
signal.signal(signal.SIGSEGV, sdk_handler)
if {saved_sdk_handler!r}:
    faulthandler.enable(file=sys.stderr, all_threads=True)
spec = importlib.util.spec_from_file_location("diagnostic_probe_runtime", {str(path)!r})
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)
assert hasattr(rt, "enable_fatal_diagnostics"), "Missing post-AppLauncher fatal diagnostics"
rt.enable_fatal_diagnostics()
assert signal.getsignal(signal.SIGTERM) is terminate_handler
assert faulthandler.is_enabled()
ready = threading.Event()
def diagnostic_background_wait():
    ready.set()
    threading.Event().wait()
threading.Thread(target=diagnostic_background_wait, daemon=True).start()
assert ready.wait(2)
def diagnostic_fatal_probe():
    os.kill(os.getpid(), signal.{fatal_signal})
diagnostic_fatal_probe()
raise SystemExit("Fatal signal was incorrectly suppressed")
'''
    child = subprocess.run([sys.executable, "-c", script], cwd=tmp_path,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                           capture_output=True, text=True, timeout=10)
    assert child.returncode == -int(getattr(signal, fatal_signal)), child.stdout + child.stderr
    assert "M1_REFERENCE_FATAL_DIAGNOSTICS_ENABLED" in child.stdout
    assert "Fatal Python error:" in child.stderr
    assert "diagnostic_fatal_probe" in child.stderr and "diagnostic_background_wait" in child.stderr
    assert "SDK_PYTHON_HANDLER_CALLED" not in child.stdout
    assert not list(tmp_path.glob("core*"))
