# Bounded support heading implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, task-by-task.

**Goal:** Restore bounded yaw response in load-aware support execution, preserving actual crossing and recovery standards.
**Architecture:** Small pure geometry helper transforms only support XY before existing interpolation/IK; evidence is independently reconstructed.
**Tech Stack:** Python/PyTorch, pytest CPU overlay, isolated Isaac probe.
**Spec:** docs/superpowers/specs/2026-10-15-m1-bounded-support-heading-design.md

## Global constraints
Cap .05rad, mode1+height only; exact support world Z and active goal preservation; original IK/rate/branch/nominal gates. No production training, PD/wheel/std change, deletion or live candidate overwrite.

## Review focus
- Quaternion wrap/invalid inputs: Task1 tests.
- Mixed active legs/modes/dtypes and missing height: Task1 tests.
- Exact active and world-Z preservation: Task1 tests.
- Compatibility with active intent/refinement and rollback: Task2 real-frame tests.
- Independent evidence tampering: Task2 tests.

## Task1 — Geometry and RED/GREEN
Files: new ame_baseline/m1_teacher_support_heading.py; m1_teacher_execution_targets.py; tests/test_m1_teacher_support_heading.py.
- [ ] Save exact baseline files and immutable v30 selected-frame fixture after final source hash verification.
- [ ] Write tests calling existing execution_targets: desired yaw perturbation must yield correct signed support XY response, world Z and active unchanged. Run RED before helper.
- [ ] Implement support_heading_goal(goal, measured_quat, command_quat, active, enabled) returning (goal, delta), finite quaternion validation remains upstream. Wrapped yaw via atan2 of rotation forward-axis components; clamp .05. Rotate measured-world-relative support vectors, preserve Z, inverse transform.
- [ ] Add heading_delta optional zero tensor to ExecutionTarget; apply helper only mode1 with height before start/interpolation. Preserve invalid goal.
- [ ] Run targeted tests across float32/64/all4legs/modes/wrap/saturation/equivariance; assert exact disabled values and no nonfinite acceptance.

## Task2 — Integration and evidence
Files: m1_reference_teacher.py, scripts/probe_m1_teacher.py, same tests plus existing support_translation tests.
- [ ] Add execution_heading_delta diagnostic and v31 fingerprint; no state/history changes.
- [ ] Independent verifier computes heading from raw quaternion formula, applies same specified geometric map without producer helper, checks diagnostic and existing goal/step/FK.
- [ ] Add RED tamper tests for delta/support XY/Z; make them GREEN by independent checks.
- [ ] Replay actual115/120/125/128/134; require valid and original residual/rate/nominal contract, preserve active target.
- [ ] Update old yaw-insensitive expectations to explicit bounded heading; do not weaken tilt translation tests.
- [ ] Full previous840 selection plus new tests; fix regressions with evidence.

## Task3 — Review and actual10cm
- [ ] One fresh final review against exact baseline; one C/I RED/GREEN correction pass and regression, ledger minor findings.
- [ ] Verify v30 terminal, archive all source/evidence/config/video and local/remote SHA.
- [ ] Deploy only candidate changedfiles, verify SHA and GPU/kernel lock; unique slow-rolling first-obstacle10cm native, no production training.
- [ ] Read complete actual lift/cross/recovery and video; archive result. Keep goal open unless full objective proven.

## Self-review
All spec requirements map to tasks. Diagnostic fields are default tensors for merges. No new recovery behavior. Native remains gated by terminal archive and CPU/review. User authorized direct execution; no repeated approval or Git identity mutation.

