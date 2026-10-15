# Active-contact load Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox tracking.

**Goal:** Correct active-contact moment allocation, then test actual 10 cm crossing without weakening safety.

**Architecture:** Required measured wheel geometry supplies the active contact affine coordinates. Existing bounded load feedback consumes corrected target; teacher and independent probe bind the same raw frame.

**Tech Stack:** Python, torch, pytest, isolated Isaac native probe.

Spec: docs/superpowers/specs/2026-10-15-m1-active-contact-load-design.md. Paths below relative to this isolated worktree. Preserve prior evidence, no production/BC/PPO changes. User authorized continuous inline execution. Missing Git identity: retain dirty files and SHA, no invented author/commit. Preserve evidence workspace.

### Task 1: Correct transitional allocation

Files: Go2Pvcnn/ame_baseline/m1_teacher_load_feedback.py; tests Go2Pvcnn/tests/test_m1_teacher_active_contact_load.py and test_m1_teacher_load_feedback.py.

- [ ] RED rectangle: forces [60,100,100,100], active0, fractions [.4,.4,.2], supports FR/RL/RR, affine [1,1,-1]. Expected target [84,84,132], not [120,120,60]; sum300, combined moment targetCOM*360. Run CPU pytest active-contact file; expected assertion failure on old target.
- [ ] Implement required wheels_w keyword, same shape/dtype/device validation; tripod_load(active point,wheels,active,ones) for affine geometry. Compute `desired=normalized*(S+A)-A*affine`, project45..S sumS. Freeze invalid rows. Append unprojected_fz,active_affine,moment_residual_xy to LoadProposal. Residual is `sum((target-desired)*(supportXY-supportXY0))`, units N*m. Mask diagnostics on invalid rows.
- [ ] Add cases all4active, float32/64, translations/rotations, active0force, projectedbounds, NaN/degenerate rowfreeze, dtype/device/shape rejection, original longfloat32sequence. Update original api test adapter to supply measured rectangle geometry, not omit validation.
- [ ] Run both pytest files; expected all pass; retain output and SHA.

### Task 2: Bind teacher and independent evidence

Files: Go2Pvcnn/ame_baseline/m1_reference_teacher.py, Go2Pvcnn/scripts/probe_m1_teacher.py, Go2Pvcnn/tests/test_m1_teacher_load_feedback_evidence.py.

- [ ] RED required geometry teacher call fails until updated; add audit tests for forged unprojected/affine/moment/activeforce/rawwheel fields.
- [ ] Teacher passes `wheels_w=measured.wheels_w`; record new load diagnostics unprojected_0..3,affine_0..2,moment_x/y,active_fz; default0 in RESTORE. Fingerprint v22-active-contact-load.
- [ ] Independent scalar affine: supportrelativeXY u=p1-p0,v=p2-p0, t=active-p0; det=ux*vy-uy*vx, b1=(tx*vy-ty*vx)/det,b2=(ux*ty-uy*tx)/det,b0=1-b1-b2. Require all coordinatesfinite and absdet>1e-10. Use raw preparation_input wheels, validate feedback measured_wheels matches. Compute corrected allocation and projection; compare each new diagnostic. Do not call controller helper.
- [ ] Run loadtransaction/evidence and all heightTests plus heave tests; expected all pass with IK/finalencode failure rollback/reset/restore unchanged.

### Task 3: Review and unique physical experiment

- [ ] One fresh-context reviewer for whole v22 delta and spec, independent load audit/float32/invalidgeometry/transaction edge cases. Important fixes RED/GREEN then full suite. No second reviewer.
- [ ] Verify candidate runtime SHA, no training/native jobs and GPU empty. Use existing v21 launch parameters but unique v22 evidence output and fingerprint; never rerun v21 command/output. Kernel flock preserved,4env seed101 first10cm.
- [ ] Read completed exit, all episode JSONL audit/force/activewheel bottom/overlap/recovery and videos. Archive with matching SHA and update notes. Only full crossing+recovery is goal completion; failure remains new diagnostic progress, no production start.

Self-review: same source geometry in producer/auditor; negative affine allowed, negative lambda forbidden. Projection residual explicit. Single mechanism, heave/PD/rate/safety unchanged. All spec requirements covered above.
