"""CPU artifact-level tests: the finalizer is independent from the controller."""

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
N, STEPS, START = 8, 1600, 250
PARAMETERS = {"candidate": "post_cross_sync_v1", "dt": .02, "tau": .20,
              "alpha": 1-math.exp(-.02/.20), "ki": .5, "bias_bound": 1., "slew_rate": 1.,
              "physical_velocity_limit": 20., "feedforward": [1.,1.,1.4,1.4], "ready_samples": 5,
              "wheel_radius": .0959, "bar_center": [.85,-.2], "bar_size": [.06,.16,.06],
              "clearance": .005, "force_threshold": 1., "root_x_min_exclusive": 1.15,
              "height_min": .53, "height_max": .61, "tilt_max": .45, "rounding_atol": 1e-12}
GATE_REASONS = {key: 1 << i for i,key in enumerate(("no_packet", "phase11_not_seen",
    "ordered_touchdown_missing", "wave_gate", "nonzero_legs", "wheel_not_past_bar", "wheel_height",
    "ground_force", "root_not_past_gate", "root_height", "tilt", "reference_collision", "bar_contact", "episode_ended"))}


def module():
    path = ROOT / "sync_verdict.py"
    assert path.is_file(), "Missing independent sync verdict implementation"
    spec = importlib.util.spec_from_file_location("verdict_under_test", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")


def mutate_json(path, update):
    value = json.loads(path.read_text())
    update(value)
    write_json(path, value)


def update_npz(path, update):
    with np.load(path, allow_pickle=False) as data:
        value = {key: data[key].copy() for key in data.files}
    update(value)
    np.savez(path, **value)


@pytest.fixture
def runs(tmp_path):
    baseline, candidate = tmp_path / "baseline", tmp_path / "candidate"
    baseline.mkdir(); candidate.mkdir()
    sample = {"step": np.arange(STEPS), "elapsed_seconds": np.arange(STEPS) * .02}
    shapes = {"root_pos": (3,), "gravity": (3,), "wheel_pos": (4, 3),
              "wheel_contact_force": (4,), "wheel_bar_force_peak": (4,),
              "nonwheel_bar_force_peak": (13,), "wheel_velocity": (4,),
              "raw_actions": (16,), "prepared_actions": (12,), "joint_posture_error": (12,),
              "reference_collision": (4,), "root_state_w": (13,), "joint_pos": (16,),
              "joint_vel": (16,), "applied_actions": (16,), "ik_jacobians": (4,3,3),
              "ik_actions": (12,), "substep_counts": (), "foreign_bar_peak": (),
              "scanner_own_counts": (), "scanner_foreign_counts": ()}
    for key, shape in shapes.items():
        sample[key] = np.zeros((STEPS, N) + shape)
    for key in ("wave_gate", "terminated", "timeout"):
        sample[key] = np.zeros((STEPS, N), dtype=bool)
    sample["phase"] = np.full((STEPS, N), 11, dtype=np.int64)
    sample["ik_joint_ids"] = np.tile(np.arange(12).reshape(1,4,3), (STEPS,1,1))
    sample["full_jacobian_shape"] = np.tile([8,17,6,22], (STEPS,1))
    sample["substep_counts"][:] = 4
    sample["root_pos"][:] = [1.2, 0, .57]
    sample["root_pos"][:245,:,0] = 1.1
    sample["root_state_w"][:, :, :3] = sample["root_pos"]
    sample["applied_actions"][:,:,12:] = [1,1,1.4,1.4]
    sample["wheel_velocity"][:] = 1.2
    sample["gravity"][:,:,2] = -1
    sample["wheel_pos"][:] = [1., -.2, .0959]
    sample["wheel_contact_force"][:] = 10
    for wheel in (0,2):
        sample["wheel_pos"][:100,:,wheel] = [.7,-.2,.0959]
        sample["wheel_pos"][100:150,:,wheel] = [.7,-.2,.20]
        sample["wheel_pos"][150:200,:,wheel] = [.85,-.2,.20]
        sample["wheel_pos"][200:210,:,wheel] = [1.,-.2,.20]
        sample["wheel_contact_force"][100:210,:,wheel] = 0
    metadata = {"name": "post_cross_sync_v1", "parameters": PARAMETERS,
                "gate_source": "controller_oracle", "gate_reasons": GATE_REASONS, "files": {
                    name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                    for name in ("post_cross_sync.py", "sync_bridge.py", "sync_verdict.py")}}
    config = {"before": {"seed": 20260711}, "after": {"seed": 20260711, "episode_length_s": 32.02},
              "allowlisted_changes": ["episode_length_s"], "source_wave_and_acceptance": {"gain": 3}}
    event = {leg: {name + "_step": step for name, step in zip(
        ("prelift", "overbar", "passed", "touchdown"), (100,150,200,210))} for leg in ("FAR", "RAR")}
    report = {"run_id": "fixture", "completed": True, "passed": True, "native_exit_code": 0,
              "wrapper_return_code": 0, "finalization_errors": [], "measurement_issues": [],
              "source_bindings_valid": True, "prepare_and_ik_calls": {"prepare_calls": STEPS, "ik_calls": STEPS},
              "ik_sample_count": STEPS, "sample_chunks": 1, "scene": {"valid": True},
              "metrics": {"num_envs": N, "requested_steps": STEPS, "received_steps": STEPS,
                  "per_env": [{"env_id": i, "active_sample_count": STEPS, "reset_count": 0,
                               "strict_clearance": event} for i in range(N)]}}
    for run in (baseline, candidate):
        for filename, value in {
            "configuration.json": config, "provenance.json": {"passed": True, "binary_hashes": {"asset": "a"*64}},
            "bindings_before.json": {"source": {"path": "/reference.py", "sha256": "b"*64}},
            "bindings_after.json": {"source": {"path": "/reference.py", "sha256": "b"*64}},
            "scene_manifest.json": {"valid": True, "num_envs": N},
            "scene_geometry_measurements.json": {"dimensions": [1,2,3]},
            "initial_randomization.json": {"seed": 20260711},
            "run_start.json": {"run_id": "fixture", "pid": 123, "num_envs": N, "requested_steps": STEPS},
            "candidate_report.json": report, "report.json": report,
        }.items():
            write_json(run / filename, value)
        write_json(run / "POST_CLEANUP.json", {"run_id": "fixture", "pid": 123, "steps": STEPS,
            "candidate_sha256": hashlib.sha256((run/"candidate_report.json").read_bytes()).hexdigest()})
        np.savez(run / "initial_randomization.npz", root_state_w=np.zeros((N,13)), joint_pos=np.zeros((N,16)),
                 joint_vel=np.zeros((N,16)), masses=np.ones((N,17)), material_properties=np.ones((N,17,3)),
                 env_origins=np.zeros((N,3)))
        np.savez(run / "samples_0000_1599.npz", **sample)
    for name in ("configuration.json", "provenance.json"):
        mutate_json(candidate/name, lambda d: d.update(diagnostic_candidate=metadata))
    write_json(candidate / "sync_live_contract.json", {
        "wheel_scale": 1., "actual_offset": 0., "default_joint_velocity": 0.,
        "wheel_joint_names": [f"{leg}_FOOT_JOINT" for leg in ("FAR","FBL","RAR","RBL")],
        "wheel_joint_ids": [12,13,14,15], "action_columns": [12,13,14,15],
        "dt": .02, "velocity_limit_sim": 20., "damping": 30., "stiffness": 0.})
    sync = {"step": np.arange(STEPS), "env_id": np.tile(np.arange(N),(STEPS,1)),
            "episode_id": np.zeros((STEPS,N),np.int64),
            "episode_length": np.tile(np.arange(STEPS)[:,None],(1,N)),
            "active": np.arange(STEPS)[:,None].repeat(N,axis=1)>=START,
            "activation_step": np.full((STEPS,N),-1,np.int64),
            "events": np.full((STEPS,N,2,4),-1,np.int64),
            "ready_count": np.zeros((STEPS,N),np.int64),
            "gate_reasons": np.ones((STEPS,N),np.int64),
            "support_ok": np.zeros((STEPS,N),bool),
            "original_actions": sample["applied_actions"].copy(), "final_actions": sample["applied_actions"].copy(),
            "velocity": sample["wheel_velocity"].copy(), "filtered_velocity": np.zeros((STEPS,N,4)),
            "error": np.zeros((STEPS,N,4)), "bias": np.zeros((STEPS,N,4)),
            "slew_limited": np.zeros((STEPS,N,4),bool), "bias_limited": np.zeros((STEPS,N),bool),
            "physical_limited": np.zeros((STEPS,N,4),bool), "hold": np.zeros((STEPS,N),bool),
            "integral_paused": np.zeros((STEPS,N),bool),
            "current_root_pos": sample["root_pos"].copy(), "current_wave_gate": np.zeros((STEPS,N),bool),
            "current_drive_allowed": np.ones((STEPS,N),bool),
            "actual_actions": sample["applied_actions"].copy(),
            "processed_wheel_targets": sample["applied_actions"][:,:,12:].copy()}
    sync["activation_step"][START:] = START
    for event,step in enumerate((100,150,200,210)):
        sync["events"][step+1:,:,:,event] = step
    sync["ready_count"][246:] = np.arange(1,STEPS-245)[:,None]
    sync["gate_reasons"][1:101] = 4+32+256
    sync["gate_reasons"][101:201] = 4+32+64+128+256
    sync["gate_reasons"][201:211] = 4+64+128+256
    sync["gate_reasons"][211:246] = 256
    sync["gate_reasons"][246:] = 0
    sync["support_ok"][246:] = True
    sync["current_root_pos"][1:] = sample["root_pos"][:-1]
    sync["filtered_velocity"][START:] = sample["wheel_velocity"][START:]
    sync["hold"][START] = True
    sync["integral_paused"][:START+2] = True
    np.savez(candidate / "sync_0000_1599.npz", **sync)
    return candidate, baseline


def test_complete_evidence_accepts_and_reports_per_env_tail_metrics(runs):
    candidate, baseline = runs
    result = module().evaluate(candidate, baseline)
    assert result["accepted"] is True, result
    assert result["sync_checks_passed"] is True
    assert len(result["per_env"]) == 8
    row = result["per_env"][0]
    assert row["tail800"]["difference_count"] == 799
    assert row["tail800"]["wheel_target_difference_rms"] == 0
    assert row["tail800"]["actual_velocity_difference_rms"] == 0
    assert row["wheel_mean_angular_speed"] == pytest.approx([1.2]*4)
    assert row["prefix"]["unexplained_difference_count"] == 0


@pytest.mark.parametrize("fault", ["missing_sync", "duplicate", "gap", "shape", "nan", "episode", "env_id",
    "inactive_change", "legs_change", "actual_change", "processed_change", "not_activated", "activation", "hold",
    "slew", "bounds", "bias", "events", "prefix", "config", "randomization", "metadata", "live_units", "truncated"])
def test_rejects_corrupt_or_incomplete_evidence(runs, fault):
    candidate, baseline = runs
    path = candidate / "sync_0000_1599.npz"
    if fault == "missing_sync": path.unlink()
    elif fault == "duplicate": (candidate/"sync_0000_1599_duplicate.npz").write_bytes(path.read_bytes())
    elif fault == "config": mutate_json(candidate/"configuration.json", lambda d: d["after"].update(seed=7))
    elif fault == "metadata": mutate_json(candidate/"provenance.json", lambda d: d["diagnostic_candidate"]["files"].update({"sync_bridge.py":"bad"}))
    elif fault == "live_units": mutate_json(candidate/"sync_live_contract.json", lambda d:d.update(actual_offset=1.))
    elif fault == "randomization": update_npz(candidate/"initial_randomization.npz", lambda d:d["joint_pos"].__setitem__((0,0),.1))
    elif fault == "prefix": update_npz(candidate/"samples_0000_1599.npz", lambda d:d["root_pos"].__setitem__((100,1,0),1.21))
    else:
        def change(d):
            if fault=="gap": d["step"][7]=8
            elif fault=="shape": d["bias"]=d["bias"][:,:,:3]
            elif fault=="nan": d["bias"][500,0,0]=np.nan
            elif fault=="episode": d["episode_id"][500:,0]=1
            elif fault=="env_id": d["env_id"][500,0]=1
            elif fault=="inactive_change": d["final_actions"][0,0,15]=.9
            elif fault=="legs_change": d["final_actions"][500,0,0]=.1
            elif fault=="actual_change": d["actual_actions"][500,0,15]=.9
            elif fault=="processed_change": d["processed_wheel_targets"][500,0,0]=.9
            elif fault=="not_activated": d["active"][:,0]=False
            elif fault=="activation": d["activation_step"][START:,0]=START-1
            elif fault=="hold": d["hold"][START,0]=False
            elif fault=="slew": d["final_actions"][600,0,15]+=1
            elif fault=="bounds": d["final_actions"][600,0,15]=-1
            elif fault=="bias": d["bias"][600,0,0]=1.01
            elif fault=="events": d["events"][START:,0,0,0]=START+1
            elif fault=="truncated":
                for key in d: d[key]=d[key][:-1]
        update_npz(path,change)
    result=module().evaluate(candidate,baseline)
    assert result["accepted"] is False, fault
    assert result["sync_checks_passed"] is False, fault
    assert result["errors"], fault


def test_original_strict_failure_kept_separate_from_sync_contract(runs):
    candidate,baseline=runs
    mutate_json(candidate/"report.json",lambda d:d.update(passed=False,wrapper_return_code=3))
    result=module().evaluate(candidate,baseline)
    assert result["original_report_passed"] is False
    assert result["sync_checks_passed"] is True
    assert result["accepted"] is False
    assert result["original_native_exit_code"]==0
    assert result["original_wrapper_return_code"]==3


def test_walltime_ignored_but_physical_prefix_fields_reported(runs):
    candidate,baseline=runs
    update_npz(candidate/"samples_0000_1599.npz",lambda d:d["elapsed_seconds"].__setitem__(slice(None),42))
    assert module().evaluate(candidate,baseline)["accepted"]
    update_npz(candidate/"samples_0000_1599.npz",lambda d:d["joint_vel"].__setitem__((15,3,2),.2))
    result=module().evaluate(candidate,baseline)
    assert not result["accepted"]
    assert result["per_env"][3]["prefix"]["fields"]["joint_vel"]["max_abs_difference"]==.2


def test_cli_exit_code_writes_only_new_verdict(runs):
    candidate,baseline=runs
    module()
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in candidate.iterdir()}
    command=[sys.executable,"-B",str(ROOT/"sync_verdict.py"),"--output",str(candidate),"--baseline",str(baseline)]
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stderr+result.stdout
    assert json.loads((candidate/"sync_verdict.json").read_text())["accepted"] is True
    assert all(hashlib.sha256((candidate/name).read_bytes()).hexdigest()==digest for name,digest in before.items())
    mutate_json(candidate/"report.json",lambda d:d.update(passed=False,wrapper_return_code=3))
    assert subprocess.run(command,capture_output=True,text=True).returncode==3


