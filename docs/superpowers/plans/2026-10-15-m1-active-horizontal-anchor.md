# Active horizontal anchor implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Inline execution, one final independent reviewer.

**Goal:** Correct stale active XY at first rolling LIFT; prove actual crossing separately.
**Architecture:** Scratch-only active anchor capture, existing bounded actuator transaction, independent raw-history audit.
**Tech Stack:** Python/PyTorch/pytest/IsaacLab.
**Spec:** ../specs/2026-10-15-m1-active-horizontal-anchor-design.md

## Global Constraints
No production training; no old evidence deletion; no PD/geometry/safety relaxation; .05rad at20ms and .1mm execution residual retained; v33 archive immutable. No Git identity/commit/push; SHA baselines.

## Review Focus
- Transaction rejected after successful IK: no anchor or phase leak (Task1).
- Repeated step/retry: exactly one successful capture with current input (Task1).
- Other rows/legs: no accidental support anchor motion (Task1).
- Already LIFT/PASS and legacy: no recapture (Task1).
- Shared producer/replay defect: raw independent audit rejects forged capture (Task2).

### Task1: Lifecycle capture
Files: ame_baseline/m1_reference_teacher.py; tests/test_m1_teacher_active_horizontal_anchor.py under Go2Pvcnn.
Consumes TeacherState.wheel_pos_w and existing scratch work; produces one-time wheel_anchor change, no API change.
- [x] Write real transaction tests for firstcapture/support preservation, duplicate, laterphase, rejection/retry, legacy.
- [x] Run new file against v33 CPUoverlay, expect capture assertion FAIL not importerror.
- [x] At original preparation transition copy activeXY only in authorized mode. Upgrade fingerprint.
- [x] Run newfile plus existing reference/load/lift tests, expect pass; recordSHA.

### Task2: Independent evidence
Files: scripts/probe_m1_teacher.py; tests/test_m1_teacher_active_horizontal_anchor_evidence.py.
Consumes dynamic raw pre/input/post; produces independent failure strings joined into existing outerverification.
- [x] Tests reject forged active capture, support snap, recapture, rejected-state mutation, including shared-producer defect.
- [x] RED then implement scalar history checks, GREEN.
- [x] Full relevant prior962 + newfiles:985passed312.94s; barecollect13knownerrors. Single final review Important fixed with RED/GREEN before deployment.

### Task3: Isolated physical verification
- [x] Archive/recheck v33, compare runtimeSHA, verify idle GPU/no native/train.
- [x] Unique v34 run under existingflock, actual10cm first-obstacle path:runner428984 at2026-10-15T00:40:59Z. Do not duplicate live PID.
- [x] Read trace/video/result/exit, preserve archiveSHA ba2001283bbc209910d865bdeef8280685ecef290179ffceb2f6d377ce3168db. FAILED_DIAGNOSTIC/0success; next evidenced diagnosis is support-orientation candidate/execution consistency. Objective remains unachieved.

Self-review: Task2 consumes Task1 transition with unchanged state schema, fingerprint binds semantics. Tests cover all five review risks. No requirement changes or safety substitutes.
