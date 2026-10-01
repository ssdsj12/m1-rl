"""Independent, CPU-only artifact verdict for the fixed post_cross_sync_v1 run.

Never imports the controller, reference evaluator, torch, or the simulator.
The original reports and native/wrapper exit codes are preserved verbatim.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

import numpy as np


N, STEPS = 8, 1600
PARAMETERS = {
    "candidate": "post_cross_sync_v1", "dt": .02, "tau": .20,
    "alpha": 1-math.exp(-.02/.20), "ki": .5, "bias_bound": 1., "slew_rate": 1.,
    "physical_velocity_limit": 20., "feedforward": [1.,1.,1.4,1.4], "ready_samples": 5,
    "wheel_radius": .0959, "bar_center": [.85,-.2], "bar_size": [.06,.16,.06],
    "clearance": .005, "force_threshold": 1., "root_x_min_exclusive": 1.15,
    "height_min": .53, "height_max": .61, "tilt_max": .45, "rounding_atol": 1e-12,
}
GATE_REASONS = {key: 1 << i for i,key in enumerate(("no_packet", "phase11_not_seen",
    "ordered_touchdown_missing", "wave_gate", "nonzero_legs", "wheel_not_past_bar", "wheel_height",
    "ground_force", "root_not_past_gate", "root_height", "tilt", "reference_collision", "bar_contact", "episode_ended"))}
SYNC_SHAPES = {
    "env_id": (), "episode_id": (), "episode_length": (), "active": (), "activation_step": (),
    "events": (2,4), "ready_count": (), "gate_reasons": (), "support_ok": (),
    "original_actions": (16,), "final_actions": (16,), "velocity": (4,),
    "filtered_velocity": (4,), "error": (4,), "bias": (4,), "slew_limited": (4,),
    "bias_limited": (), "physical_limited": (4,), "hold": (), "integral_paused": (),
    "current_root_pos": (3,), "current_wave_gate": (), "current_drive_allowed": (),
    "actual_actions": (16,), "processed_wheel_targets": (4,),
}
SYNC_BOOL = {"active", "support_ok", "slew_limited", "bias_limited", "physical_limited", "hold",
             "integral_paused", "current_wave_gate", "current_drive_allowed"}
SYNC_INT = {"env_id", "episode_id", "episode_length", "activation_step", "events", "ready_count", "gate_reasons"}
SAMPLE_SHAPES = {
    "root_pos": (3,), "gravity": (3,), "wheel_pos": (4,3), "wheel_contact_force": (4,),
    "wheel_bar_force_peak": (4,), "nonwheel_bar_force_peak": (13,), "wheel_velocity": (4,),
    "raw_actions": (16,), "prepared_actions": (12,), "joint_posture_error": (12,),
    "wave_gate": (), "phase": (), "terminated": (), "timeout": (), "reference_collision": (4,),
    "root_state_w": (13,), "joint_pos": (16,), "joint_vel": (16,), "applied_actions": (16,),
    "ik_jacobians": (4,3,3), "ik_actions": (12,), "substep_counts": (), "foreign_bar_peak": (),
    "scanner_own_counts": (), "scanner_foreign_counts": (),
}
EVENT_NAMES = ("prelift_step", "overbar_step", "passed_step", "touchdown_step")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON key {key}")
        result[key] = value
    return result


def _json(path):
    result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object,
                        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"non-finite JSON {x}")))
    _require(isinstance(result, dict), f"{path.name}: expected JSON object")
    return result


def _npz(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        _require(len(names) == len(set(names)), f"{path.name}: duplicate array entries")
        _require(sum(item.file_size for item in archive.infolist()) <= 256*1024*1024,
                 f"{path.name}: archive exceeds bounded offline budget")
    with np.load(path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    for key, value in data.items():
        _require(value.dtype.kind in "biuf" and np.all(np.isfinite(value)),
                 f"{path.name}/{key}: non-finite or non-numeric array")
    return data


def _chunks(root, prefix, shapes):
    paths = sorted(root.glob(f"{prefix}_*.npz"))
    _require(0 < len(paths) <= STEPS, f"{prefix}: missing or excess evidence chunks")
    rows, keys, expected = [], None, 0
    for path in paths:
        match = re.fullmatch(rf"{prefix}_(\d{{4}})_(\d{{4}})\.npz", path.name)
        _require(match is not None, f"{prefix}: malformed or duplicate chunk filename {path.name}")
        data = _npz(path)
        _require("step" in data, f"{path.name}: missing step")
        step = data["step"]
        _require(step.ndim == 1 and step.dtype.kind in "iu" and 0 < len(step) <= STEPS,
                 f"{path.name}: invalid step array")
        _require(np.array_equal(step, np.arange(expected, expected+len(step))) and
                 int(match[1]) == expected and int(match[2]) == expected+len(step)-1,
                 f"{path.name}: missing, duplicate, out-of-order, or mismatched step")
        _require(expected+len(step) <= STEPS, f"{prefix}: more than exact1600 samples")
        _require(set(shapes).issubset(data), f"{path.name}: incomplete fields {sorted(set(shapes)-set(data))}")
        _require(keys is None or set(data) == keys, f"{path.name}: inconsistent chunk fields")
        keys = set(data)
        for key, shape in shapes.items():
            _require(data[key].shape == (len(step),N)+shape, f"{path.name}/{key}: shape mismatch")
        for key, value in data.items():
            _require(value.ndim >= 1 and value.shape[0] == len(step), f"{path.name}/{key}: missing step rows")
        if prefix == "sync":
            for key in SYNC_BOOL:
                _require(data[key].dtype.kind == "b", f"{path.name}/{key}: expected boolean")
            for key in SYNC_INT:
                _require(data[key].dtype.kind in "iu", f"{path.name}/{key}: expected integer")
        else:
            _require(data.get("ik_joint_ids", np.empty(0)).shape == (len(step),4,3), f"{path.name}: missing IK mapping")
            _require(data.get("full_jacobian_shape", np.empty(0)).shape == (len(step),4), f"{path.name}: missing Jacobian shape")
        rows.append(data)
        expected += len(step)
    _require(expected == STEPS, f"{prefix}: incomplete evidence {expected}/{STEPS}")
    return {key: np.concatenate([row[key] for row in rows]) for key in keys}, paths


def _metadata(candidate, baseline, result):
    config = _json(candidate/"configuration.json")
    provenance = _json(candidate/"provenance.json")
    meta = config.get("diagnostic_candidate")
    _require(isinstance(meta, dict) and meta == provenance.get("diagnostic_candidate"),
             "configuration/provenance diagnostic_candidate missing or inconsistent")
    _require(meta.get("name") == "post_cross_sync_v1" and meta.get("parameters") == PARAMETERS,
             "candidate name or fixed parameters changed")
    _require(meta.get("gate_source") == "controller_oracle" and meta.get("gate_reasons") == GATE_REASONS,
             "candidate gate source/reason metadata missing or changed")
    files = meta.get("files")
    _require(isinstance(files, dict) and set(files) == {"post_cross_sync.py", "sync_bridge.py", "sync_verdict.py"}
             and all(isinstance(value,str) and re.fullmatch("[0-9a-f]{64}",value) for value in files.values()),
             "missing/malformed candidate source hashes")
    for name, digest in files.items():
        _require(_hash(Path(__file__).resolve().parent/name) == digest,
                 f"frozen candidate source hash changed: {name}")
    result["candidate_metadata"] = meta
    result["verifier_sha256"] = _hash(Path(__file__))
    for name in ("configuration.json", "provenance.json", "bindings_before.json", "bindings_after.json",
                 "scene_manifest.json", "scene_geometry_measurements.json", "initial_randomization.json"):
        left, right = _json(candidate/name), _json(baseline/name)
        if name in ("configuration.json", "provenance.json"):
            left.pop("diagnostic_candidate", None)
        _require(left == right, f"baseline mismatch: {name} (no path or physics exclusions)")
    for root in (candidate, baseline):
        _require(_json(root/"bindings_before.json") == _json(root/"bindings_after.json"),
                 f"{root.name}: source bindings changed within run")
    left, right = _npz(candidate/"initial_randomization.npz"), _npz(baseline/"initial_randomization.npz")
    required = {"root_state_w", "joint_pos", "joint_vel", "masses", "material_properties", "env_origins"}
    _require(required.issubset(left) and set(left) == set(right), "initial_randomization: missing arrays")
    for key in left:
        _require(_bitwise(left[key],right[key]), f"initial_randomization mismatch: {key}")
    contract = _json(candidate/"sync_live_contract.json")
    for key, value in {"wheel_scale": 1., "actual_offset": 0., "default_joint_velocity": 0.,
                       "wheel_joint_names": [f"{leg}_FOOT_JOINT" for leg in ("FAR","FBL","RAR","RBL")],
                       "action_columns": [12,13,14,15], "dt": .02, "velocity_limit_sim": 20.,
                       "damping": 30., "stiffness": 0.}.items():
        _require(contract.get(key) == value, f"live action units contract mismatch: {key}")
    ids = contract.get("wheel_joint_ids")
    _require(isinstance(ids,list) and len(ids)==4 and len(set(ids))==4
             and all(type(i) is int and 0 <= i < 16 for i in ids), "live wheel joint IDs missing/invalid")
    result["live_contract"] = contract


def _completion(root, report, count):
    start, marker = _json(root/"run_start.json"), _json(root/"POST_CLEANUP.json")
    candidate = _json(root/"candidate_report.json")
    _require(start.get("num_envs") == N and start.get("requested_steps") == STEPS, "run budget must be 8x1600")
    _require(report.get("completed") is True and report.get("native_exit_code") == 0
             and report.get("finalization_errors") == [] and report.get("measurement_issues") == [],
             f"{root.name}: incomplete cleanup/native exit or measurement failure")
    _require(marker.get("run_id") == start.get("run_id") == report.get("run_id") == candidate.get("run_id")
             and isinstance(start.get("run_id"),str) and bool(start["run_id"])
             and marker.get("pid") == start.get("pid") and type(start.get("pid")) is int
             and marker.get("steps") == STEPS
             and marker.get("candidate_sha256") == _hash(root/"candidate_report.json"),
             f"{root.name}: cleanup identity/hash mismatch")
    metrics = report.get("metrics",{})
    _require(metrics.get("num_envs") == N and metrics.get("requested_steps") == STEPS
             and metrics.get("received_steps") == STEPS, f"{root.name}: report budget mismatch")
    rows = metrics.get("per_env",[])
    _require(isinstance(rows,list) and len(rows)==N and [row.get("env_id") for row in rows]==list(range(N)),
             f"{root.name}: missing/duplicate report environment")
    _require(all(row.get("active_sample_count")==STEPS and row.get("reset_count")==0 for row in rows),
             f"{root.name}: first episode incomplete/reset")
    _require(report.get("prepare_and_ik_calls") == {"prepare_calls":STEPS,"ik_calls":STEPS}
             and report.get("ik_sample_count")==STEPS and report.get("sample_chunks")==count,
             f"{root.name}: original prepare/IK/sample count mismatch")


def _bitwise(left, right):
    return left.shape == right.shape and left.dtype == right.dtype and left.tobytes() == right.tobytes()


def _difference(left, right):
    mismatch = left != right
    count = int(np.count_nonzero(mismatch))
    delta = np.abs(left.astype(np.float64)-right.astype(np.float64))
    return {"different_element_count": count, "max_abs_difference": float(delta.max()) if delta.size else 0.,
            "first_difference_step": int(np.argwhere(mismatch)[0,0]) if count else None,
            "dtype_equal": left.dtype == right.dtype, "bitwise_equal": _bitwise(left,right)}


def _prefix(samples, baseline, env, stop):
    _require(set(samples) == set(baseline), "candidate/baseline sample fields differ")
    fields = {}
    for key in sorted(set(samples)-{"step","elapsed_seconds"}):
        left,right = samples[key][:stop],baseline[key][:stop]
        if key not in {"ik_joint_ids","full_jacobian_shape"}:
            _require(left.ndim>=2 and left.shape[1]==N, f"unknown sample environment axis: {key}")
            left,right = left[:,env],right[:,env]
        _require(left.shape==right.shape, f"prefix shape mismatch: {key}")
        fields[key] = _difference(left,right)
    return {"sample_count":stop, "last_included_step":stop-1,
            "unexplained_difference_count":sum(not row["bitwise_equal"] for row in fields.values()),
            "fields":fields, "ignored_fields":["elapsed_seconds"], "comparison":"exact; no physics tolerance"}


def _rms(value, axis=None):
    return np.sqrt(np.mean(np.square(value.astype(np.float64)),axis=axis))


def _observer_replay(samples):
    """Derive full first-episode history from physical samples, without sidecar claims.

    Event detection is an independent search for the first eligible time after
    each predecessor. All returned rows describe prepare(t), hence exclude t.
    """
    positions=samples["wheel_pos"].astype(np.float64)
    force=samples["wheel_contact_force"].astype(np.float64)
    root=samples["root_pos"].astype(np.float64)
    gravity=samples["gravity"].astype(np.float64)
    ends=samples["terminated"].astype(bool)|samples["timeout"].astype(bool)
    ended=np.maximum.accumulate(ends,axis=0)
    alive_before=np.concatenate([np.ones((1,N),bool),~ended[:-1]])
    events=np.full((STEPS,N,2,4),-1,dtype=np.int64)
    times=np.arange(STEPS)
    for env in range(N):
        for column,wheel in enumerate((0,2)):
            x,y,z=positions[:,env,wheel].T
            lateral=np.abs(y+.2)<=.08+.0959+1e-12
            high=z>=.06+.0959+.005-1e-12
            conditions=(lateral&high&(x<=.85-.03-.0959+1e-12),
                        lateral&high&(np.abs(x-.85)<=.03+1e-12)&(force[:,env,wheel]<=1.),
                        x>=.9759-1e-12,
                        (np.abs(z-.0959)<=.005+1e-12)&(x>=.9759-1e-12)&(force[:,env,wheel]>1.))
            previous=-1
            for index,condition in enumerate(conditions):
                eligible=np.flatnonzero(condition&alive_before[:,env]&(times>previous))
                if not len(eligible): break
                previous=int(eligible[0])
                events[previous:,env,column,index]=previous
    right=positions[:,:,[0,2]]
    physical={
        "wheel_not_past_bar":np.any(right[:,:,:,0]<.9759-1e-12,axis=2),
        "wheel_height":np.any(np.abs(right[:,:,:,2]-.0959)>.005+1e-12,axis=2),
        "ground_force":np.any(force[:,:,[0,2]]<=1.,axis=2),
        "root_not_past_gate":root[:,:,0]<=1.15,
        "root_height":(root[:,:,2]<.53-1e-12)|(root[:,:,2]>.61+1e-12),
        "tilt":np.arccos(np.clip(-gravity[:,:,2],-1.,1.))>.45+1e-12,
        "reference_collision":np.any(samples["reference_collision"].astype(bool),axis=2),
        "bar_contact":np.any(samples["wheel_bar_force_peak"].astype(np.float64)>1.,axis=2)
                      |np.any(samples["nonwheel_bar_force_peak"].astype(np.float64)>1.,axis=2),
        "episode_ended":ended,
    }
    support=~np.logical_or.reduce(list(physical.values()))
    failures={**physical,
        "phase11_not_seen":~np.maximum.accumulate((samples["phase"]==11)&alive_before,axis=0),
        "ordered_touchdown_missing":np.any(events[:,:,:,3]<0,axis=2),
        "wave_gate":samples["wave_gate"].astype(bool),
        "nonzero_legs":np.any(samples["prepared_actions"]!=0,axis=2),
    }
    reasons=np.zeros((STEPS,N),np.int64)
    for key,failed in failures.items(): reasons|=failed.astype(np.int64)*GATE_REASONS[key]
    ready=np.zeros((STEPS,N),np.int64)
    running=np.zeros(N,np.int64)
    for step in range(STEPS):
        running=np.where(reasons[step]==0,running+1,0)
        ready[step]=running
    def prior(value,fill):
        return np.concatenate([np.full_like(value[:1],fill),value[:-1]])
    return {"events":prior(events,-1),"gate_reasons":prior(reasons,GATE_REASONS["no_packet"]),
            "ready_count":prior(ready,0),"support_ok":prior(support,False)}


def _replay(sync,samples,result):
    """Independently reproduce the fixed equations and every diagnostic state."""
    replay=_observer_replay(samples)
    active=np.zeros(N,bool)
    first=np.full(N,-1,np.int64)
    filtered=np.zeros((N,4),np.float64)
    bias=np.zeros((N,4),np.float64)
    previous=np.zeros((N,4),np.float64)
    limited=np.zeros((N,4),bool)
    physical=np.zeros((N,4),bool)
    held=np.zeros(N,bool)
    float_keys=("filtered_velocity","error","bias")
    bool_shapes={"active":(),"hold":(),"integral_paused":(),"slew_limited":(4,),
                 "physical_limited":(4,),"bias_limited":()}
    replay.update({key:np.zeros((STEPS,N,4)) for key in float_keys})
    replay.update({key:np.zeros((STEPS,N)+shape,bool) for key,shape in bool_shapes.items()})
    replay["activation_step"]=np.full((STEPS,N),-1,np.int64)
    replay["final_actions"]=sync["original_actions"].copy()
    for step in range(STEPS):
        new=(~active)&(replay["ready_count"][step]>=5)
        integrate=active&replay["support_ok"][step]&~(held|limited.any(axis=1)|physical.any(axis=1))
        velocity=sync["velocity"][step].astype(np.float64)
        filtered[active]+=PARAMETERS["alpha"]*(velocity[active]-filtered[active])
        filtered[new]=velocity[new]
        next_active=active|new
        error=np.zeros((N,4))
        error[next_active]=filtered[next_active].mean(axis=1,keepdims=True)-filtered[next_active]
        saturated=np.zeros(N,bool)
        proposal=bias[integrate]+.01*error[integrate]
        proposal-=proposal.mean(axis=1,keepdims=True)
        divisor=np.maximum(1.,np.max(np.abs(proposal),axis=1,keepdims=True))
        bias[integrate]=proposal/divisor
        saturated[integrate]=divisor[:,0]>1.
        bias[new]=0.
        desired=np.asarray([1.,1.,1.4,1.4])+bias
        delta=desired-previous
        limited=np.zeros((N,4),bool)
        physical=np.zeros((N,4),bool)
        limited[active]=np.abs(delta[active])>.02
        moved=previous[active]+np.clip(delta[active],-.02,.02)
        safe=np.clip(moved,0.,20.)
        physical[active]=safe!=moved
        previous[active]=safe
        if np.any(new):
            _require(step>0,"replay: activation without previous physical packet")
            previous[new]=samples["applied_actions"][step-1,new,12:16].astype(np.float64)
        first[new]=step
        held=new
        active=next_active
        for key,value in {"active":active,"activation_step":first,"hold":held,"integral_paused":~integrate,
                          "slew_limited":limited,"physical_limited":physical,"bias_limited":saturated,
                          "filtered_velocity":filtered,"error":error,"bias":bias}.items():
            replay[key][step]=value
        replay["final_actions"][step,active,12:16]=previous[active].astype(sync["final_actions"].dtype)
    comparisons={}
    for key,expected in replay.items():
        actual=sync[key]
        if key in float_keys:
            different=np.abs(actual.astype(np.float64)-expected)>1e-12
        else:
            different=actual!=expected
        mismatch=np.argwhere(different)
        comparisons[key]={"different_element_count":len(mismatch),
                          "first_mismatch_step":int(mismatch[0,0]) if len(mismatch) else None,
                          "first_mismatch_env":int(mismatch[0,1]) if len(mismatch) else None}
        if len(mismatch):
            result["errors"].append(f"replay {key}: mismatch at step {mismatch[0,0]} env {mismatch[0,1]}")
    # Final command equality is stronger than numerical equality (signed zero,
    # action dtype, and a changed single ULP must not be silently accepted).
    if not _bitwise(replay["final_actions"],sync["final_actions"]) and not comparisons["final_actions"]["different_element_count"]:
        result["errors"].append("replay final_actions: dtype or bitwise mismatch")
    result["independent_replay"]={"fields":comparisons,"filter_bias_arithmetic_atol":1e-12,
                                  "final_action_comparison":"cast expected float64 to recorded action dtype, then bitwise exact"}


def _analyze(sync, samples, baseline, report, result):
    errors = result["errors"]
    def check(condition, message):
        if not bool(condition): errors.append(message)
    check(np.array_equal(sync["env_id"],np.tile(np.arange(N),(STEPS,1))), "sync env_id mismatch/duplicate")
    check(np.all(sync["episode_id"]==0), "sync episode mismatch/reset")
    check(np.array_equal(sync["episode_length"],np.tile(np.arange(STEPS)[:,None],(1,N))), "sync episode_length mismatch")
    check(not np.any(samples["terminated"] | samples["timeout"]), "samples contain termination/timeout")
    check(np.all(samples["raw_actions"]==0), "nonzero raw policy actions")
    check(np.all(samples["substep_counts"]==4), "incomplete physical substeps")
    active, original, final = sync["active"],sync["original_actions"],sync["final_actions"]
    check(_bitwise(original[~active],final[~active]), "inactive complete16 action parity failure")
    check(_bitwise(original[:,:,:12],final[:,:,:12]), "leg action parity failure")
    check(_bitwise(final,sync["actual_actions"]), "actual action-manager actions differ from final")
    check(_bitwise(final,samples["applied_actions"]), "original samples applied_actions differ from final")
    check(_bitwise(final[:,:,12:],sync["processed_wheel_targets"]), "processed wheel targets differ from final rad/s")
    check(np.array_equal(sync["velocity"][1:],samples["wheel_velocity"][:-1]), "prepare velocity mismatches previous physical sample")
    check(np.array_equal(sync["current_root_pos"][1:],samples["root_pos"][:-1]), "prepare root mismatches previous physical sample")
    check(np.all((sync["gate_reasons"]>=0)&(sync["gate_reasons"]<1<<len(GATE_REASONS))), "unknown gate reason bits")
    check(np.all(sync["ready_count"]>=0), "negative readiness count")
    check(np.all(np.abs(sync["bias"])<=1+1e-12), "bias exceeds fixed bound")
    check(np.all(np.abs(sync["bias"].sum(axis=2))<=1e-12), "bias is not zero sum")
    _replay(sync,samples,result)
    for env in range(N):
        indices=np.flatnonzero(active[:,env])
        start=int(indices[0]) if len(indices) else STEPS
        prefix=_prefix(samples,baseline,env,start)
        check(prefix["unexplained_difference_count"]==0,f"env{env}: unexplained preactivation physical/action prefix difference")
        row={"env_id":env,"activation_step":start if start<STEPS else None,"prefix":prefix}
        result["per_env"].append(row)
        check(0<start<STEPS,f"env{env}: no valid activation")
        if not 0<start<STEPS: continue
        mask=active[:,env]
        check(np.all(mask[start:]) and not np.any(mask[:start]),f"env{env}: active state reverted")
        check(np.all(sync["activation_step"][:start,env]==-1) and np.all(sync["activation_step"][start:,env]==start),
              f"env{env}: inconsistent activation_step")
        expected_hold=np.arange(STEPS)==start
        check(np.array_equal(sync["hold"][:,env],expected_hold),f"env{env}: first-output hold flags mismatch")
        check(_bitwise(final[start,env,12:],samples["applied_actions"][start-1,env,12:]),f"env{env}: activation output not previous actual hold")
        check(sync["ready_count"][start,env]>=5 and sync["gate_reasons"][start,env]==0,
              f"env{env}: activation lacks five qualified samples")
        events=sync["events"][start,env]
        check(np.all(events>=0) and np.all(events<start) and np.all(np.diff(events,axis=1)>0),f"env{env}: invalid/late event order")
        check(np.all(sync["events"][start:,env]==events),f"env{env}: event history changed after activation")
        expected_events=np.asarray([[report["metrics"]["per_env"][env]["strict_clearance"][leg][name]
            for name in EVENT_NAMES] for leg in ("FAR","RAR")])
        check(np.array_equal(events,expected_events),f"env{env}: independent event history differs from strict evidence")
        check(np.any(samples["phase"][:start,env]==11),f"env{env}: phase11 not observed before activation")
        check(not np.any(sync["current_wave_gate"][mask,env]) and np.all(sync["current_drive_allowed"][mask,env])
              and np.all(sync["current_root_pos"][mask,env,0]>1.15) and np.all(original[mask,env,:12]==0),
              f"env{env}: active applicability condition failed")
        wheels=final[start:,env,12:]
        check(np.all((wheels>=0)&(wheels<=20)),f"env{env}: active wheel physical/forward bound failure")
        differences=np.diff(wheels.astype(np.float64),axis=0)
        rounding=.5*(np.abs(np.spacing(wheels[:-1])).astype(np.float64)+np.abs(np.spacing(wheels[1:])).astype(np.float64))+1e-12
        check(np.all(np.abs(differences)<=.02+rounding),f"env{env}: active adjacent output exceeds .02 plus half-endpoint-ULP rounding")
        row["active_max_adjacent_target_difference"]=float(np.max(np.abs(differences))) if differences.size else 0.
        row["slew_rounding_allowance_max"]=float(rounding.max()) if rounding.size else 0.
        row["slew_excess_above_exact_point02"]=max(0.,row["active_max_adjacent_target_difference"]-.02)
        tail=np.diff(sync["processed_wheel_targets"][800:1600,env].astype(np.float64),axis=0)
        velocity_delta=np.diff(samples["wheel_velocity"][800:1600,env].astype(np.float64),axis=0)
        target_rms=float(_rms(tail))
        check(len(tail)==799 and target_rms<=.05,f"env{env}: tail800 wheel-target difference RMS exceeds .05")
        row["tail800"]={"first_step":800,"last_step":1599,"sample_count":800,"difference_count":len(tail),
            "wheel_target_difference_rms":target_rms,"wheel_target_difference_rms_by_wheel":_rms(tail,axis=0).tolist(),
            "actual_velocity_difference_rms":float(_rms(velocity_delta)),
            "actual_velocity_difference_rms_by_wheel":_rms(velocity_delta,axis=0).tolist(),
            "wheel_mean_angular_speed":samples["wheel_velocity"][800:,env].mean(axis=0).tolist()}
        means=samples["wheel_velocity"][:,env].mean(axis=0)
        row["wheel_mean_angular_speed"]=means.tolist()
        row["wheel_mean_angular_speed_spread"]=float(np.ptp(means))
        row["bias_saturation_fraction"]=float(np.mean(sync["bias_limited"][start:,env]))
        row["bias_at_bound_fraction"]=float(np.mean(np.max(np.abs(sync["bias"][start:,env]),axis=1)>=1-1e-12))
        row["displacement_after_activation_m"]=(samples["root_pos"][-1,env]-samples["root_pos"][start-1,env]).tolist()
        row["sample0_to_final_displacement_m"]=(samples["root_pos"][-1,env]-samples["root_pos"][0,env]).tolist()


def evaluate(output, baseline):
    """Return a fail-closed JSON-safe verdict without changing any artifact."""
    output,baseline=Path(output),Path(baseline)
    result={"candidate":"post_cross_sync_v1","accepted":False,"sync_checks_passed":False,
            "original_report_passed":False,"original_native_exit_code":None,"original_wrapper_return_code":None,
            "errors":[],"per_env":[],"baseline":str(baseline),"output":str(output),
            "scope":"controller-assisted single-bar diagnostic; not policy-only or broader approval",
            "rounding_policy":"Adjacent target differences allow .02 plus half the ULP of each stored endpoint and 1e-12 double arithmetic; no generic physics tolerance."}
    try:
        report=_json(output/"report.json")
        result.update(original_report_passed=report.get("passed") is True,
                      original_native_exit_code=report.get("native_exit_code"),
                      original_wrapper_return_code=report.get("wrapper_return_code"))
        result["original_report_sha256"]=_hash(output/"report.json")
        _metadata(output,baseline,result)
        samples,paths=_chunks(output,"samples",SAMPLE_SHAPES)
        reference,base_paths=_chunks(baseline,"samples",SAMPLE_SHAPES)
        sync,sync_paths=_chunks(output,"sync",SYNC_SHAPES)
        _completion(output,report,len(paths))
        _completion(baseline,_json(baseline/"report.json"),len(base_paths))
        result["evidence_chunks"]={"samples":len(paths),"sync":len(sync_paths),"baseline_samples":len(base_paths)}
        _analyze(sync,samples,reference,report,result)
    except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError,OverflowError,zipfile.BadZipFile) as error:
        result["errors"].append(f"{type(error).__name__}: {error}")
    result["sync_checks_passed"]=not result["errors"]
    result["accepted"]=result["original_report_passed"] and result["sync_checks_passed"]
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--baseline",type=Path,required=True)
    args=parser.parse_args(argv)
    result=evaluate(args.output,args.baseline)
    try:
        path=args.output/"sync_verdict.json"
        temporary=path.with_name("sync_verdict.json.tmp")
        temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        temporary.replace(path)
    except OSError as error:
        print(f"sync verdict could not be written: {error}")
        return 3
    print(json.dumps({key:result[key] for key in ("accepted","original_report_passed","sync_checks_passed","errors")}))
    return 0 if result["accepted"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
