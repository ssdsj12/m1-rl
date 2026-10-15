# Active intent atomic commit implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline, task-by-task. Preserve all artifacts; explicit user authority permits isolated deployment without repeated approval.

**Goal:** Remove proven shared-beta attenuation of feasible lift intent while keeping physical reference, command reference and execution evidence consistent.

**Architecture:** Keep the existing support transaction as immutable baseline. A bounded active-only refinement returns a new whole FeedbackReferenceStep only when nominal IK, assembled execution IK and original callback pass. Explicit intent_fraction records reference interpolation separately from support fraction and active execution fraction.

**Tech Stack:** Python/PyTorch, pytest CPU overlay, isolated Isaac native probe.

Spec: `docs/superpowers/specs/2026-10-15-m1-active-intent-commit-design.md`.
Workspace: `.superpowers/sdd/2026-10-15-m1-active-intent-commit`.
Runtime changes remain local/CPU overlay until old native381180 is terminal and archived. No training, PT deletion, threshold relaxation, global configuration or unrelated changes.

## Task 1: Real-frame RED and preserved baseline

Files: `Go2Pvcnn/tests/test_m1_teacher_active_intent.py`, `tests/fixtures/m1_v29_active_intent.json`.

- [ ] Copy verified fixture SHA49d0a974121eca34661abbd96c69c993a27a43fbefb9d061e2e9180e6d10ca0a without editing its values; copy current runtime into this plan workspace for exact final review.
- [ ] Test real frames125/128 by unpacking dynamic_support input/pre, creating ReferenceTeacher with fixture config and invoking `_step_row`. Require valid result and accepted active worldZ equal original dynamic_requested_z within1e-6; current code should fail on >.1mm attenuation. Frames129/133 unchanged request must remainvalid;134 must remaininvalid.

```python
assert bool(out.valid[0])
requested = row['teacher_diagnostic']['dynamic_requested_z']
accepted = teacher._rows[0]['accepted'].wheels_w[0, row['active_wheel'], 2]
assert abs(float(accepted)-requested) <= 1e-6
```

- [ ] Run `/opt/conda/envs/env_issacsim/bin/python -m pytest -q tests/test_m1_teacher_active_intent.py` from CPU overlay with OMP_NUM_THREADS1. Expected2RED on active-reference assertion, unchanged controls pass. Record exact failures before implementation.

## Task 2: Atomic active refinement

Files: new `ame_baseline/m1_teacher_active_intent.py`; modify `m1_teacher_pose.py`, `m1_teacher_execution_targets.py`.

- [ ] Add `ExecutionTarget.intent_fraction` defaulting to cloned fraction, preserving old positional construction and dataclass merge behavior.
- [ ] Implement `improve_active_intent(step, accepted, requested, measured, active, last_applied, q_seed, branch, dt, cfg, validator)`; only mode1, step.valid rows with nonzero active request and support beta<1 qualify.
- [ ] For eight coarse gamma=2**(-attempt), then four bisection refinements, alpha=baseline_beta+(1-baseline_beta)*gamma. Candidate active physical wheel = accepted + alpha*(requested-accepted). Body and three other physical/command wheels remain baseline. Candidate command active world wheel equals candidate physical world wheel.
- [ ] Solve nominal whole-pose geometry with original pose seed wrapper and tolerance. Convert candidate active world position into measured body frame; solve that leg from last_applied with original .1mm execution tolerance, holding other solver targets at FK(last_applied). Assemble only active q and per-leg IK fields into baseline support IKResult, recompute aggregate valid. Require nominal.valid, assembled.valid, slew<=2.5*dt, original validator(assembled, baseline.output). No bypass of invalid baseline.
- [ ] On acceptance replace physical, command, nominal_ik, command_ik, target.body_goal/body_step active row and target.intent_fraction atomically. Set active execution fraction1 for fully solved candidate. On rejection preserve entire baseline. Support target arrays, joints, output, valid/index/slew and histories remain exact. Keep selected intent best; refine only between last accepted and rejected gamma. Stop after bounded12trials; finite/mixed-row masks use device/dtype of baseline.
- [ ] Invoke helper after existing active execution refinement, before returning FeedbackReferenceStep. Do not modify base IK, PD, wheel controller or readiness gates.
- [ ] Run real-frame test above. Expectedallpass. Then add float32/64, mixed mode/invalid rows, rejected validator, no-request, nominal failure and slew failure cases; assert exact baseline rollback and exact support values.

## Task 3: Evidence binding

Files: `m1_reference_teacher.py`, `scripts/probe_m1_teacher.py`, same test module.

- [ ] Add diagnostic `execution_intent_fraction` and fingerprint v30-active-intent-commit. Existing support beta selects load/heave/height histories unchanged.
- [ ] In independent execution geometry verifier require beta<=intent_fraction<=1 and nonmode1 intent_fraction==beta. Reconstruct active reference from context.accepted_before/requested with intent_fraction; other wheels use beta. Compare reconstructed physical/command active world wheel to recorded attempted values. Existing measured-frame FK/step/residual checks remain.

```python
expected_active = old_active + intent_fraction*(requested_active-old_active)
assert_close(recorded_active, expected_active, atol=2e-6, rtol=0)
```

- [ ] Capture fresh feedback context for real-frame results; run independent encoded geometry verifier. Mutate intent fraction, active world target and support beta independently and require rejection. Preserve feedback replay/dynamic audit tests; no weakening residual gates to make tests pass.

## Task 4: Regression, review and native evidence

- [ ] Run new tests plus existing806test selection from v29 full log; read failures, fix root cause with RED/GREEN, retain complete output.
- [ ] Request one fresh final reviewer against this plan baseline and spec, focused on mixed rows, exact support preservation, rollback, independent evidence and intent/reference/execution consistency. ResolveC/I once with regression; ledger minors.
- [ ] After oldnative is confirmed gone and exit/result inspected, archive its source/tests/trace/video/results; verify remote/local SHA. Never overwrite a live candidate.
- [ ] Deploy only changed candidate files with SHA matching, verifyGPUidle and kernel lock, launch unique first-obstacle native (same10cm geometry/slowrolling/loadfeedback/4env/1000steps). Observeactual lift, crossing and recovery; code/tests are not success evidence.

## Rulings and review

User direct execution overrides repeated approval/choice prompts. Existing linked worktree reused. No configured Git identity: preserve files and hashes rather than change global identity or pretend commits. Windows helper unavailability uses manual ledger. Keep all evidence despite skill cleanup defaults. One implementation focus; yaw physical cause remains OPEN and must be evaluated after native change, not papered over by a relaxed gate.

Self-review: task2 produces intent_fraction consumed bytask3; all dataclass merges must include default tensor, notNone. Task1 fixture is immutable source, task3 updates a copiedrow only. The selected feature does not certify actual crossing. Exact implementation details may be corrected with ledgered rulings if test evidence contradicts this plan.