def test_missing_original_report_is_rejected_without_exception(runs):
    candidate,baseline=runs
    (candidate/"report.json").unlink()
    result=module().evaluate(candidate,baseline)
    assert result["accepted"] is False
    assert "report.json" in " ".join(result["errors"])


def test_tail800_rejects_one_env_even_when_pooled_rms_passes(runs):
    candidate,baseline=runs
    def change_sync(d):
        for key in ("final_actions","actual_actions"):
            d[key][800:,0,12:] += (np.arange(800)%2)[:,None]*.08
        d["processed_wheel_targets"][800:,0] += (np.arange(800)%2)[:,None]*.08
    update_npz(candidate/"sync_0000_1599.npz",change_sync)
    update_npz(candidate/"samples_0000_1599.npz",lambda d:
        d["applied_actions"].__setitem__((slice(800,None),0,slice(12,None)),
            d["applied_actions"][800:,0,12:]+(np.arange(800)%2)[:,None]*.08))
    result=module().evaluate(candidate,baseline)
    assert result["accepted"] is False
    assert any("env0: tail800" in error for error in result["errors"])
    rms=[row["tail800"]["wheel_target_difference_rms"] for row in result["per_env"]]
    assert rms[0]==pytest.approx(.08)
    assert np.sqrt(np.mean(np.square(rms)))<.05
    assert all(value==0 for value in rms[1:])


