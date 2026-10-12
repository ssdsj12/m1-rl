# M1 Learning Signals / Reference Robot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. User chose current mirror inline execution.

**Goal:** Implement approved three autonomous-learning signals and reference bare-M1 physics, validate, then start a new pure-PPO run.
**Architecture:** Separate reference constants/configuration, tensor-only wheel observations, and bounded per-encounter reward state. Existing wrapper integrates final reward; checkpoint contract prevents stale policy loads. No action generator.
**Tech Stack:** PyTorch, IsaacLab/PhysX/USD, pytest, PowerShell/SSH.
**Spec:** ../specs/2026-10-12-m1-learning-signals-reference-robot-design.md
**Baseline:** 8fa5df3, branch10-12; all old PT/logs retained, no production hot edit, no GPU probe alongside training.

## Verification command

Run CPU tests via `../m1-learning-tests.ps1 -Tests 'Go2Pvcnn/tests/<test>.py'` using supplied pwsh. This packages candidate source into /tmp/m1-learning-reference-20261012, with CUDA_VISIBLE_DEVICES empty. Baseline: required-crossing/dynamic/strict/no-extra-clearance tests must pass before edits.

### Task 1: Reference robot configuration and version contract

Files: create `Go2Pvcnn/ame_baseline/m1_reference_robot.py`; modify `m1_ame_contract.py`, `m1_ame_env_cfg.py`, `m1_ame_assets.py`, `extension/parallelism/m1_kinematics.py`; test `Go2Pvcnn/tests/test_m1_reference_robot.py`.

- [ ] RED: assert root .62, named front(.3,-.6)/rear(-.3,.6), radius.0959, contractversion2/85/88 and old-contract rejection. Verify failure before implementation.
- [ ] Implement shared reference constants and `configure_reference_robot(cfg)` with DCMotor legs120/5.5/150/20 and implicit wheels0/30/200/20. Apply after inherited defaults; material1/1/0, no mass jitter, zero reset velocity, solver4/2. Spawn real Y-cylinder and disable only wheel meshes.
- [ ] GREEN: test real configuration via minimal Isaac config stubs plus static wiring; retain legacy tests with explicitly updated approved pose assumptions. Commit exact task files.

Interfaces: reference contract is consumed by Tasks2–5; cylinder radius is shared by physical actuator conversion, measurements, reward and termination.

### Task 2: Shape-consistent crossing measurements

Files: create `ame_baseline/m1_reference_geometry.py`; modify `m1_dynamic_crossing.py`, `m1_strict_crossing.py`, `ame_env_wrapper.py`, `tracking/mdp/policy_geometry_rewards.py`; test `tests/test_m1_reference_geometry.py`.

- [ ] RED: wheel bottom for identity/tilted cylinder; circle-edge near-miss with whole-bottom below top must not imply penetration; interior overlap penetration remains unsafe, no phantom pass by skipping overlap.
- [ ] Implement analytic oriented-cylinder bottom and actual surface-overlap evidence using named wheel pose. Feed same shape into strict/proxy queries. Preserve collision reset and far-side loaded recovery; optional new measurement interface keeps unrelated legacy callers explicit.
- [ ] GREEN: run geometry, strict, dynamic, no-margin, obstacle termination regressions. Log approximation limits; commit.

### Task 3: Explicit perceived wheel/obstacle and load observations

Files: create `ame_baseline/m1_learning_observations.py`; modify `m1_ame_env_cfg.py`; test `tests/test_m1_learning_observations.py`.

- [ ] RED: API `wheel_learning_features(hits, labels, valid, wheel_pos, root_quat, forces, weight)` returns [B,32], each wheel ordered near/far/dy/top/valid/contact/load/other-min. Test invalid rays, two separated obstacles, yaw/translation, shuffled named sensors, no terrain-registry reads.
- [ ] Implement chunked true-scan reduction and normalized load. Select nearest small-obstacle hit cluster in each wheel corridor; observed far extent is not hidden geometry. Missing observations zero+validity, all outputs finite/clipped. Runtime adapter uses actual robot mass, gravity and named contact/body indices.
- [ ] GREEN: test85/88 state input, unchanged map,12actions; run network shape test; commit.

### Task 4: Bounded safe preparation and passage rewards

Files: create `ame_baseline/m1_learning_progress.py`; modify `m1_dynamic_crossing.py`, `m1_required_crossing.py`, `ame_env_wrapper.py`; test `tests/test_m1_learning_progress.py`.

- [ ] RED: per-encounter frozen loaded baseline, unloading cap.10, passage cap.30, repetition/unsafe-rise no backpay, support loss/terminal/collision zero; inactive stage0/mixed4 zero, identity/reset clean.
- [ ] Implement tensor state with monotone observed highwaters. No fixed sequence: existing real encounter identifies wheel; support requires other3 upward loads and safe attitude. Advancement only while airborne, lane valid and nofailed/collision; no state-to-action connection.
- [ ] Extend final reward API optional process deltas: `bonus += safe * blocked * (.1*unload_delta + .3*passage_delta)`. Keep .3*prelift_delta+2*recovery; record each component and final PPO reward.
- [ ] GREEN: test final reward numerically including pre-step terminal snapshot, existing required-crossing regressions; commit.

### Task 5: Integrated tests, independent review, native and deployment

Files: new candidate diagnostic/deployment scripts under `Go2Pvcnn/scripts/`; README, notesindex/dashboard/T306/logindex, ai/human17.

- [ ] Full related CPU suite, finite new observations/checkpoint rejection/shape fixtures. Review branch once using fresh reviewer per executing-plans skill; fix important findings with RED→GREEN.
- [ ] Verify currentPID/cwd/checkpoint on CPU; SIGINT only current training after valid checkpoint, wait GPU release. Record safe boundary. No generic kill/restart helpers.
- [ ] Native isolated4env: actual DCMotor/shape/material/mass, stable ground rolling, correct features/reward, obstacle hit per-row reset/near-miss,5frame receipt. No teaching controller; probe exits before any training.
- [ ] Backup exact changed runtime files and hashes, deploy candidate, fresh2048/noresume/unchangedstd/.30/save100/10000. Observe firstupdates, CPU-check PT metadata/Adam/course and actual new dimensions; TB newrun. Do not launch if native evidence fails.
- [ ] README/notes/contract docs + server hash sync, ordinary push10-12 + independentref check; update heartbeat with newcontract/latestPID or actual blocker.

## Review Focus

Scan feature leakage, missing support sensor fail-open, observation memory at2048, robot config inheritance overrides, cylinder/proxy disagreement at edges, actor normalization/order, reward budget reset and unsafe backpay, terminal resets creating reward, loaded-wheel fake lifting,旧PT误载、并发GPU与生产热改。
