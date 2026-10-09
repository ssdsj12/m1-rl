# M1 Prepare Gate Implementation Plan

> **For agentic workers:** Use executing-plans task-by-task for this isolated component. Steps use checkbox syntax.

**Goal:** Implement the PREPARE readiness predicate in the approved contact-driven design without enabling it in training before runtime integration is verified.

**Architecture:** A batched, stateful Torch gate accepts pre-action contact, pose, support-margin and IK evidence. Each environment keeps independent identity, consecutive-frame count and collision latch. This component only authorizes leaving PREPARE; it neither produces joint actions nor declares crossing success.

**Tech Stack:** Python, PyTorch, pytest in the existing amp environment.

## Scope and dependencies

Parent: [approved design](../specs/2026-10-07-m1-contact-crossing-design.md).
Baseline `dacfb46` preserves previous dirty source separately from new implementation.
This component is an independently testable part of the full design, not a replacement for it.
Remaining parent obligations: pre-action observation adapter; bounded load transfer/M1 IK;
full phase coordinator and timeouts; independent event metrics; collision substeps;
8-env smoke; three-seed per-leg and six-obstacle physical gates with video;
safe bypass; PPO wiring/actual control ratio; policy-only evaluation.
Do not start training or claim physical acceptance after this component passes.

## Files

- Create `Go2Pvcnn/ame_baseline/m1_prepare_gate.py`: pure tensor readiness state.
- Create `Go2Pvcnn/tests/test_m1_prepare_gate.py`: 16 parameterized contract tests.
- Update notes dashboard, T306 and log index; add evidence log.

## Task 1: Protect baseline

- [x] Create branch `codex/m1-contact-crossing` in `.worktrees/m1-contact-crossing`.
- [x] Copy only scoped source/tests/notes; compare byte-for-byte to source with `cmp`.
- [x] Run seven focused existing test files: 23 passed. Commit baseline separately as `dacfb46`.

## Task 2: Readiness gate RED/GREEN

- [x] Add `test_m1_prepare_gate.py` using a real `PrepareGate(2)` instance.
  Input identities are integer episode/obstacle/leg/step tensors; force is [B,4],
  tilt and tilt_rate [B,2], margin [B], IK-valid/collision boolean [B].
  Tests cover five consecutive frames, broken support including selected wheel,
  tilt/rate/margin/IK rejection, per-row resets, skipped/repeated samples,
  unknown obstacle, NaN and collision surviving selected-leg handoff.
- [x] Run `/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q tests/test_m1_prepare_gate.py --tb=short`.
  Observed 16 assertion failures because the gate file does not exist.
- [x] Implement the following tensor transition in `PrepareGate.update`:

```python
same_event = (episode == self.episode) & (obstacle == self.obstacle)
consecutive = same_event & (leg == self.leg) & (step == self.step + 1)
self.poisoned = (self.poisoned & same_event) | collision
finite = (torch.isfinite(force).all(-1) & torch.isfinite(tilt).all(-1)
          & torch.isfinite(tilt_rate).all(-1) & torch.isfinite(margin))
safe = (finite & (force > 10.).all(-1) & (tilt.abs() <= .15).all(-1)
        & (tilt_rate.abs() <= .20).all(-1) & (margin >= .02)
        & ik_valid & ~self.poisoned & (episode >= 0) & (obstacle >= 0)
        & (leg >= 0) & (leg < 4) & (step >= 0))
self.count = torch.where(safe, torch.where(consecutive, self.count + 1, 1), 0).clamp(max=5)
self.episode, self.obstacle, self.leg, self.step = [x.clone() for x in (episode, obstacle, leg, step)]
return self.count >= 5
```

  Constructor initializes identities to -1, count to zero and poisoned to false
  on the requested device. Shape/type validation must reject malformed input
  rather than allow broadcasting; add failing tests before that validation.
- [x] Rerun the exact gate test plus the seven baseline test files: 43 passed.
- [x] Review source diff for unintended integration or changed training defaults: no runtime consumers added.
- [ ] Commit only gate/tests/plan and synchronized notes with test evidence.

## Parent coverage review

Covered here: initial PREPARE thresholds, continuous evidence, row isolation,
contact jitter, unknown/nonfinite rejection, event collision latch.
Not covered: geometry-derived margin correctness, actual support transfer or action
production, wall-clock stage timeouts, later crossing states, policy skill.
These remain open in T306; no simulator resources are consumed by this component.
