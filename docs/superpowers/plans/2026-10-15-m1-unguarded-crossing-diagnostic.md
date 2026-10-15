# Unguarded crossing diagnostic implementation plan

> Execute inline with superpowers:executing-plans. Direct-run approval already supplied; preserve SHA evidence instead of commits in dirty isolated worktree.

**Goal:** Observe actual10cm lifting/crossing without controller physical-safety gates, without changing physics or falsifying evidence.
**Architecture:** Explicit default-false `unguarded_diagnostic` propagated through teacher and isolated probe. Numerical validity and hard actuator limits remain. Raw physical state and strict verifier remain untouched.
**Tech:** Python/PyTorch CPU tests; isolated IsaacSim native.

## Task1 — teacher opt-in

Files `Go2Pvcnn/ame_baseline/m1_reference_teacher.py`, `Go2Pvcnn/tests/test_m1_teacher_unguarded.py`.
- [ ] RED configuration strict bool and coherent-mode prerequisite; default false.
- [ ] RED frozen coherent transaction with `s.collision[:]=True`, weak support `s.wheel_force_w[:,3,2]=20`, unsafe COM or tilt: default refuses/freezes, diagnostic may produce valid motion while inputs remain unchanged. Invalid quaternion/NaN still refuses.
- [ ] Implement strict flag and fingerprint, bypass only physical-control gates. Collision and SUPPORT_LOST early returns use `and not cfg.unguarded_diagnostic`; APPROACH_UNREADY likewise. Preparation capture permits `was_balancing` without bearing/quiet gate. Readiness/tracking control decisions bypass without modifying measured diagnostic values.
- [ ] In dynamic lift newmode uses existing fixed `measured_lift_rate_m_s*dt` increment up to physical lift ceiling, not support-reserve/lead throttling. Preserve raw reserve calculation as diagnostics. Load-proposal invalidity must not veto lift but must keep finite previous load correction, not fabricate force data.
- [ ] Retain valid reachable pose/IK, finite encode, hard joint/torque limits and measured clearance/past-obstacle transition geometry. RESTORE must still prove actual recovery; diagnostic mode must never fabricate receipts to progress or report success.
- [ ] Run new tests, coherent/recovery/legacy regressions. Record RED/GREEN and SHA.

## Task2 — probe and physical termination boundary

File `Go2Pvcnn/scripts/probe_m1_teacher.py`, new tests `Go2Pvcnn/tests/test_m1_teacher_unguarded_evidence.py`.
- [ ] Add CLI `--unguarded-diagnostic`, reject acceptance/course/production use; explicitly propagate to config/factory/NativeProbe/source.
- [ ] RED `DiagnosticBatchGate` test raw support/collision/penetration does not latch physical stop in newmode, but action evidence/NaN corruption still does. Keep sample raw booleans unchanged.
- [ ] Inspect wrapper/termination flow before editing: native mode must prevent physical reset while continuing to compute/log original termination flags and budgets. Do not clear failure data or pass fake inputs. Add targeted tests against the actual interception boundary; do not merely mask post-reset done.
- [ ] Ensure fixed diagnostic horizon still ends; all artifacts marked diagnostic-only and not student-demonstration-usable. Existing strict verification rejects unsafe outcomes, independent of execution continuation.
- [ ] Add CLI/serialization/dynamic replay and raw-flag negative tests. Relevant fullsuite and explicit barecollection limitations.

## Task3 — isolated actual evidence

- [ ] One final scoped review and C/I repair, exact SHA archive. No changes to production.
- [ ] Verify no live native/train, idleGPU, kernel lock; snapshot currentv36 candidate and deploy reviewed files only.
- [ ] Unique prefix `evidence-first-obstacle-unguarded-v1`, same10cm terrain and4env, maximum1000steps with all current coherent flags plus newflag.
- [ ] Watch original run handle, no duplicate. Inspect actual wheelheight, collision, loading, body/joint tracking and recovery even if physicalfailure occurs. Archive original full trace/video/source/result with local/remote SHA.
- [ ] Report actual passage separately from strictsuccess. No training restart.

Self-review: unresolved exact environment termination interception must be inspected during Task2 before implementation; this is a known investigation step, not permission to fake evidence. All requested gate categories mapped; hard numerical/physics limits explicitly excluded in user-facing scope.