@pytest.mark.parametrize("increment,adjacent_valid",[(.02,True),(.02001,False),(.02000022,False)])
def test_adjacent_float32_accepts_only_endpoint_half_ulp_rounding(runs,increment,adjacent_valid):
    candidate,baseline=runs
    def change_sync(d):
        for key in ("original_actions","final_actions","actual_actions","processed_wheel_targets"):
            d[key]=d[key].astype(np.float32)
        for key in ("final_actions","actual_actions"):
            d[key][500:,0,15]+=increment
        d["processed_wheel_targets"][500:,0,3]+=increment
    def change_sample(d,is_candidate):
        d["applied_actions"]=d["applied_actions"].astype(np.float32)
        if is_candidate: d["applied_actions"][500:,0,15]+=increment
    update_npz(candidate/"sync_0000_1599.npz",change_sync)
    update_npz(candidate/"samples_0000_1599.npz",lambda d:change_sample(d,True))
    update_npz(baseline/"samples_0000_1599.npz",lambda d:change_sample(d,False))
    result=module().evaluate(candidate,baseline)
    # The deliberate target perturbation independently fails formula replay;
    # here isolate whether its adjacent change also violates the ULP bound.
    adjacent_errors=[error for error in result["errors"] if "adjacent" in error]
    assert bool(adjacent_errors) is not adjacent_valid,result["errors"]


