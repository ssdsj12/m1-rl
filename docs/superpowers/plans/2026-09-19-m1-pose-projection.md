# M1 outward live pose projection implementation plan

> **For agentic workers:** Use subagent-driven-development for the numerical implementation and independent SPEC then QUALITY reviews. Root owns distinct binding/runtime glue. Keep the full encounter and training goal active.

**Goal:** Supply reconstructible, same-step, whole-robot conservative s/q/z bounds from retained live collision geometry and raw native body poses, as required by approved encounter design §§4.2,5,8.

**Architecture:** Pure vectorized interval arithmetic encloses three declared public pose interpretations, without silently normalizing evidence. An immutable geometry/frame binding maps every collider to its environment and named body. The existing default-off 8×32 live capture records the resulting arrays and versioned manifest; no controller, thresholds, SDK, or CLEAR decision changes in this package.

**Tech Stack:** amp Python3.10, NumPy, pytest, existing live CollisionSceneLease. Isolated branch codex/m1-encounter-lifecycle at a89170b; root and /data already expanded, do not repartition.

## Task 1 — numerical kernel

Files: `tools/m1_reference_validation/collision_pose_projection.py` and `tests/test_collision_pose_projection.py`.

- [x] Write tests that dynamically look up missing `project_pose_bounds` and fail an assertion, not collection. API:
  ```python
  actual = project_pose_bounds(bounds_local, poses_xyzw, centers_xyz, directions_xy)
  assert actual.dtype == np.float64 and actual.shape == (len(bounds_local), 2, 3)
  ```
  bounds `(C,2,3)`, poses raw float32 `(C,7)`, centers `(C,3)`, unit directions `(C,2)`. Exact Fraction corner oracle covers normalized rational map, nonunit raw PxQuat and PxMat33, translations, cancellation, sign changes, batches. Independent f32 public expression oracle verifies rounded graphs. Reject invalid shapes/nonfinite/zero quaternion/overflow/bools.
- [x] Record RED, then implement outward elementary interval +,-,*,positive division. At every raw f32 operation enclose both exact and f32-rounded results (including flush-to-zero), so declared graph contraction is included. Translation and frame projection also use outward operations. Exact-normalized rational matrix is included separately; do not claim internal collision-kernel equivalence. Export `POSE_CONTRACT='physx_public_pose_envelope_xyzw_f32_v1'`.
- [x] Run targeted tests under amp with CUDA hidden and unique /data pytest temp; preserve RED/GREEN logs. SPEC then QUALITY review before freezing.

## Task 2 — complete binding and live recording

Files: new `collision_projection.py`, `tests/test_collision_projection.py`; modify `collision_provider_live.py`, `run.py`; add `tests/test_collision_projection_live.py`.

- [x] RED for missing `CollisionProjector(geometry,frames)`. Constructor requires constructed identity-local geometry with valid content SHA; sequential complete environments, unique collider identity, exact named-body index/path mapping, all bodies covered, frame count and generation matching. Defensively copy inputs.
- [x] Implement immutable mapping. `sample(raw_sample)` verifies pose dtype/shape and geometry hash/stage/generation; call Task1 with record-indexed poses and frame centers/directions. Aggregate lower minima and upper maxima by environment. Return `collision_collider_bounds_sqz`, `collision_robot_bounds_sqz`, `collision_projection_sha256`. `manifest()` returns detached JSON with full frame descriptors, ordered record bindings, geometry SHA and contract; manifest SHA covers all fields except itself.
- [x] RED for live opt-in initialization with frames. Preserve no-frames raw capture compatibility; pass G1 frames from the existing validated scene report (own prim paths, actual bbox center, actual ground height, +X, FAR/RAR). Existing IK uses its original env-origin anchor and is untouched.
- [x] Initialize projection inside the guarded capture initialization, write `collision_projection.json`; per-step include projected arrays after the already validated raw pose capture. Any initialization/projection failure invalidates provider and fails run; no fallback to root/wheels. Preserve native lease close ordering and original raw fields.
- [x] Tests use actual pure binding and real live-capture fixture with SDK boundary substituted only. Verify all136 colliders/eight frames, same-step data, manifest detachment, mutation rejection, sticky failure, old raw default unchanged. Existing sink already stores observer fields generically; verify actual NPZ in native run.

## Task 3 — actual replay and normal runtime gate

- [x] Independently replay stored `live-provider-20260919-1830` geometry/poses; verify every collider and frame, finite conservative enclosure with separate exact oracle, not runtime self-report. Preserve old raw containment40 failures and old artifacts.
- [x] Main full adapter suite (prior2026 tests), bash syntax/diff check, SPEC→QUALITY approval; freeze exact files and plan in an isolated commit.
- [x] Fresh disk/GPU7 check. Keep verified351307 reservation if8×32 still fits. Run once:
  ```bash
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 32 --collision-live-provider --output /data/hexinkun-m1-acceptance-20260918/pose-projection-live-20260919
  ```
  No restart/resume. Verify same PID complete32,128physics,32prepare/IK,zeroreset,native0/wrapper0,CLOSED-before-env; verify persisted geometry/manifest/raw poses/projected bounds and old non-timing prefix equality. This is startup/geometry only,0PPO, not G1 or10000.
- [x] Update per-test log, dashboard, T306 and log index with evidence and next concrete registry/coordinator gate. Full objective remains unproven. Do not overwrite user main source or SDK; notes sync only after fresh hash checks.

Verified package: code9dc0dc7, main2128full237.61s/0skip/exit0, SPEC→QUALITY PASS. Tests-only exactRN32 oracle correction64PASS and reviewer approval, production unchanged. Actual unique8×32/native0/wrapper0 plus independent all4352colliderstep rational replay; second independent reviewer2040 exact maps and hash/prefix/cleanup PASS. Detailed evidence: [verification log](../../../notes/log/2026-09-19-m1-pose-projection.md). This closes this plan only; the full user objective below is still ACTIVE.

## Remaining full-goal gates (not replaced by this package)

Encounter registry/coordinator, reference hook and sync handoff; three new frozen8×1600 strict passes;1024×32 then1024×1600 all-env strict; actual same-obstacle return and multiple objects; AME normal lifecycle/named actions; policy-only crossing/avoidance; single process10000 actual PPO updates.
