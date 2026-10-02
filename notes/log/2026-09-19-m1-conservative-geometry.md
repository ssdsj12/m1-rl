# M1 conservative local collision geometry

## Scope and references

- Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child `T306.6h.6a.1a.2c.1 QUERY_BOUND_ROUNDING`.
- Approved behavior: [encounter lifecycle spec](../../docs/superpowers/specs/2026-09-19-m1-encounter-lifecycle-design.md).
- Implementation: [plan](../../docs/superpowers/plans/2026-09-19-m1-conservative-geometry.md).
- Baseline and last verified at start: `36bec9240bf90dc8d30e6999679a535bdf56e972` (unchanged production code `c02bde0`, 1785 full tests).
- Existing live negative evidence: [cooked capture](2026-09-19-m1-live-cooked-evidence.md).

## Design decision

This is an explicit derived representation, not a relaxed raw-query check. Mesh bounds are the coordinate-wise union of every complete cooked hull's extrema and original query bounds. Native Cylinder bounds include source and float32-converted positive dimensions plus query bounds. No synthetic Cylinder hull/vertices are claimed. The builder supports the actual meter/Z-up, unit body scale, identity collider-to-body contract; other collider transforms are explicitly unsupported until their cooked-coordinate semantics are implemented.

Input completeness and raw diagnostic consistency are verified by replaying the existing pure collector and comparing its full canonical digest. All Mesh records must be available and complete first. Thus a failed strict containment check may coexist with a constructed conservative representation, but a partial/getter/preflight failure cannot be accepted by matching error strings. No collector code or old artifact is changed.

The original 40 raw failures remain failures. The `.005 m` clearance, `_ROUNDING_ATOL`, action owner, native runtime, original reference and policy thresholds are unchanged.

## Resource evidence

Fresh SSH confirms isolated worktree `codex/m1-encounter-lifecycle`, separate git-dir/common-dir and no superproject. Root now 944G, 448G used / 497G free; `/data` about 6.4T free. Only GPU7 task-related compute process is original `hexinkun python sleep.py` PID351307, start Sep18 23:05:13, 15744MiB. It was not stopped. No new Kit process or training was started for the local geometry package.

## Initial independent findings

The frozen live capture contains 136 matching collider identities, 104 available Mesh hulls / 3664 vertices and 32 native Cylinders. Read-only analysis confirms union bounds contain all hull vertices and all query boxes. For actual Cylinders (axis Y, radius .0959, height .0465), source and float32 analytic extrema must both be covered. Query `local_rot` must not be applied again because its query AABB already reflects Y-axis geometry.

## Verification status

Implementation commit: `7b6ddd7e3fdd640440a646f5e2a9c62063521461`, exactly two new source/test files (135/361 lines). Original collector, runtime and SDK unchanged.

Implementation RED: 131 tests failed with the expected explicit `build_collision_geometry callable is required` assertion (3.10s), not fixture/import failures. First focused GREEN: 209 tests passed (2.77s, exit0, zero skips). Final focused GREEN: **210 passed / 2.75s / exit0 / zero skips**, comprising 132 new tests and 78 existing collector tests. The final added case uses real two-env/two-body nonlexical ordering; rotation non-use is checked with an asymmetric box. Main full suite: **1917 passed / 178.69s / exit0 / zero skips**, handle78621 terminal. `git diff --check` and `bash -n run.sh` pass; local/remote source and test hashes match.

Independent SPEC: PASS after actual code/diff review, 17 additional corruption cases rejected and 12 XYZ×dimension cases accepted including float32 minimum positive subnormal and maximum finite values. Pure module import and original JSON immutability also checked.

QUALITY first review: one Important found, no Critical/Minor. Public builder accepts JSON integer Cylinder dimensions; `2**54+1` is rounded down by float64 conversion to `2**54`, and float32 is also `2**54`, so the later `max` cannot restore the lost radius 1 or half-height .5. Main independently reproduced the radius defect on an in-memory copy of the real artifact with source hashes recomputed. Existing live dimensions are floats and are not affected. This is not a reason to loosen physical thresholds or rerun the unchanged simulator.

Correction commit `3d97e9bcf85f71ceb79630c71010ba77288c0eeb` adds only a builder-local exact-integer conversion check for source Cylinder dimensions and original query bounds. RED reproduced **8 failed / 5 passed / 131 deselected / .74s**: two dimensions plus six query endpoints, including mixed integer/float sequences. Final focused GREEN: **222 passed / 2.88s / exit0 / zero skips**, 144 geometry tests plus 78 unchanged collector tests. Original values are retained with object dtype for the comparison, so prior NumPy mixed-sequence promotion cannot hide precision loss. The shared `_real_array`, collector and SDK stay unchanged. Evidence: `conservative-lossless-red-20260919.log`, `conservative-lossless-green-20260919.log`.

