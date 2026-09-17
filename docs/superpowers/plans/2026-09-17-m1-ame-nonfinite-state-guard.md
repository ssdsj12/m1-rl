# M1 AME Non-finite State Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent one invalid M1 simulation environment from terminating the whole AME training process by resetting that environment before its NaN/Inf state reaches the policy, while preserving a clear policy-side diagnostic for any future non-finite input.

**Architecture:** Add a pure Torch termination predicate that marks only environments whose articulation root or joint state contains NaN/Inf, then wire it into the M1 AME termination configuration. Keep the policy mathematically unchanged for finite inputs, but validate its observation, action mean, and standard deviation before constructing `Normal`, using `expand_as` instead of coupling the scale to the mean with `mean * 0.0`.

**Tech Stack:** Python 3.10, PyTorch, IsaacLab manager-based environments, pytest, tmux, TensorBoard.

---

### Task 1: Reset only M1 environments with non-finite articulation state

**Files:**
- Create: `Go2Pvcnn/ame_baseline/m1_ame_terminations.py`
- Modify: `Go2Pvcnn/ame_baseline/m1_ame_env_cfg.py`
- Modify: `Go2Pvcnn/ame_baseline/ame_env_wrapper.py`
- Create: `Go2Pvcnn/tests/test_m1_ame_terminations.py`
- Modify: `Go2Pvcnn/tests/test_m1_ame_config_static.py`
- Modify: `Go2Pvcnn/tests/test_ame_vec_env_and_cfg.py`

- [ ] **Step 1: Write failing predicate tests**

Add tests using `SimpleNamespace` robot data with three environments. Assert all-finite state returns `[False, False, False]`; NaN in `root_state_w`, Inf in `joint_pos`, and NaN in `joint_vel` each mark only their owning environment.

- [ ] **Step 2: Write a failing wiring test**

Read `m1_ame_env_cfg.py` and assert it declares `M1AmeTerminationsCfg`, constructs a `DoneTerm(func=nonfinite_robot_state, ...)`, and assigns that config to `M1AmeCrossLargeComplexEnvCfg.terminations`.

- [ ] **Step 3: Run tests and observe the expected failure**

Run:

```bash
cd /home/hexinkun/m1_rl/Go2Pvcnn
env -u PYTHONPATH -u CUDA_VISIBLE_DEVICES /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest \
  tests/test_m1_ame_terminations.py tests/test_m1_ame_config_static.py -q
```

Expected: failure because `ame_baseline.m1_ame_terminations` and M1 termination wiring do not exist.

- [ ] **Step 4: Implement the minimal predicate and config**

Create a pure Torch `nonfinite_robot_state(env, asset_cfg)` function. For `root_state_w`, `joint_pos`, and `joint_vel`, flatten every row after the environment dimension, require every value to be finite, and OR the invalid masks. Export the function. In `m1_ame_env_cfg.py`, subclass `TeacherElevationTrajectoryMpcSemanticTerminationsCfg`, add a `DoneTerm` using the new predicate, and assign the subclass to the M1 environment.

- [ ] **Step 5: Run the focused tests**

Run the command from Step 3. Expected: all focused tests pass, with only the existing Kit-dependent config-construction test skipped in plain pytest.

- [ ] **Step 6: Isolate the bad environment's same-step reward**

Add failing wrapper tests proving that a NaN reward is replaced with zero only when the same environment is currently reset by `nonfinite_robot_state`, while a NaN reward in any other environment raises an explicit error. Implement `_sanitize_rewards` using the intersection of the termination manager's recorded cause and the current `reset_buf`; this intersection is required because `get_term()` retains an episode's last termination cause. Call it immediately after `env.step()` and before handing rewards to RSL-RL.

### Task 2: Make policy failures explicit without changing finite behavior

**Files:**
- Modify: `Go2Pvcnn/ame_baseline/actor_critic_ame.py`
- Modify: `Go2Pvcnn/tests/test_actor_critic_ame.py`

- [ ] **Step 1: Write failing policy validation tests**

Add a test that inserts NaN into one observation and expects `RuntimeError` containing `non-finite AME actor observation`. Add a test that corrupts one policy parameter and expects `RuntimeError` containing `non-finite AME action mean`.

- [ ] **Step 2: Run tests and observe the expected failure**

Run:

```bash
cd /home/hexinkun/m1_rl/Go2Pvcnn
env -u PYTHONPATH -u CUDA_VISIBLE_DEVICES /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest tests/test_actor_critic_ame.py -q
```

Expected: the new tests fail because the current policy delegates the failure to `torch.distributions.Normal`/sampling.

- [ ] **Step 3: Implement validation and independent scale expansion**

In `update_distribution`, reject non-finite observations, reject a non-finite action mean, reject a non-finite or non-positive learned standard deviation, and construct the scale as `self.std.expand_as(mean)`. Do not clamp or replace policy observations.

- [ ] **Step 4: Run focused and regression tests**

Run the Task 1 and Task 2 test files, followed by the existing M1 AME/AME-AMP regression suite. Expected: no failures.

### Task 3: Validate the real failure mode and launch the official run

**Files:**
- Runtime log: `/home/hexinkun/m1_rl/run_logs/m1_ame_nonfinite_fix_1024x120.log`
- Runtime log: `/home/hexinkun/m1_rl/run_logs/m1_ame_1024x10000_once.log`

- [ ] **Step 1: Verify no competing training process**

List AME trainer processes and GPU compute PIDs. Stop only stale M1 AME processes after matching their exact PID and command; leave unrelated user jobs untouched.

- [ ] **Step 2: Run one fresh 1024-environment, 120-iteration process on GPU 4**

Use the AMP Python runtime, `cuda:4`, no resume checkpoint, and no restart supervisor. Capture all output and the exit code in the 120-iteration log.

- [ ] **Step 3: Prove the original boundary is crossed in the same process**

Verify the same PID logs iterations 98, 99, 100, and completes iteration 120 with exit code 0. Verify no `Traceback`, `RuntimeError`, `NaN`, `Inf`, `EARLY_TERMINATION`, or process restart marker appears. If the invalid-state termination fires, confirm training continues afterward.

- [ ] **Step 4: Start one fresh 10000-iteration process on GPU 4**

Launch exactly one 1024-environment process with the AMP runtime and no automatic restart. Point a fresh TensorBoard instance only at its newly reported log directory.

- [ ] **Step 5: Monitor the official run**

Confirm its PID, command, GPU allocation, increasing iteration/timestep counters, and TensorBoard event growth. Create a read-only heartbeat that reports only completion, failure, or required intervention; it must not restart training.

---

Self-review: the plan covers the observed non-finite state, M1-only wiring, policy diagnostics, regression tests, the exact prior iteration boundary, single-process proof, and a fresh 10000-iteration launch. It intentionally does not change rewards, model architecture, optimizer settings, environment count, or checkpoint semantics.
