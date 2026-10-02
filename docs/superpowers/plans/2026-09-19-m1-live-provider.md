# M1 Live Collision Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Keep the validated collider geometry source lease alive during a real 8×32 run and persist same-step, pre-reset native poses for all 17 bodies, with explicit cleanup before environment destruction.

**Architecture:** A simulator-independent provider owns one CollisionSceneLease, builds the already reviewed conservative local geometry, and polls its source before and after each pose snapshot. A small lazy-SDK adapter initializes it under the existing 23-array no-step guard. Default runtime behavior and the old strict cooked diagnostic remain unchanged. This package produces live raw evidence, not CLEAR decisions, projected extents, strict behavior acceptance, PPO, or a 10000-update claim.

**Tech Stack:** amp Python 3.10, NumPy, pytest, installed Isaac Sim 4.5 / omni.physics.tensors 106.5.7; physical GPU7.

## Verified execution status

Code frozen as `47167e8c6a5664d8959d1f022f5231f7bae853b6`; SPEC→QUALITY PASS; main2026 CPU tests pass. Unique real amp/GPU7 `live-provider-20260919-1830` completes8×32/native0/wrapper0,23 raw guard arrays unchanged,32×8×17 poses,28 old non-timing fields bitwise identical, closed resources before env/app teardown. Full M1 goal remains ACTIVE; this is raw capture startup only, not projected extent/CLEAR/G1/PPO/10000. Evidence: [live-provider verification](../../../notes/log/2026-09-19-m1-live-provider.md).

## Approved scope and baseline

- Implements the online source/pose portion of approved encounter lifecycle spec §§4.2/5/8. The subsequent conservative projection is a distinct gate; not silently supplied by normalized quaternion math.
- Existing isolated worktree `/data/hexinkun-m1-acceptance-20260918/encounter-worktree`, branch `codex/m1-encounter-lifecycle`, baseline `f3ae4a3b8efaab3161be32b39c793cea8d7acd7f`, clean; baseline full suite 1929 passed.
- Local staging `C:/Users/xk/Documents/project/m1_reference_validation_stage/encounter_lifecycle/adapter`; exact SCP to `tools/m1_reference_validation` in isolated worktree only.
- No SDK/reference edits, threshold/budget changes, resets, pumps, native pointer exploration, GPU reservation changes, or automatic restart.

## Task 1: Owned live provider and raw pose transaction

Files: create `tools/m1_reference_validation/collision_provider.py` and `tests/test_collision_provider.py`.

- [x] RED tests exercise real conservative geometry through complete artifact/cooked fixtures, not a mock geometry builder.
- [x] Create `LiveCollisionProvider()` with no native initialization in its constructor. `initialize(lease_factory, query_prim, query_mode, cooked_inspector, capture, write_state, write_report)` captures raw before, constructs/owns lease, submits without pump, finalizes complete query, records cooked evidence unchanged, calls `build_collision_geometry`, checks source, captures raw after, requires byte equality, persists report, then READY. Errors latch FAILED; ownership is retained for explicit cleanup. Capture `CollisionLeaseCleanupError.cleanup_owner` even when lease construction fails.
- [x] `sample(step, episode_ids, body_names, capture_poses)` requires READY, contiguous non-bool integer steps from zero, exact body order matching all environments, nonnegative integer episode vector, and finite raw float32 `(N,17,7)` with nonzero xyzw quaternion. Source is polled before and after copying poses; any failure latches FAILED with no future reuse. No normalization or extent/CLEAR claim.
- [x] Returned detached numeric fields: `collision_body_link_pose_xyzw`, `collision_episode_id`, `collision_step`, `collision_geometry_generation`, `collision_stage_id`, `collision_geometry_sha256` (32 uint8 bytes). Pose dtype/bytes unchanged. Static body paths/order and raw query/cooked/geometry are in initialization report.
- [x] `close()` polls a READY owner one final time, closes the lease with bounded retry for CollisionLeaseCleanupError, records diagnostics and sticky errors, verifies no pending unsubscriptions, and is idempotent. Retain a failed cleanup owner for another explicit attempt; never mask failure or release it merely because retry succeeded. `diagnostics()` returns detached JSON. Initialization/sample/close errors cannot leave a success result.
- [x] GREEN focused tests plus existing geometry/lease/probe tests. Cover stale source before/after capture, no ABA after failure, captured-array mutation, wrong body order, dtype/shape/NaN/zero-quat, step duplicates/gaps, episode validation, initialization failures including persistence and partial constructor cleanup, cleanup ordering/retry/sticky failure.

