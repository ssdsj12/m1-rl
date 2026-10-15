# Support translation decoupling implementation plan

> **For agentic workers:** use superpowers:executing-plans inline; one fresh review at end.

**Goal:** Remove orientation-induced opposite lateral support commands while preserving actual crossing/recovery evidence.
**Architecture:** Only mode1+support height uses measured orientation for support translation. Existing separate Z authority and transaction remain unchanged.
**Tech Stack:** PyTorch pure tests, independent probe audit, isolated Isaac native.

## Task1: execution geometry

Modify Go2Pvcnn/ame_baseline/m1_teacher_execution_targets.py. Add Go2Pvcnn/tests/test_m1_teacher_support_translation.py.

- [ ] Write parameterized RED (4active×2dtype): nonzero measured quaternion and command translation; call existing execution_targets with support_reference_w_z; transform result back with measured pose and assert support XY equals command.wheels+measured.pos-command.pos, while active equals measured-frame wheel target. Assert height/heave/load Z and start+fraction*(goal-start). Mode2/without height stay legacy.
- [ ] Run CPU pytest test_m1_teacher_support_translation.py, expected FAIL geometric XY, not import.
- [ ] After validated support_reference, implement:

```python
support=torch.arange(4,device=pos.device)[None]!=active_wheel[:,None]
translation=world_to_goal_body(PoseReference(BodyPose(command.body.pos_w,measured.quat_w),command.wheels_w))
goal=torch.where((support&(mode[:,None]==1))[:,:,None],translation,goal)
```

Import BodyPose. No other geometry branches change. Existing vertical override runs after this.
- [ ] Run new tests plus execution_targets/support_height/load_feedback_transaction. Expected all pass. Record exact log; no commit without configured identity.

## Task2: evidence audit and integration

Modify Go2Pvcnn/scripts/probe_m1_teacher.py, ame_baseline/m1_reference_teacher.py; add evidence tests in new testfile.

- [ ] Add nonzero attitude sample using real load_teacher/advance and probe observers. Original independent execution audit should fail after Task1 until formula fixed.
- [ ] In verify_execution_geometry after goal=transform(command), for mode1+load_feedback use Rm.T*(wheels-command.pos), then active=transform(measured). Preserve all subsequent height/heave/load, fraction, residual and encoded checks.
- [ ] Fingerprint replace v24-load-priority-attitude with v25-support-translation-decoupling.
- [ ] Add tampered execution goal/step rejection and RESTORE unchanged roundtrip. Run full related suite plus new tests; expected0fail. Review Focus: mixed mode batches, nonfinite poses, actual vs goal orientation use, no double fraction/capture, independent audit/source binding, recovery transition.
- [ ] One fresh independent review; any Important/Critical RED/GREEN then full suite. No native before final review.

## Task3: isolated physical verification

- [ ] Copy only changed candidate runtime/tests, verify SHA local/remote; preserve v24 full archive.
- [ ] Check no train/play/probe and GPUempty; kernel flock; unique evidence-first-obstacle-translation-decoupled-v1, 4env stage3 first-obstacle/slow-rolling/load-feedback. Never rerun launch on observation failure.
- [ ] Read terminal result, exit, all episode audits, actual support/lift/cross/recovery/video; archive with matching local/remote SHA. Failure is not completion; use same-env failure sequence for next action.

Self-review: Task1formula feedsTask2scalarrecompute; mode1implicit gate exactly cfg.load_feedback+height at caller, mode2legacy. Task3 cannot count CPUgreen as physicalsuccess. User continuous authority selected inline, no extra choice prompt.