def test_matching_metadata_hashes_still_require_frozen_source_content(runs):
    candidate,baseline=runs
    for filename in ("configuration.json","provenance.json"):
        mutate_json(candidate/filename,lambda d:d["diagnostic_candidate"]["files"].update({"sync_bridge.py":"0"*64}))
    result=module().evaluate(candidate,baseline)
    assert not result["accepted"]
    assert any("frozen candidate source hash changed" in error for error in result["errors"])


@pytest.mark.parametrize("fault",["missing_prelift","gate_interruption","filter","error","bias","antiwindup"])
def test_independent_replay_rejects_fabricated_finite_diagnostics(runs,fault):
    candidate,baseline=runs
    if fault in ("missing_prelift","gate_interruption"):
        for run in (candidate,baseline):
            if fault=="missing_prelift":
                update_npz(run/"samples_0000_1599.npz",lambda d:d["wheel_pos"].__setitem__((slice(100,150),0,0,2),.0959))
            else:
                update_npz(run/"samples_0000_1599.npz",lambda d:d["wheel_contact_force"].__setitem__((247,0,0),0))
    else:
        def change(d):
            if fault=="filter": d["filtered_velocity"][400,0,0]+=.1
            elif fault=="error": d["error"][400,0,0]=.1
            elif fault=="bias": d["bias"][400,0,:2]=[.1,-.1]
            elif fault=="antiwindup": d["integral_paused"][START+1,0]=False
        update_npz(candidate/"sync_0000_1599.npz",change)
    result=module().evaluate(candidate,baseline)
    assert result["accepted"] is False,fault
    assert any("replay" in error for error in result["errors"]),result["errors"]


