# Coherent support pose Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Direct-run authorization already supplied; no repeated approval.

**Goal:** Make selected support posture drive coherent XYZ leg geometry, then prove actual10cm crossing/recovery by isolated evidence.
**Architecture:** Opt-in coherent_support_pose bypasses captured-height/heave and indirect attitude preference, retaining load-only bounded offset and complete transaction safeguards.
**Tech Stack:** Python, PyTorch CPU tests, IsaacSim isolated GPU probe.
**Spec:** docs/superpowers/specs/2026-10-15-m1-coherent-support-pose-design.md.
**Constraints:** No production/train/PD/threshold/deletion/Git identity changes. SHA snapshots instead of commits. Existing worktree retained.

## Task1 — teacher transaction
Files Go2Pvcnn/ame_baseline/m1_reference_teacher.py; tests/test_m1_teacher_coherent_support.py.
Interface produces TeacherConfig.coherent_support_pose bool and real full-XYZ transaction; legacy false unchanged.
- [ ] RED tests use frozen v34 fixture via frozen_teacher(), replace cfg coherent_support_pose=True; invalid nonbool and missing dependencies reject. Valid step exposes height_enabled/heave_enabled/attitude_enabled=0 while load_enabled=1; accepted q slew<=.05 and residual<=.0001. Mutation: old height/attitude branch accidentally active.
- [ ] Run pytest -q tests/test_m1_teacher_coherent_support.py. Expected missing config failure.
- [ ] Add field false, exclude boolean from numeric validation, strict bool/dependency validation:
```python
if type(self.coherent_support_pose) is not bool or (self.coherent_support_pose and not self.bounded_crossing_attitude):
    raise ValueError('coherent support requires bounded crossing attitude')
```
Bounded mode already requires rolling/load. Update fingerprint implementation v36.
- [ ] In _feedback_transaction retain offset context unconditionally for load_feedback, move height/origin/heave block under `if not self.cfg.coherent_support_pose:`. No execution builder rewrite.
- [ ] In dynamic load proposal use `attitude_delta=None` for coherent mode and don't compute/store attitude history. Old branch computes exact olderror/e0 and diagnostics. Pass attitude_error_m=attitude_delta into same load function.
- [ ] Tests add full transaction support goal independent scalar Rd^T*(wheel-commandposition)+Rm^T*load, active measured transform, duplicate/rollback/RESTORE/reset. Use recorded transaction output, not spy-only assertions.
- [ ] Run new + bounded transaction + loadfeedback + execution-target suites. Preserve SHA and terminal command/result in ledger.

## Task2 — probe propagation / independent audit
Files Go2Pvcnn/scripts/probe_m1_teacher.py; tests/test_m1_teacher_coherent_evidence.py.
Interface consumes exact Task1 flag in parser/config/NativeProbe/source/runtime verifier.
- [ ] RED CLI parse --coherent-support-pose plus prerequisites, factory cfg roundtrip and dependent source fingerprint; legacy missing option remainsfalse.
- [ ] Thread bool through existing bounded option callsites and serialized config. No inferred activation.
- [ ] RED independent coherent execution audit rejects producer/replay shared substitution of legacy height goal.
- [ ] Audit coherent raw frame using independently scalar quaternion rotation, selected fullcommand geometry and chosen load offset plus beta. Verify missing legacy heights is intentional only coherent config; reject unexpected legacy history or silently different flags. Existing helpers handling absence ofheight cannot alone certify coherent path.
- [ ] Run new evidence + all1024 relevant existing tests, barepytest collection with limitations named. No task completion while tests unrun.

## Task3 — review and isolated actual test
- [ ] Prepare scoped delta against v35 SHA snapshots and exact test results. One fresh reviewer; Important/Critical RED/GREEN fix pass.
- [ ] Verify no live train/native/pytest and idleGPU. Archive candidate v35 runtime and SHA, deploy only reviewed changed files.
- [ ] Run unique evidence-first-obstacle-coherent-pose-v1 with --slow-rolling --load-feedback --bounded-crossing-attitude --coherent-support-pose --teacher-scope first-obstacle --diagnostic-steps1000 --headless --devicecuda:0 --enable_cameras under originalflock.
- [ ] Pollsame livehandle untilterminal; inspect sameenv input/command/load/actualwheelbottom/overlap/recovery and video, immutablearchiveSHA.
- [ ] No CPU, probeexit0, predictedreserve or partialepisode counts as success. Goal requires physical passage/restoration.

## Review focus
Full rigid geometry not split XYZ; load correction only once; baselineownership/rollback/reset; legacyexact; RESTORE level; independentauditor notsame-helper tautology; actualsafety neverpredicted.
Self-review: task1 bool consumedtask2, task3 requiresbothgreen. No feature outside isolatedteacher. No repeatedapproval or defaultactivation.

