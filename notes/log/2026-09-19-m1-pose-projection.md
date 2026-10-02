# M1 whole-collider outward pose projection — 2026-09-19

## Scope / identity

Parent T306.6h.6a.1a.2c.1, approved encounter design §§4.2/5/8. Baseline a89170b, isolated `codex/m1-encounter-lifecycle` at `/data/hexinkun-m1-acceptance-20260918/encounter-worktree`. Main user source, SDK, reference and old artifacts are untouched. Root already944G/free495G; no partition commands repeated. GPU7 reservation351307 remains15744MiB, no competing task compute at preflight.

This package supplies same-step full-body bounds and reproducible inputs. It does not authorize CLEAR, change IK/controller/actions/thresholds, or claim strict behavior/PPO10000. It continues toward registry/coordinator and real encounter gates.

## Implementation

- `collision_pose_projection.py`: vectorized affine intervals for complete boxes, union raw public `PxQuat.rotate`/`PxTransform`, raw `PxMat33`, and exact normalized rational quaternion map. Every elementary operation uses outward binary64 interval arithmetic; raw graphs enclose binary32 rounding, optional skipped intermediate rounding (contraction along the declared graph), and subnormal input/output flushing. Reject unsupported intermediate overflow; no fixed physical slack or raw-pose normalization. The fixed official PhysX commit is32ae713f6cb35f1df2544ffa499fc98a39639a62; actual forward `rotate` was checked, not inverse. No installed internal kernel equivalence claim.
- `collision_projection.py`: detached complete geometry/frame manifest, exact source SHA/stage/generation and ordered named-body mapping; all17 bodies/env covered; per-collider and full robot s/q/z output. Frames from actual validated own-bar bbox centers and ground, +X/FAR-RAR in G1, not the old IK anchor. Per-step output includes projection manifest SHA.
- `collision_provider_live.py` and `run.py`: existing default-off8×32 live flag now binds actual G1 projection frames; direct no-frames raw API unchanged. Any projection error is sticky provider failure, no wheel/root fallback. Lease/native teardown contract unchanged.

## Test evidence

Artifacts below are under `/data/hexinkun-m1-acceptance-20260918/`:

- Fresh baseline199 passed10.30s, provider and conservative geometry.
- Numerical RED `pose-projection-math-red-20260919.log`:53 explicit missing-callable assertions; its wrapper exit forwarding had an extra quoting error, but pytest RED is recorded. Numerical GREEN `pose-projection-math-green2-20260919.log`:56 passed1.09s, commandexit0. Exact Fraction, independent f32 graphs, cancellation, sign/nonunit, invalid inputs, subnormal flushing and overflow cases.
- Binding/live RED `pose-projection-binding-red.log`:45 failed/1 default raw passed5.20s. Validation subset29 passed4.12s. First integrated run85 passed/3 failed: test fixture incorrectly retained pre-permutation geometry SHA, assumed absolute step1 though fixture starts at1, and old source-string assertion expected no keyword. All three corrected to the actual input/contract, without weakening production guards.
- Binding/live+old capture GREEN `pose-projection-binding-green2.log`:88 passed48.17s,exit0.
- Independent exact-real replay `verify_pose_projection_20260919.py`, result `pose-projection-old-replay2.json`:4352 actual collidersteps (32×136), all three exact maps enclosed, max additional bound1.9539731167929496e-6m. Mean/max projection CPU step26.417/49.387ms for136 colliders; no1024 performance claim. Raw pose/old samples preserved SHA341652414ca4b2aee58f3636a066a3e4241da034d4956b8e9312167de1ad7b13, original raw containment40 failures retained. An initial verifier reconstruction passed np.int64 scalars instead of0d ndarray and was rejected; verifier corrected reconstruction, production identity check retained. One command used an incorrect20260919 parent path and did not run; successful replay uses authoritative20260918 parent.
- Main full adapter suite `pose-projection-main-full.log`:2128 passed237.61s,exit0,zero skips. `git diff --check` and `bash -n tools/m1_reference_validation/run.sh` pass. SPEC independent source review PASS, including actual fixed official forward arithmetic graphs. QUALITY Ready/no Critical or Important; independently56 passed1.12s.
- QUALITY Minor: original test oracle could double-round Fraction→binary64→binary32 at a midpoint. Tests-only regression2failed/6passed (`pose-projection-oracle-red.log`) then exact nearest-neighbor Fraction/tie-even fix64passed2.99s (`pose-projection-oracle-green.log`); root fresh64passed3.07s. Reviewer reread the exact diff and approved, Minor resolved. Production hashes unchanged and no runtime candidate changed. Main full2128 count refers to before these8 added tests, not a claim of a fresh2136 full run.

