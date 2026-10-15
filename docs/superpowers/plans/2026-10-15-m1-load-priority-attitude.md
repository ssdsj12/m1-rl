# Load-priority attitude implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, with test-first checkpoints.

**Goal:** Restore usable support attitude authority without retracting underloaded support wheels, then verify actual 10cm crossing.

**Architecture:** One shared support offset and constrained zero-sum projection. Geometry produces an attitude preference; load reserve imposes directional limits before both velocity and position projections. Existing atomic execution transaction remains authoritative.

**Tech Stack:** PyTorch CPU tests, Isaac Sim isolated native probe, Python evidence audit.

## Task 1: bounded allocation math

Files: modify Go2Pvcnn/ame_baseline/m1_teacher_load_feedback.py; create Go2Pvcnn/tests/test_m1_teacher_load_priority_attitude.py.

- [ ] Write RED test using raw=[12,179,159,35], fractions=[.45,.43,.12], active=0, previous=0, dt=.02 and attitude=[0,-.02,-.02,.04]. Require RR velocity<0, no sum drift or bound violation. Detect missing optional keyword with inspect.signature assertion.
- [ ] Run CUDA_VISIBLE_DEVICES='' PYTHONPATH=.:tests:rsl_rl python -m pytest -q tests/test_m1_teacher_load_priority_attitude.py; record intended assertion failure.
- [ ] Add optional attitude_error_m=None; validate [B,4] dtype/device and zero active/zero support sum. Freeze nonfinite rows. New preference is -.0002*(target-measured)+.5*attitude; weak=(measured<45)|(target-measured>15), strong=(measured-target>15)&~weak. Intersect upper with0 for weak and lower with0 for strong.
- [ ] Integrate using existing _project, retaining the directional lower/upper also in the position projection via old+dt*lower/upper. Keep None path unchanged.
- [ ] Add balanced-load response, all active wheels, float32/64, invalid batch rows, saturation, long sequence, None equivalence tests. Run load_feedback/active_contact_load plus new tests; save exact logs.

## Task 2: geometry and transaction integration

Files: new ame_baseline/m1_teacher_attitude.py and tests/test_m1_teacher_attitude.py; modify ame_baseline/m1_reference_teacher.py and transaction tests.

- [ ] Test quaternion sign invariance, global translation/yaw equivariance, zero error when Rd=Rm, zero active/zero sum, mixed invalid row and first capture no impulse.
- [ ] Implement pure centered_support_attitude_error using rotation difference and support mean; no state inside module.
- [ ] In dynamic teacher branch compute e from goal body, measured body and preserved wheels; use work.get('support_attitude_error0',e), pass e-e0 to load proposal. Capture only in accepted transaction, clear on reset and restore completion.
- [ ] Add state lifecycle and rejection tests; secondpass keeps original capture; exact execution_fraction commits unified offset once. Keep active lift, body speed and heave unchanged.

## Task 3: independent evidence and native

Files: scripts/probe_m1_teacher.py, tests/test_m1_teacher_load_priority_attitude_evidence.py, notes/log/2026-10-15-m1-load-priority-attitude.md.

- [ ] Extend producer context and diagnostics with current attitude error/captured error/priority masks; independent recomputation rejects forged source history and mask, not only derived values.
- [ ] Bind context fields in complete replay, include nonzero secondpass/backtracked mixed cases. Run related regression suite and inspect output; never count canceled/full unavailable suites as passed.
- [ ] Perform independent final review and address blocking findings with RED/GREEN. Preserve old source archive; verify candidate SHA.
- [ ] Confirm no train/play/probe, GPU empty, acquire native kernel flock; launch exactly one first-obstacle 4env stage3 run in new output directory, not production. Read terminal exit/result/all episodes/video before claiming outcome.
- [ ] Archive evidence and compare SHA local/remote, update notes. If failure, use same-env ordered raw forces/target/FK/pose to select next action. Complete goal only for actual crossing and post-cross recovery.

Self-review: all spec modules mapped; Task1 is not deployment or goal completion. Steps retain original safety and exact success. No broad staging of historical dirty files; commits only with existing valid Git identity, otherwise record SHA.
