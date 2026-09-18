"""One simulator child. Only the external finalizer may declare completion."""

import importlib
import os
from pathlib import Path
import sys
import time
import traceback
import uuid

from provenance import audit_provenance
from runtime import (
    REQUIRED_MODULES, RuntimeSink, adapt_cfg, cleanup_run, create_output, instrument_reference_wrapper,
    interpreter_evidence,
    jsonable, make_diagnostic_cfgs, parse_args, step_once, validate_scene,
    validate_source_bindings, write_json,
)


def main(argv=None):
    args = parse_args(argv)
    interpreter = interpreter_evidence(sys.executable, sys.version)
    output = create_output(args.output)
    run_id = str(uuid.uuid4())
    start = {**interpreter, "run_id": run_id, "pid": os.getpid(), "num_envs": args.num_envs,
             "requested_steps": args.steps, "reference": args.reference, "device": args.device,
             "started_unix": time.time()}
    write_json(output / "run_start.json", start)
    write_json(output / "status.json", {**start, "status": "source_preflight", "received_steps": 0})
    print(f"M1_REFERENCE_START pid={os.getpid()} device=cuda:4 output={output}", flush=True)
    simulation_app = None
    env = None
    sink = None
    restore_ik = None
    candidate = {"run_id": run_id, "measurement_issues": [], "source_bindings_valid": False}
    counters = {"prepare_calls": 0, "ik_calls": 0}
    exit_code = 0
    started = time.perf_counter()
    try:
        provenance = audit_provenance(args.reference)
        write_json(output / "provenance.json", provenance)
        reference = str(Path(args.reference).resolve())
        sys.path[:0] = [reference, str(Path(reference) / "rsl_rl")]
        validate_source_bindings(reference)

        from isaaclab.app import AppLauncher
        launcher = AppLauncher(args, fast_shutdown=False)
        simulation_app = launcher.app
        # Simulator-dependent imports must remain below successful AppLauncher.
        import torch
        import gymnasium as gym
        import go2_pvcnn.tasks
        from go2_pvcnn.tasks.m1_pvcnn_small_obstacle_env_cfg import M1PvcnnCrossing60mmContactFreePlayEnvCfg
        from go2_pvcnn.tasks.m1_rsl_rl_wrapper import M1RslRlEnvWrapper
        from isaaclab.utils.io import dump_yaml

        torch.cuda.set_device(4)
        torch.cuda.reset_peak_memory_stats(4)
        properties = torch.cuda.get_device_properties(4)
        gpu = {"physical_index": 4, "name": properties.name, "uuid": str(properties.uuid),
               "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
               "fast_shutdown": False, "fast_shutdown_default_override_reason": "allow normal Python cleanup and native exit accounting"}
        if gpu["cuda_visible_devices"] is not None:
            raise ValueError("CUDA_VISIBLE_DEVICES must be unset for physical GPU4")
        write_json(output / "runtime_metadata.json", gpu)
        cfg = M1PvcnnCrossing60mmContactFreePlayEnvCfg()
        holder = {"sink": None}
        sensor_cfg, recorder_cfg = make_diagnostic_cfgs(cfg.scene.semantic_contact_small.filter_prim_paths_expr, holder, cfg.decimation)
        before, after, changes = adapt_cfg(cfg, args.num_envs, args.steps, provenance["overlay_path"], sensor_cfg, recorder_cfg)
        write_json(output / "configuration.json", {"before": before, "after": after, "allowlisted_changes": changes,
            "source_wave_and_acceptance": {key: value for key, value in before.items() if key.startswith(("wave_", "acceptance_", "base_height_"))}})
        dump_yaml(str(output / "cfg_before.yaml"), before)
        dump_yaml(str(output / "cfg_after.yaml"), after)
        bindings_before = validate_source_bindings(reference, required=REQUIRED_MODULES)
        write_json(output / "bindings_before.json", bindings_before)
        write_json(output / "status.json", {**start, "status": "creating_environment", "received_steps": 0})
        env = gym.make("Isaac-M1-Pvcnn-Crossing-60mm-ContactFree-Play-v0", cfg=cfg)
        wrapper_module = importlib.import_module("go2_pvcnn.tasks.m1_rsl_rl_wrapper")
        wrapper_type, restore_ik = instrument_reference_wrapper(M1RslRlEnvWrapper, wrapper_module, counters)
        # Original wrapper __init__ performs the one and only explicit reset.
        wrapped = wrapper_type(env.unwrapped, clip_actions=1)
        if wrapped.num_actions != 16 or wrapped.num_envs != args.num_envs:
            raise ValueError("Reference wrapper action/environment contract mismatch")
        scene_report, bboxes, generic_rows = validate_scene(env.unwrapped, output)
        sink = RuntimeSink(env.unwrapped, args.steps, output, bboxes, generic_rows, counters)
        holder["sink"] = sink
        zeros = torch.zeros((args.num_envs, 16), device="cuda:4")
        print("M1_REFERENCE_SCENE_READY", f"exposed_height_m={scene_report['actual_exposed_bar_height_m'][0]:.6f}", flush=True)
        with torch.inference_mode():
            for step in range(args.steps):
                before_ik = counters["ik_calls"]
                step_once(wrapped, sink, step, zeros, simulation_app.is_running)
                if counters["prepare_calls"] != step + 1 or counters["ik_calls"] <= before_ik:
                    raise RuntimeError("Original prepare_actions/task-space IK was not called for this step")
                if (step + 1) % 32 == 0:
                    progress = {**start, "status": "running", "received_steps": sink.received_steps,
                                "elapsed_seconds": time.perf_counter() - started,
                                "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(4), **counters}
                    write_json(output / "status.json", progress)
                    print("M1_REFERENCE_PROGRESS", jsonable(progress), flush=True)
        sink.flush()
        bindings_after = validate_source_bindings(reference, required=REQUIRED_MODULES)
        if any(bindings_after.get(name) != record for name, record in bindings_before.items()):
            raise ValueError("Bound source modules changed during simulation")
        write_json(output / "bindings_after.json", bindings_after)
        sensor = env.unwrapped.scene["diagnostic_bar_contacts"]
        candidate.update({"metrics": sink.metrics.report(process_finalized=False), "scene": scene_report,
                          "scanner": sink.scanner_report(), "source_bindings_valid": True,
                          "candidate_process_finalized": False, "gate_source": "controller_oracle",
                          "prepare_and_ik_calls": counters, "ik_sample_count": sink.ik_sample_count,
                          "sample_chunks": sink.chunk_count, "npz_write_seconds": sink.npz_write_seconds,
                          "sensor_sampling_seconds": sensor.sample_seconds,
                          "physical_sensor_updates": sensor.physical_update_count,
                          "elapsed_seconds": time.perf_counter() - started,
                          "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(4),
                          "gpu": gpu})
    except BaseException as error:
        exit_code = 1
        candidate["measurement_issues"].append(f"{type(error).__name__}: {error}")
        candidate["traceback"] = traceback.format_exc()
        print(candidate["traceback"], flush=True)
        if sink is not None:
            candidate["metrics"] = sink.metrics.report(process_finalized=False)
            try:
                sink.flush()
            except Exception as flush_error:
                candidate["measurement_issues"].append(f"chunk flush: {flush_error}")
    finally:
        exit_code = cleanup_run(output, start, candidate, sink, env, simulation_app, restore_ik, exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
