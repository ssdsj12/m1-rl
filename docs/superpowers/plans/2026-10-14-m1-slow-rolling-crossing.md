# Slow rolling crossing implementation plan

> Execute inline with TDD and one independent review. User explicitly approved low-speed approach, rolling weight shift/lift, and recovery after passage; no repeated isolated preparation or approval gates.

**Execution status:** Implementation and bounded actual trial finished;229relatedCPU passed, independent P1 fixed.4×178nativeframes reach LIFT control but wheel remains loaded;1cm root tracking freezes progress,1approach protection lock/3peer interruptions. No actual crossing or recovery success. Native exit0/GPU released; source/video archive SHA and follow-up in [execution log](../../../notes/log/2026-10-14-m1-slow-rolling-crossing.md).

**Goal:** Teacher's normal crossing uses continuous 0.05m/s nominal wheel surface speed, not stop/start phases.
**Architecture:** Add opt-in slow_rolling TeacherConfig and explicit probe flag. Keep legacy mode for archived contracts. Ramp wheel commands at0.10m/s²; all active phases share measured forward-only support transport. Translate body anchor, goal, accepted reference and support origin coherently; never individually re-anchor wheels or absorb lateral slip. Capture while slowly moving, compare velocity against rolling target, retain measured support and physical gates. Physics/PD/reward/production/PPO unchanged.
**Tech Stack:** PyTorch teacher + isolated Isaac native probe.

## Decisions

- User's approval replaces historical fixed-world preparation anchors during forward rolling, but retains relative support geometry and measured slip evidence.
- Begin weight shift0.16m before old capture position so low-speed rolling has time to lift; no clearance/success relaxation.
- Normal wheel slew uses committed previous commands; protection failures may command immediate hold. Rejection must reset remembered wheel command to the actually issued hold.
- First bounded actual10cm trial remains1000steps; insufficient horizon is not crossing failure or success and must be reported as partial. Do not change training timeout.
- Existing dirty candidate and evidence remain intact. Changes stay isolated, no production/training/push.

## Task1: Tests and motion implementation

Files: Go2Pvcnn/tests/test_m1_teacher_slow_rolling.py; ame_baseline/m1_reference_teacher.py.

- [x] Add RED tests: initial wheel target<=.002, BALANCE/LIFT/PASS/RESTORE positive forward wheels, forward transport of all references before tracking/selection, no lateral drift absorption, yaw-rotated transport, rejected transaction does not commit transport.
- [x] Add TeacherConfig slow_rolling=False/rolling_speed_m_s=.05/rolling_accel_m_s2=.10/rolling_lead_m=.16; exclude bool from positive numeric validation, require true bool. New fingerprint.
- [x] In course slow mode, replace phase wheel choices with ramped target .05; capture on low relative velocity, not standstill. Translate prepared references by measured support common displacement projected onto locked heading before tracking and selection; exclude old PASS-only transport to avoid double shift.
- [x] Keep local diagnostic mode legacy; run new tests and previous213-related tests. Fix genuine regressions, not weaken safety assertions.

## Task2: Probe evidence and actual trial

Files: scripts/probe_m1_teacher.py; tests/test_m1_teacher_slow_rolling.py.

- [x] Add --slow-rolling and explicit TeacherConfig wiring in NativeProbe. Record config in source/hash and per-record as usual. Verifier readiness uses relative velocity in this mode.
- [x] Independent review covers monotonic forward command, slew, yaw, committed transport, reset/rejection, source selection and evidence replay.
- [x] Verify local/server SHAs and idle GPU; run --mode teacher --teacher-scope first-obstacle --slow-rolling --diagnostic-steps1000 with video (no isolated lift).
- [x] Read actual phase/force/collision/passage/recovery, wait native exit, archive source/tests/video/SHA, update notes. Do not infer actual motion or success from command alone.