RED pattern:
```python
def provider_type():
    import importlib.util
    assert importlib.util.find_spec('collision_provider') is not None, 'live provider missing'
    from collision_provider import LiveCollisionProvider
    return LiveCollisionProvider
```

Verification (unique basetemp for every invocation):
```bash
cd /data/hexinkun-m1-acceptance-20260918/encounter-worktree
M1_USD=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310
M1_SCHEMA=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extsPhysics/omni.usd.schema.physx
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp PXR_PLUGINPATH_NAME="$M1_SCHEMA/plugins/PhysxSchema/resources" PYTHONPATH="/data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation:$M1_USD:$M1_SCHEMA" LD_LIBRARY_PATH="$M1_USD/bin:$M1_SCHEMA/bin" /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest tools/m1_reference_validation/tests/test_collision_provider.py -q --basetemp=/data/hexinkun-m1-acceptance-20260918/live-provider-red-20260919
```

## Task 2: Lazy SDK adapter and runtime wiring

Files: create `collision_provider_live.py`; modify `runtime.py`, `run.py`; add `tests/test_collision_provider_runtime.py`.

- [x] RED default/mutual exclusion/budget parsing tests and explicit cleanup-order/failure tests.
- [x] Add `--collision-live-provider`, default false, only 8×32, mutually exclusive with old query/cooked probe.
- [x] Adapter validates existing scene/stage/articulation/body order; uses existing `capture_live_state` under a temporary physics callback. Initialization must leave all 23 arrays identical and absolute physics event count zero. Callback removal and final report persistence must succeed before provider is exposed to sampling. On every failure provider remains reachable for cleanup.
- [x] Runtime creates provider before adapter initialization so partial failures retain ownership. Attach to RuntimeSink; sample raw native link transforms at the existing completed-physics, pre-reset recorder point. Record per-env episode ID, advancing only at recorder post_reset after provider bind; initial constructor reset remains epoch zero. Do not modify controller actions.
- [x] Persist each provider sample in existing chunk NPZ; require 32 snapshots for an 8×32 run. Snapshot only after source poll, clone before backend buffer reuse. Keep the existing sync observer and metrics unchanged.
- [x] cleanup_run closes provider and persists diagnostics before env.close, and preserves all cleanup errors. Existing default cleanup order otherwise unchanged; release provider references before application unload.
- [x] SPEC review clarification: after the bounded close attempts, verify source lease is CLOSED/no pending subscriptions and temporary physics callback removed. If pending or diagnostics unavailable, retain the complete runtime-owner/app/release-closure chain in a process-lifetime quarantine, write cleanup_pending, return nonzero without explicitly closing environment/app or emitting POST_CLEANUP. This only prevents this adapter's unsafe explicit unload; it does not guarantee interpreter/OS final destruction order. Historical error with resources confirmed closed still permits teardown but returns failure.
- [x] SPEC review clarification: recheck current stage, body names, articulation paths and physics clock on both sides of the native getter; test mutations during the getter, not only before it.
- [x] GREEN new runtime tests and old cleanup/probe/recorder tests; validate old strict cooked probe still rejects raw containment failure.

## Task 3: Independent reviews and real verification

- [x] SPEC review of tasks 1–2, then QUALITY review; fix/retest findings before live run.
- [x] Main full CPU suite once final source is stable, fresh basetemp and tee log; no skip-based acceptance.
- [x] Fresh read-only GPU7/process/resource check; preserve verified 15GB reservation if 8-env fits. Run one fresh amp/GPU7 8×32 with `--collision-live-provider` through existing native-exit wrapper. No reuse/overwrite of old output.
- [x] Independently verify raw guard equality, source hashes, 32×8×17 raw poses, monotonic steps, no reset/episode mix, READY through last sample, CLOSED/no pending subscriptions before environment close, native and wrapper exit codes, original raw containment FAIL preserved. This is live capture startup evidence only.
- [x] Update per-test log, notes/todo.md, T306 and notes/log/index.md; preserve dirty main source. Commit isolated reviewed implementation and notes. Keep full goal ACTIVE.

## Pose interpretation follow-up boundary

Installed Tensor API `get_link_transforms` returns float32 and does not normalize in Python. Native public PxQuat/PxTransform and PxMat33 differ for raw quaternions with norm² not exactly one. Fixed official source commit `32ae713f6cb35f1df2544ffa499fc98a39639a62` is the source contract for a later versioned outward-rounded public-pose envelope. No derived world/frame bounds or departure verdict is fabricated in this package.