## Native online evidence

Frozen production commit **9dc0dc7b730052fc09e3ff8df4b0e61a4f65d855**. One run `pose-projection-live-20260919`, nativePID68017, run_id a16b3848-3bc6-4c02-836d-6f6fb3be2836, amp/cuda:7. Completed32steps/8env/32prepare/32IK/128physics, no restart; source close→env close→runtime owners release→app close→POST_CLEANUP→native0→wrapper0. startup_passed=true and passed=false. Native process is gone; only original GPU7 reservation351307/15744MiB remains, never paused.

Main independent exact Fraction replay on persisted NPZ: `pose-projection-live-replay2.json`,exit0,4352collidersteps/3 exact maps enclosed. All32 recorded collider bounds and robot unions bit-equal to recomputation from persisted raw geometry/frame/pose. Maximum extra bound1.9539731167929496e-6m, mean/max CPU projection24.320/24.715ms per136-collider step. All28 old non-timing fields plus rawbodypose bits identical to prior live-provider startup. Initial verifier excluded any name containing `time`, unintentionally excluding physical `timeout`; its fixed-count assertion rejected that verifier. Corrected exclusion is ONLY elapsed_seconds; timeout included, denominator unchanged. First failed verifier output remains `pose-projection-live-replay.json`.

23 raw before/after arrays are identical; source cleanupCLOSED,pending0,errors[]; original raw query containment40 failures retained. No extra initialization physics, no root/wheel fallback, no controller changes. This is startup/geometry evidence, not CLEAR or learned behavior. PPO updates=0.

Second independent read-only artifact reviewer did not use the main replay script: directly asserted all32×8 robot unions, full source/settings/artifact/cooked/geometry/projection hash chain, stage/generation/frame/named-body coverage and old28 field/rawpose bit parity. Separately reconstructed rational support for all136 colliders at steps0/7/15/23/31:680 collidersteps ×3 maps=2040 exact maps enclosed. Normal exit/budgets/zero reset and sole original reservation also independently confirmed. This is a second startup/geometry check, not full encounter acceptance.

Hashes:

- projection manifest semantic SHA d6133280117f29b9f5926637f91bc0dee8092ec35e7ad55a973d1a3fe34b2de8; fileSHA6c7980ffbb7054cd68dd6b77f2385863832c0b829cc541b756e69b6041a89a51.
- samples SHA8558a9259daedc3dafe2f586940623d78ba60ee25d8e828da8bef54c1c6c38ee.
- initialization JSON SHAadb62f7b87714ae391e40bfff344fa38b1524081e337d34c25471b7d4ae889b3.
- cleanup JSON SHA7eb72c13da1eb9e74906b92b6474b1630ac8f98ce5431ad3ce4deb4cd4d23139.
- report SHA6736e8f891e39e9677e50f1bb0849f0f07d49c01eb7c52700e856d9dd3a3eeba.
- production kernel9432ebfca3e61ce898fce60ff8d1518c8557007c1b642b98d4bacff6407063f6 and binding7fd21b095e4b40326b1b8e668ec41aa3c593d3c6fbc2ba02332c679501bca5aa stayed unchanged through the tests-only oracle correction.

## Remaining gates

Online8×32 projection gate is verified. Next implement registry/coordinator/reference hook/sync handoff, using this provider rather than repeating getter/query/numeric audits. Three new frozen strict8×1600 passes →1024×32 →1024×1600 full behavior; actual same-obstacle return and multiple obstacles; AME named actions/normal lifecycle; policy-only small crossing and large avoidance; single-process10000 actual PPO updates. None is replaced by these geometry results.

Plan: [outward projection implementation](../../docs/superpowers/plans/2026-09-19-m1-pose-projection.md). Previous input: [raw live provider](2026-09-19-m1-live-provider.md). Branch: [T306](../todo/T306-m1-ame-long-train-stability.md).
