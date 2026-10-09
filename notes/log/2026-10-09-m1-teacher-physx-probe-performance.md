# 2026-10-09 M1 PhysX crossing-probe progress instrumentation

## Priority and current result

The user reaffirmed the acceptance order: strict obstacle crossing and a safe
far-side touchdown come first; restoring the pre-crossing balance is a separate
post-crossing phase. The strict crossing tracker already separates those gates.

The live-USD geometry-only probe passed for all six forward obstacles. Its
predicted wheel-envelope clearance is 5 cm, far-side landing margin is about
22 cm, and reference vertical acceleration is 0.95–1.52 m/s². This validates
only geometric reference feasibility, not physical actuation or crossing.

## Physical-probe attempt and observed bottleneck

- The teacher-driven PhysX probe was launched on GPU7 for 320 steps, then
  restarted for 64 steps to bound the experiment. Both remained in high CPU
  use for more than seven minutes without emitting a final summary.
- The second run's log stopped after Kit/terrain initialization messages; no
  strict crossing, landing, collision, or recovery result was produced. Both
  probes were manually terminated by exact PID. No training or checkpoint
  write occurred.
- The shell timeout did not promptly terminate the Isaac process. The existing
  script emitted no stage/step heartbeat, so the delay could not be localized
  to app startup, environment reset, teacher planning, or physics stepping.
- Added `M1_TEACHER_PHYSX_PROGRESS` stage and per-step timing output, defaulting
  to every eight control steps. Test-first regression: initially failed because
  the progress contract was absent; after implementation the focused test
  passes and the script compiles.
- The GPU7 placeholder was restored after each run. On the latest read-only
  check it was PID 2803 using 10,624 MiB, and a separate `python3` process
  (PID 4139569) used 3,194 MiB; total GPU memory was 13,861 MiB and utilization
  100%. The separate process was not touched. No M1 train/eval/probe is active.

## Verification and next gate

- WBC/crossing CPU regression set: 137 passed.
- New physical-probe progress-contract test: 1 passed.
- Next: once GPU7 is available without displacing the separate process, rerun
  the instrumented probe with a hard-kill timeout and inspect the first delayed
  stage. Then wire the swing/QP task into the actual single-wheel controller
  path and require measured far-edge clearance plus safe touchdown before
  testing rapid balance recovery. Training remains stopped until those
  physical gates pass.

## 2026-10-09 instrumented 64-step replay after invalid-frame fallback

- GPU7 was rechecked before launch; only the user's `sleep.py` placeholder was
  present. It was stopped for this bounded diagnostic and restored afterward
  (PID 66532, about 10.6 GiB). No training, checkpoint write, or unrelated
  process change occurred.
- The instrumented probe completed in about 65 seconds and emitted per-step
  evidence. This confirms the earlier delay was initialization/observability,
  not a stuck physics loop.
- Result: `strict_any_crossing_verified=false`, `strict_crossing_count=0`,
  `strict_failed=true`, `max_commanded_leg_count=1`, and maximum tilt
  `0.463 rad`. Geometry collision steps were zero, but zero collision does not
  imply crossing: the selected wheel did not produce a measured far-edge,
  safe-touchdown event.
- The obstacle hold began at step 1 and hit its configured 32-step timeout.
  The selected wheel reached about 0.35 m world height early, then fell to
  about 0.08 m by step 32 while still near/over the obstacle envelope. The
  robot advanced only about 0.20 m over those 32 control steps, and tilt grew
  past the strict failure limit. The controller then changed the selected
  leg from 0 to 3; the invalid-swing fallback did not fire because both the
  obstacle hold and selected leg had already changed. Thus this replay does
  not validate the fallback fix.
- Root cause is broader than an invalid planner frame: the timed swing/hold
  expires before measured far-edge progress, while the one-leg lift and
  three-wheel support path allow severe body tilt. Extending the timeout or
  simply reusing a cached joint target would risk holding an unsafe pose and
  is not an acceptable fix. Next work must make swing progress/landing
  geometry-driven and stabilize the remaining support polygon with the
  approved WBC path; strict crossing remains the first acceptance gate, with
  original-balance recovery measured only after successful touchdown.
- Focused CPU tests and compile checks still pass (150 tests before this replay),
  but this is only controller regression evidence. No crossing capability or
  training readiness is claimed.

## 2026-10-09 strict crossing/recovery runtime gate wiring

The prior CPU test proved that `StrictCrossingTracker` separates a safe loaded
far-side touchdown from later recovery, but the production wrapper was wiring
the inputs incorrectly: it passed `touchdown_safe AND tilt/rate safe AND
nominal joint pose ready` as the crossing event's touchdown gate. This made
the runtime require recovery before recording the crossing, contrary to the
approved order.

- Added `split_crossing_and_recovery_gates`: crossing receives only the
  measured four-wheel loaded touchdown gate; recovery additionally requires
  recovered tilt/rate and nominal joint pose.