Main actual-capture replay on the correction also PASS, producing the **same** geometry digest and original raw JSON digest; report `conservative-live-replay-v2-20260919.json`. Main has read the exact delta; `git diff --check` is clean.

Final gates on `3d97e9b`: **SPEC PASS → QUALITY PASS**. SPEC independently rejected 8 lossy public API inputs, accepted 12 exact integer/float and 33 list/tuple/int64 cases; QUALITY independently rejected 8 lossy and accepted 8 exact integer inputs. No remaining Critical/Important/Minor issues. Main fresh full v2: **1929 passed / 178.99s / exit0 / zero skips**, handle55138 terminal. Log `conservative-main-full-v2-20260919.log`, fresh basetemp `conservative-main-full-v2-20260919`; the earlier full log is retained. Main local/remote SHA matched for both files; `bash -n run.sh` and diff checks pass.

Final resource check: root944G / 449Gused / **495G available**, `/data`673Gused / about6.4Tfree; GPU7 still only original PID351307/15744MiB. No task Kit or training process. This turn is implementation progress, not a new blocker or full-goal completion.

Test logs on server under `/data/hexinkun-m1-acceptance-20260918/`: `conservative-impl-red-20260919.log`, `conservative-impl-green-20260919.log`, `conservative-impl-green2-20260919.log`, `conservative-main-full-20260919.log`. Fresh full-suite basetemp is `conservative-main-full-20260919`; no old fixtures/evidence were overwritten.

Main independently replayed the actual frozen negative capture using `/data/hexinkun-m1-acceptance-20260918/verify_live_local_geometry_20260919.py`; report `/data/hexinkun-m1-acceptance-20260918/conservative-live-replay-20260919.json` is PASS for **local representation only**:

- 136 exact collider identities; 104 Mesh / 3664 vertices contained, all original query boxes retained.
- 32 native Cylinders; 192 source analytic extrema and 192 float32 analytic extrema contained; no manufactured vertices/hulls.
- 168 expanded boundary components across Mesh and Cylinder, maximum `8.308887480823479e-9 m` (Cylinder contribution; prior Mesh-only maximum remains `7.450580596923828e-9 m`).
- Derived representation SHA256 `9cecf087d7103a8930ce8e5bc6a9e2bd55b422041de73f1a9b4a965058068fae` independently recomputed.
- Original JSON SHA256 remains `003aaae8f10a3f0500d1ba06bc7a64711f259b555e04c0200eb0f11a915d5597`; report/cooked results both remain `failed`, exact 40 errors unchanged. Builder input/output mutation independence checked separately in unit tests.

This is not a new simulation or strict behavior result. No PASS is inferred for the old raw diagnostic.

## Live-provider boundary

`query_initialization_probe.probe()` remains a strict diagnostic and closes its lease before returning. Its report cannot confer live geometry validity. The next coherent runtime package must own an open `CollisionSceneLease`, preserve the 23 unchanged initialization state arrays, copy all 17 same-step native body link poses with step/episode/env/body/generation/hash identity, poll source validity around use, and close the lease before `env.close()`. Per-step conservative world/frame projection must account for every floating operation, rather than applying an unexplained final epsilon. This package does not claim these consumers are wired.

The bounded independent math audit supplied a feasible vectorized interval recipe for the next package: explicitly version `R(q)` as the homogeneous quadratic quaternion rotation matrix divided by `q dot q`, then compute `a=R^T d`, `rho=d dot (translation-frame_center)`, and `rho+sum(a_j*[local_min_j,local_max_j])`, outward-rounding **every** arithmetic operation. Fraction checks on 136 actual poses in each of two directions, 160 random inputs and 4 pathological inputs reported no mathematical containment violations. Actual raw q norm² spans `[0.9999998807907141,1.0000002537292019]`; normalized and raw unit-assumption formulas differ in X support by up to `2.380496197479166e-8 m`. Therefore the next pose mapping must be explicit; mathematical interval coverage alone must not be advertised as proof of SDK internal arithmetic. The audit made no production changes or new permission demand.

The full goal remains active: new strict repeated 8-env runs, 1024 capacity/full behavior, real repeated encounters, AME/named-action integration, policy-only crossing/avoidance and single-process 10000 updates remain unverified. No restart stitching or reduced test denominator is authorized by this local representation change.