def test_numpy_verdict_replays_real_core_varying_velocity_trace_on_cpu(runs):
    """Cross-implementation check, including float32 commands and bias projection."""
    import torch
    spec=importlib.util.spec_from_file_location("cpu_core_for_verdict_test",ROOT/"post_cross_sync.py")
    core_module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core_module)
    core=core_module.PostCrossSync(num_envs=N)
    candidate,baseline=runs
    with np.load(candidate/"samples_0000_1599.npz") as archive:
        samples={key:archive[key].copy() for key in archive.files}
    samples["reference_collision"]=samples["reference_collision"].astype(bool)
    samples["applied_actions"]=samples["applied_actions"].astype(np.float32)
    samples["wheel_velocity"][300:]=np.asarray([5.,-2.,3.,-1.])
    samples["wheel_velocity"][300:]+=np.sin(np.arange(1300)*.07)[:,None,None]*np.asarray([.2,.1,-.1,-.2])
    samples["wheel_contact_force"][700:706,0,0]=0
    rows=[]
    original=torch.zeros((N,16),dtype=torch.float32)
    original[:,12:]=torch.tensor([1.,1.,1.4,1.4])
    for step in range(STEPS):
        current={"wheel_velocity":samples["wheel_velocity"][max(0,step-1)],
                 "root_pos":samples["root_pos"][max(0,step-1)],
                 "wave_gate":np.zeros(N,bool),"drive_allowed":np.ones(N,bool),
                 "episode_length":np.full(N,step,np.int64)}
        final,diagnostic=core.prepare(step,original,current)
        row={key:value.detach().cpu().numpy().copy() for key,value in diagnostic.items()}
        row.update(step=np.asarray(step),env_id=np.arange(N),episode_length=current["episode_length"].copy(),
                   current_root_pos=current["root_pos"].copy(),current_wave_gate=current["wave_gate"].copy(),
                   current_drive_allowed=current["drive_allowed"].copy(),actual_actions=final.numpy().copy(),
                   processed_wheel_targets=final[:,12:].numpy().copy())
        rows.append(row)
        samples["applied_actions"][step]=final.numpy()
        packet={key:value[step].copy() for key,value in samples.items()}
        packet.update(episode_id=np.zeros(N,np.int64),env_id=np.arange(N))
        core.observe(step,packet)
    sidecar={key:np.stack([row[key] for row in rows]) for key in rows[0]}
    assert sidecar["bias_limited"].any(),"trace must exercise bounded projection"
    assert sidecar["slew_limited"].any(),"trace must exercise rate limiting"
    assert sidecar["integral_paused"][702,0] and not sidecar["support_ok"][702,0]
    np.savez(candidate/"sync_0000_1599.npz",**sidecar)
    np.savez(candidate/"samples_0000_1599.npz",**samples)
    def baseline_types(d):
        d["applied_actions"]=d["applied_actions"].astype(np.float32)
        d["reference_collision"]=d["reference_collision"].astype(bool)
    update_npz(baseline/"samples_0000_1599.npz",baseline_types)
    result=module().evaluate(candidate,baseline)
    assert result["accepted"] is True,result["errors"]
