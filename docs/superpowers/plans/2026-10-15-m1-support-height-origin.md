# Support height origin implementation plan

> Use superpowers:executing-plans inline; one final fresh review before native.

**Goal:** Remove measured vertical collapse-following from support execution, then verify real10cm crossing/recovery.
**Architecture:** Optional capture-origin execution transform; teacher atomic origin history; independent evidence reconstruction and bounded RESTORE handover.
**Tech Stack:** Python/PyTorch CPU tests, isolated Isaac native.
**Spec:** docs/superpowers/specs/2026-10-15-m1-support-height-origin-design.md

## Global constraints
No production training. Preserve .1mm execution/.05rad step/30Nsupport, existing geometry,heave/load/PD/wheel/recovery. No live overwrite, no evidence deletion. Legacy calls unchanged.

## Review focus
Origin paired history cannot partially commit; RESTORE coordinates must not double-count delta; active leg unchanged; batch/device/dtype isolation; independent audit must reject forged origin. Tests in tasks1/2.

## Task1 — Execution geometry
- [ ] Add tests/test_m1_teacher_support_height_origin.py before code:4active×2dtype×2mode root translation invariance for support, active follows measured transform; zero-delta legacy exact; invalid shape/dtype/nonfinite/missingheight/mode0; mixedbatch.
- [ ] Run RED for unsupported keyword support_capture_root_z.
- [ ] Add optional support_capture_root_z[B] in ame_baseline/m1_teacher_execution_targets.py; effective height = stored+measuredZ-origin before existing vertical adjustment, only support legs. Validatefinite matching reference.
- [ ] Run new tests and existing execution/supportheight/heave/heading tests. Optional path is not yet production-integrated.

## Task2 — Atomic integration and audit
- [ ] Extend pose backtrack keyword support_capture_root_z and pass unchanged to each candidate.
- [ ] Teacher captures origin paired with height only on final successful commit, restores geometry in origin coordinates, clears onfinish/reset; fingerprintv33; explicit diagnostic capture/proposed/committed origin.
- [ ] Probe context/replay and independent height/execution audit reconstruct measuredZ-origin separately; bind dynamicpre history and detect forged/missing evidence.
- [ ] Write RED tests for firstcapture, rollback,encode rejection,mixed reset,RESTORE continuity and completeclear; forgedorigin rejected, producererror rejected. Preserve oldfixtures through explicit testing transitions, not silenthistoryfallback.
- [ ] Full927+newtests and barepytest; record known dependency errors, one final fresh review C/I onefixpass.

## Task3 — Physical validation
- [ ] Verify v32archive SHA/terminal; deploy reviewed files only with SHA, no concurrentnative/train and GPUcheck/flock.
- [ ] Unique first-obstacle10cm slowrolling/loadfeedback4env video probe; preserve original source/trace/result/exit.
- [ ] Inspect actual crossing/recovery; if failure diagnose rather than relax standards. Goalcomplete only full user outcome.

Self-review: Task1 optional interface feedsTask2; no independently deployed partial path. Directrun authorization, no repeatedapproval. NoGitidentity changes; baseline snapshots replace commits.
