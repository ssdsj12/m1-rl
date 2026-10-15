# IK boundary step implementation plan

> Use superpowers:executing-plans inline, one fresh final reviewer.

**Goal:** Permit legal tangent progress at the existing knee boundary and test actual10cm crossing.
**Architecture:** Project candidate knee onto existing branch half-space before unchanged legality/improvement checks. No target or outer control change.
**Tech Stack:** PyTorch CPU tests, independent runtime probe, isolated Isaac.

## Task1 — numerical solver regression

Files: Go2Pvcnn/tests/test_m1_teacher_ik_boundary.py; tests/fixtures/m1_v25_boundary.json; ame_baseline/m1_teacher_ik.py.

- [ ] Extract raw123/126 q/target/branch directly from archived JSONL into a small provenance-marked fixture, no controls.
- [ ] Test old solver:
  result=solve_constrained_ik(q,target,branch,tolerance_m=q.new_full((1,4),.0001))
  assert result.valid.all()
  assert (result.residual_m<=.0001).all()
  assert ((result.q-q).abs()<=.05).all()
  ExpectedRED on result.valid for both frames.
- [ ] Add fourleg/dtype/configbound legal target roundtrips and invalidseed/unreachable refusal. Existing iterate-record test verifies monotonicity, .25 step and branch.
- [ ] Implement immediately after proposal=q+dq.flatten(1):

```python
        knee_sign=branch_q[:,2::3].sign()
        proposal[:,2::3]=knee_sign*torch.maximum(
            knee_sign*proposal[:,2::3],
            torch.full_like(proposal[:,2::3],cfg.min_knee_abs_rad))
```

- [ ] CPU command PYTHONPATH=.:tests:rsl_rl pytest -q tests/test_m1_teacher_ik_boundary.py tests/test_m1_teacher_ik.py; expectedallpass, record log. No commit without identity; source snapshot/SHA.

## Task2 — integration and review

Files: ame_baseline/m1_reference_teacher.py fingerprintonly.
- [ ] Replace support-ik-transaction-v25-support-translation-decoupling with support-ik-transaction-v26-ik-boundary-step.
- [ ] Run prior729 related suite plus boundarytests. Expected0fail; independent probe must replay same changedsolver while scalar executiongeometry remains unchanged.
- [ ] Fresh read-only reviewer. Review Focus: negative branch/configured tighter boundary, invalid seeds/nonfinite isolation, no candidate step enlargement, residual monotonicity/final labeling, encoding/slew/independent audit compatibility. FixC/I with RED/GREEN, minorsledger.

## Task3 — native

- [ ] Verify local/remotechangedruntimeSHA; no train/play/probe/GPUempty.
- [ ] Unique evidence-first-obstacle-ik-boundary-v1, same4env10cm first-obstacle slow-rolling/loadfeedback, kernel flock/logguard; never rerun on observationloss.
- [ ] Inspect terminalexit/result/all4audits/rawload/lift/cross/recovery/video; archiveSHA localremote. Failureslead nextdiagnosis, not relaxedcriteria.

Self-review: Task1solver→Task2fingerprint/replay→Task3physical. No incompatibleinterfaces. No production train. User chose directexecution; approval/handoff prompts waived within scope.
