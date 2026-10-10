# M1 Required Crossing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Keep the existing isolated contact-recovery worktree; do not overwrite its unrelated changes.

**Goal:** Make obstacle-course reward favor actual single-wheel pre-lift, collision-free clearance and stable far-side landing instead of body progress around/through obstacles.

**Architecture:** Keep pure PPO and the existing physical encounter tracker. Modify only progressive obstacle geometry and reward consumption; do not force actions or change servos. Stage0 remains obstacle-free. Preserve 2048 environments, 3/6/10cm progression and the removed speed-error gate.

**Tech Stack:** IsaacLab, PyTorch, pytest, existing AME wrapper and semantic course registry.

## Confirmed defect / evidence

`wheel_obstacle_reward_terms` currently computes progress from root velocity;
its positive progress does not depend on collision-free crossing. The climb
shaping is not a complete crossing reward. Production at roughly1015 updates
has nonzero climb shaping and collision penalty, strict successes0.
This is not yet evidence of sufficient real wheel-bottom clearance.

## Task 1: Trace exact geometry and event consumption before editing

- [ ] Read `m1_mixed_course.py`, `semantic_course.py` obstacle sizing and
  `ame_env_wrapper.py` strict event update/reset order completely in affected sections.
- [ ] Record actual wheel-track spacing, tire envelope and obstacle footprint.
  Widen alternating single-wheel obstacles only within the opposite support
  wheel's free corridor; preserve longitudinal rear-wheel/landing spacing.
- [ ] Inspect collision/recovery event booleans and clearance geometry used by
  `m1_strict_crossing.py`; reuse measured bottom-envelope data, not wheel-center height.

## Task 2: TDD reward truthfulness

Files: `ame_baseline/m1_obstacle_rewards.py`, `ame_baseline/ame_env_wrapper.py`,
new `tests/test_m1_required_crossing.py`.

- [ ] Add failing tensor fixtures: forward sliding collision receives no positive
  obstacle-progress/completion bonus; lateral bypass receives no crossing bonus;
  pre-obstacle articulated single-wheel lift receives shaping; whole-body heave
  and simultaneous paired lift do not qualify for that shaping.
- [ ] Add event tests: successful far-side touchdown alone cannot receive stable
  recovery bonus; recovery_complete receives it once; reset/terminal frames,
  repeated calls and failed/collision encounters cannot receive duplicate bonus.
- [ ] Implement minimal event-backed bonus and collision/bypass gating. Keep
  dense pre-lift shaping separate from success counters. Never increase strict
  success counters based on reward value.
- [ ] Log actual minimum wheel-bottom clearance during horizontal overlap,
  valid sample count, pre-lift count, collision count and stable landing count.
  No samples must remain distinguishable from zero clearance.
- [ ] Run new tests RED then GREEN and existing obstacle/strict/metrics suites.

## Task 3: TDD layout exposure

Files: `ame_baseline/m1_mixed_course.py`, `extension/semantic_course.py`,
`tests/test_m1_flat_first_terrain.py` and new crossing tests.

- [ ] Add footprint intersection tests using actual tire envelope and stage
  geometry: nominal target wheel intersects each alternating block, opposite
  wheel retains free support, and downstream landing interval stays open.
- [ ] Add lateral bypass trajectory fixture proving it cannot collect crossing
  completion/progress reward. Do not substitute an impenetrable trap for learning.
- [ ] Implement the minimum stage1–3 footprint/layout adjustment, keeping stage0
  and final mixed-terrain families unchanged.

## Task 4: Deployment and physical verification

- [ ] Verify exact running process8573 and newest valid PT, then pause only at
  its checkpoint boundary. No parallel native probe while22GB training is live.
- [ ] Run bounded native geometry plus policy rollout with pre-reset wheel
  poses, obstacle bounds, contact/collision, clearance and landing trace/video.
  Validate runtime reward wiring, not only scene creation.
- [ ] A probe that fails crossing must be reported as such; fix demonstrated
  reward/layout bugs before deploying, never weaken success thresholds.
- [ ] User override: start FRESH training with2048envs/save100 for10000
  iterations after verification. Do not load previous model weights, optimizer,
  normalization or curriculum state. Start flat-first stage0.
- [ ] Verify actual resumed update/checkpoint, switch TensorBoard and update
  monitoring/notes. Claim learned10cm crossing only after video and strict metrics.

## Scope and handoff

No code has been changed for this feature yet. PID8573 has exited after TERM;
the latest observed saved checkpoint was model_1000.pt and is retained only as
an archive, not as an input to the new training. Automation m1-ppo is paused.
User explicitly requested fresh training rather than continuation of this model.
User approved the behavior design. Implementation should run inline; no need
to create a separate task or affect other processes. Current branch is
`codex/m1-contact-recovery`, baselinebb57e7d plus existing uncommitted work.
