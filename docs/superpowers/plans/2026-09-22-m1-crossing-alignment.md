# M1 AME Crossing Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align M1 AME training and evaluation with the original semantic obstacle crossing task, including wheel-phase state, adaptive clearance, real episode metrics, and strict checkpoint evaluation.

**Architecture:** Keep M1 AME observations and 16-D actions unchanged. Add a pure Torch crossing state module for per-environment lifecycle and a wrapper-owned episode accumulator that consumes semantic scanner geometry and termination signals. Reuse the original evaluator's CLI semantics while adapting asset names and M1 checkpoint validation.

**Tech Stack:** Python 3.10, PyTorch, Isaac Lab 4.5, Gymnasium, rsl_rl, TensorBoard, pytest.

---

### Task 1: Port pure crossing state transitions

**Files:**
- Create: `Go2Pvcnn/ame_baseline/m1_crossing_state.py`
- Test: `Go2Pvcnn/tests/test_m1_crossing_state.py`

- [ ] Write tests for candidate entry, front/rear axle phases, completion only after all four wheels clear the finish margin, failure reset, and large-obstacle exclusion.
- [ ] Run the focused tests and verify they fail because the module is absent.
- [ ] Implement `CrossingState` tensors and `update_crossing_state(...)` using vectorized Torch operations; inputs are obstacle candidate mask, wheel x relative to obstacle, wheel clearance, large semantic mask, `done`, and `terminated`.
- [ ] Run the focused tests and verify all state transition cases pass on CPU.
- [ ] Commit the pure state module and tests.

### Task 2: Connect M1 semantic geometry and adaptive clearance

**Files:**
- Modify: `Go2Pvcnn/ame_baseline/m1_obstacle_rewards.py`
- Test: `Go2Pvcnn/tests/test_m1_obstacle_rewards.py`

- [ ] Add a failing test that checks wheel-center target clearance is `obstacle_top + M1_WHEEL_RADIUS_M + [0.05, 0.10]` and that large semantic cells disable the small-obstacle climb term.
- [ ] Run the test and verify the current implementation fails the wheel-radius assertion.
- [ ] Update the height gate to use wheel-center clearance including `M1_WHEEL_RADIUS_M`; preserve normal gait when no semantic-small candidate is present.
- [ ] Run the obstacle reward tests and a CPU shape test for batch size 8.
- [ ] Commit the reward correction.

### Task 3: Add episode crossing and avoidance accounting

**Files:**
- Create: `Go2Pvcnn/ame_baseline/m1_crossing_metrics.py`
- Modify: `Go2Pvcnn/ame_baseline/ame_env_wrapper.py`
- Modify: `Go2Pvcnn/rsl_rl/rsl_rl/runners/on_policy_runner.py`
- Test: `Go2Pvcnn/tests/test_m1_crossing_metrics.py`

- [ ] Write failing tests for candidate denominator semantics, completion/failure counts, no-candidate `NaN`, and large-avoidance counting.
- [ ] Run the focused metrics tests and verify failure.
- [ ] Implement `CrossingEpisodeAccumulator` with counters for candidates, crossings, failures, collisions, large candidates, and large avoidance; expose `snapshot()` with rate fields.
- [ ] Feed scanner-derived semantic candidate masks and termination masks from the wrapper; reset per-environment state on done.
- [ ] Add TensorBoard scalars `Metrics/semantic_candidate_rate`, `Metrics/semantic_crossing_rate`, `Metrics/crossing_failure_rate`, `Metrics/large_avoidance_rate`, and `Metrics/lift_phase_rate`.
- [ ] Run focused metrics tests and verify no-candidate rates are NaN/unsampled rather than zero.
- [ ] Commit metrics integration.

### Task 4: Align strict checkpoint evaluation CLI

**Files:**
- Create: `Go2Pvcnn/scripts/m1_checkpoint_eval.py`
- Modify: `Go2Pvcnn/ame_baseline/m1_evaluation_metrics.py`
- Test: `Go2Pvcnn/tests/test_m1_checkpoint_eval_script.py`

- [ ] Write failing static tests for the four required flags and M1 checkpoint dimension validation.
- [ ] Run the tests and verify failure.
- [ ] Implement the evaluator with `--semantic-crossing`, `--obstacle-threshold`, `--min-crossing-rate`, and `--disable-crossing-reset`; use fixed small/large semantic layouts and M1 AME action dimensions.
- [ ] Return nonzero exit status when `semantic_crossing_rate < min_crossing_rate` unless no candidates were observed.
- [ ] Run static CLI tests and a one-environment headless evaluation smoke.
- [ ] Commit evaluator alignment.

### Task 5: End-to-end smoke and fresh long-run restart

**Files:**
- Modify: `Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh` only for metric/config switches if required.
- Create: `run_logs/m1_ame_8env_crossing_alignment.log` on the remote host.

- [ ] Run 8-env CPU logic smoke and 8-env GPU semantic crossing smoke; require state transitions, metric keys, and no shape errors.
- [ ] Run `m1_checkpoint_eval.py` against a known M1 checkpoint and capture candidate/crossing/avoidance metrics.
- [ ] Stop the current fresh run only after the new smoke passes, then start a new 1024-env run from random initialization with `SAVE_INTERVAL=100` and TensorBoard enabled.
- [ ] Verify the first training log contains the real metric names and the adaptive teacher schedule.
- [ ] Commit only source/tests/docs; keep generated logs and checkpoints untracked.
