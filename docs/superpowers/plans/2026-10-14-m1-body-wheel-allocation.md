# Body/wheel allocation implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline. User explicitly prioritizes direct actual obstacle iteration over repeated isolated preparation/approval gates.

**Goal:** Correct actual first-obstacle tracking without rolling the waiting wheel into the obstacle.
**Architecture:** Keep capture-continuity repair; replace unsuccessful anchor-X common-wheel experiment. Teacher position PI is XYZ virtual body displacement through constrained leg IK; wheel speeds are phase nominal/yaw only. X uses existing YZ position gains/bounds, never reinterprets m/s as meters. One position feedback state survives phases and decays in approach.
**Tech Stack:** Python/PyTorch; Isaac Lab isolated candidate.
**Spec:** Approved actual-crossing direction and failure evidence in [log](../../../notes/log/2026-10-14-m1-obstacle-anchor-feedback.md).

## Global constraints

10cm actual first obstacle, fixed anchors, measured support/readiness, IK2mm, joint slew2.5rad/s, physical parameters and rewards unchanged. XYZ position PI Kp.5/Ki.5, integral.01m, output.02m, slew.02m/s. No production/BC/PPO; no concurrent native. Completed crossing and recovery, not preparation alone, is the goal.

## Review focus

- X correction must rotate with captured yaw.
- Drift correction must not change nominal wheel commands.
- Invalid IK/decoder must not commit any PI state.
- Phase transitions/reset retain/clear consistent meter units.
- Evidence replay must encode the same wheel commands as runtime.

### Task 1: Coherent position allocation and counterexamples

Files: teacher_feedback.py, teacher_pose.py, reference_teacher.py, probe_m1_teacher.py and feedback tests under Go2Pvcnn.

- [x] Add real Teacher drift counterexample: root +.03m while wheels remain anchored; accepted physical progress frozen, virtual X negative, nominal zero wheels stay zero, joint slew <=.05rad.
- [x] Observe RED against anchor-X candidate.
- [x] Add BodyFeedbackConfig inheriting existing validation, all XYZ position bounds; select_integral accepts explicit config. Keep legacy pure math defaults for historical callers.
- [x] Add explicit body_x flag to feedback pose/backtrack; runtime supplies true. Remove unsuccessful anchor-X substitution/common wheel correction. Probe reconstructs BodyFeedbackConfig and uses nominal wheel speeds.
- [x] Run related CPU tests; update old wheel-feedback expectations only where contract intentionally changed. Check yaw, atomic failure, phase/reset, replay.
- [x] Self-review diff; candidate remains uncommitted until actual evidence, not falsely released.

### Task 2: Actual obstacle and records

- [x] Check no active native/training; copy scoped files to isolated candidate, verify SHA.
- [x] Run first-obstacle10cm4env bounded1000steps with video, no isolated lift fixture.
- [x] Locate earliest physical/control failure or actual crossing receipts and recovery; no gate bypass.
- [x] Wait bounded probe exit, archive/check SHA and GPU release. Update notes with honest result; no automatic production/training.