- Regression first failed because this runtime split helper was absent; after
  implementation the strict-crossing/landing/metrics/teacher focused suite
  passes **61 tests**, and changed runtime modules plus the probe compile.
  Scoped `git diff --check` passes. The physical probe now records per-step
  `strict_failed` so the first strict-failure transition can be correlated
  with swing/hold/contact samples.
- This corrects success accounting and phase ordering only; it does not repair
  the failed swing trajectory or support stability. The last physical run
  remains a strict failure (zero crossings, `0.463 rad` peak tilt). No new
  physical run or training was started in this checkpoint: a fresh GPU7 check
  found the user's placeholder plus another process (PID 88515, 3,194 MiB,
  100% GPU utilization). Neither process was touched.
- Next: make the production swing/landing progress depend on measured
  obstacle-relative motion, then integrate the approved support WBC and rerun
  the one-obstacle strict PhysX gate before any training.

## 2026-10-09 separate geometric lift release from touchdown ownership

The user clarified the priority: first complete the crossing and land safely;
restore the original balance promptly only after that. Inspecting the runtime
state flow exposed an additional landing deadlock: the strict crossing owner
stayed active until loaded touchdown, and the same boolean was also used as a
minimum-height lift lock. That could keep the wheel raised even after measured
top clearance and far-edge passage, preventing touchdown from being reached.

- Added a separate strict lift-hold predicate. It is released only after both
  clearance and far-edge latches are true; strict single-leg ownership remains
  active until the same wheel makes loaded touchdown.
- While descent is pending, phase progress is pinned at terminal touchdown
  instead of wrapping back into lift, the swing target tracks the measured
  safe-side XY point for vertical landing, and reduced support/swing wheel
  speeds remain in force until touchdown.
- The regression tests failed before the helper/API existed and pass after the
  runtime wiring. Focused suite: **69 passed**; Python compile and scoped diff
  checks pass.
- This fixes the touchdown transition logic only. There is no new PhysX result
  yet: GPU7 still reports 100% utilization and about 13.9 GiB in use, with a
  separate non-M1 process present. It was not interrupted. Training remains
  stopped; physical crossing, support stability, and recovery speed are still
  unverified.
- Follow-up CPU integration smoke now calls the production teacher adapter
  with a captured IK boundary and verifies the selected wheel targets its
  measured safe-side XY, lowers compared with the uncleared swing, and leaves
  the other three targets unchanged. Combined landing/strict-crossing tests:
  **41 passed**. This closes a coverage gap between the phase helper and the
  final IK target, but does not replace a GPU PhysX replay.

## 2026-10-09 align evaluation obstacles with the actual M1 wheel tracks

- Audit of the broad M1 CPU suite found four stale source-contract tests. Three
  were updated to test current safe behavior: preserve reduced wheel drive
  during an active teacher crossing, count the configured post-lift reserve
  call sites, and retain COM velocity from measured roll handoff through
  landing. The evaluation-layout assertion exposed a real mismatch rather
  than merely a stale assertion.
- The small-obstacle evaluator had six blocks on the body centerline at 0.8 m
  intervals and 0.10 m width, while training and the strict tracker use the
  shared six-obstacle profile on alternating wheel tracks at 0.55 m intervals
  with 0.05 m width. Evaluation now imports the shared M1 obstacle coordinates
  and diameter, so it exercises the same alternating single-wheel course as
  training.
- Test-first: the profile-alignment test failed before the evaluator edit,
  then passed. Full M1 CPU suite: **696 passed, 2 skipped**; touched runtime
  files compile and scoped diff checks pass. The optional USD/SDF test was
  excluded because the `amp` environment lacks `pxr`.
- Current host check found no M1 train/eval/probe process. GPU7 remains at 100%
  utilization (13,859 MiB / 24,564 MiB), so no PhysX smoke or training was
  started. The last physical teacher result remains the failed 64-step replay
  recorded above; crossing success, support stability, and recovery remain
  unproven.
- The newest checkpoint audit found
  `logs/rsl_rl/m1_cross_large_complex_ame/2026-10-05_18-53-03/5f94f14/model_0.pt`
  was saved at iteration 0 (`next_iter=1`) on Oct 5, with no later M1 checkpoint
  or active M1 run. It is an initialization snapshot, not evidence of learned
  crossing ability or resumed training progress.
- A numeric checkpoint scan found the latest trained candidate is
  `logs/rsl_rl/m1_cross_large_complex_ame/2026-09-30_18-46-39/3cd59cc/model_17802.pt`
  (`iter=17802`, `next_iter=17803`). Its actor/critic dimensions and AME
  architecture signature match the Oct 5 initialization checkpoint. Keep it
  as a candidate for a later strict PhysX replay, but do not call it successful:
  no current physical result proves crossing, loaded touchdown, or recovery.
