# Rolling lift/body tracking decoupling implementation plan

> Execute inline in the existing isolated worktree; user explicitly approved implementation. TDD and independent code review before direct native obstacle validation, no repeated approval or isolated support fixture.

**Goal:** slowrolling LIFT/PASS can progress under real support safety even while body position tracking is correcting.
**Architecture:** Keep _tracked and1cm body reference advancement. Split angular tracking for reuse, compute independent wheel_progress from current three support loads/tangential ratio, measured COM>=10mm and original relative attitude<=.15rad. Use wheel_progress for lift_age, LIFT/PASS transitions and wheel-reference advancement; body_age/body interpolation still depend on tracked. BALANCE and RESTORE untouched. Add named diagnostic booleans for the two independent decisions. Default legacy/local scopes unchanged.
**Tech Stack:** PyTorch teacher and isolated Isaac native probe.

## Approved boundary

No PD/reward/training/environment changes. Forward-only transport,0.05m/s rolling, approach-unready protection, raw collision failure, IK2mm/joint target slew, atomic rollback remain. Progress never means success: LIFT->PASS still requires measured wheel bottom above obstacle, PASS->RESTORE actual far side, final recovery unchanged. Low COM/attitude pauses wheel progress; actual lost support retains existing failure lock. No new timing or safety thresholds.

## Tasks

- [x] Add tests in Go2Pvcnn/tests/test_m1_teacher_lift_decoupling.py. Real prepared fixture, +.015m body position error, physically valid support/COM: LIFT and PASS must increase lift_age and requested wheel Z while body_age/body reference remain fixed. Test unsafe COM/attitude, actual support loss/collision, unchanged BALANCE/RESTORE/legacy, clear/no-clear transitions, IK rejection with no commits, next-step retry and reset.
- [x] Watch targeted tests RED against current ac4abb7 teacher; no physical false success fixture.
- [x] Modify only Go2Pvcnn/ame_baseline/m1_reference_teacher.py: helper _attitude_tracked; crossing_ready derived from measurements; independent progress/counters/target freeze. Add body_tracking_ready and wheel_progress_ready to named integer diagnostic schema and evidence. Update implementation fingerprint.
- [x] Run new tests plus existing six-file229 suite using CPU server Python, explicit PYTHONPATH=.:tests:rsl_rl and CUDA_VISIBLE_DEVICES empty. Expected all pass, no broad expensive archive tests.
- [x] Independent reviewer reads new tests/changes/this plan and previous trace diagnosis; repair Important before native.
- [x] Verify source SHA and no active GPU task, run scripts/probe_m1_teacher.py --mode teacher --teacher-scope first-obstacle --slow-rolling --diagnostic-steps1000 --headless --device cuda:0 --enable_cameras in candidate only, unique evidence-first-obstacle-lift-decoupled-v1 output.
- [x] Wait completion, inspect actual wheel bottom/loads/phase/near-side and recovery, archive runtime/tests/videos and SHA; update notes with actual result. Do not start PPO/BC or deploy production on software-only success.

## Core transition pseudocode

```python
wheel_progress = crossing_ready if rolling and phase in (LIFT, PASS) else tracked
if tracked:
    body_age += phase != RESTORE
if wheel_progress:
    age += 1
    lift_age += phase in (LIFT, PASS)
alpha = 1 / remaining if tracked else 0
if not wheel_progress:
    wheels_goal = accepted.wheels_w
```

For BALANCE/RESTORE wheel_progress==tracked, preserving prior behavior. Crossing readiness is recomputed after transitions so entry to LIFT uses the measured ready sample. All counters are scratch and discarded after IK/action failure.

## Result

243 related CPU tests pass; independent review closed. v1 initialization blocked before control, stopped with preserved evidence; same-config v2 completed4×125frames. Independent lift progress observed6frames, but target remains grounded and RR load falls below30N;1support lock3peer interruptions, no crossing. Extra minimal probe verifier prefix correction required after native exposed wheel_progress_ready being incorrectly included in pure transaction replay; RED/GREEN + review complete. Frozen4records reverified without errors, allsuccessfalse. No production/BC/PPO. Detailed evidence in notes/log/2026-10-14-m1-rolling-lift-decoupling.md.08:59:51Z no active task/GPU1MiB.
