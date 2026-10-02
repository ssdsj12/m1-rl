# M1 AME Reward Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the remaining Go2-only AME reward assumptions with named M1 joint/body geometry so training rewards normal wheel rolling, penalizes unsafe M1 body collisions, supports crossing small obstacles, and discourages impacts with large obstacles without changing PPO/AMP algorithms.

**Architecture:** Keep the reward keys and weights inherited from `parallelism-amp`, but route M1 regularizers through a dedicated module that separates the 12 planner joints from four wheel joints. Add a live-policy collision reward backed by `get_robot_backend("m1")`, and replace foot sliding with a wheel rolling-residual reward. Wire these only into `M1AmeCrossLargeComplexEnvCfg`; Go2 configs remain unchanged.

**Tech Stack:** Python 3.10, PyTorch, IsaacLab manager rewards, M1 named-joint adapter, Parallelism M1 FK/collision backend, pytest.

---

### Task 1: Named M1 joint and action regularizers

**Files:**
- Create: `Go2Pvcnn/ame_baseline/m1_ame_rewards.py`
- Create: `Go2Pvcnn/tests/test_m1_rl_reward_geometry.py`

- [ ] **Step 1: Write failing tensor tests**

Cover all 16 asset joints with deliberately different planner/wheel values. Assert planner posture and joint-limit penalties ignore wheel angle, while velocity/acceleration/action-rate terms include wheel motion through the explicit surface-speed scale `M1_WHEEL_RADIUS_M ** 2`. Assert torque and energy split planner and wheel selections by name rather than position.

- [ ] **Step 2: Run the new tests and observe import failures**

```bash
cd /home/hexinkun/m1_rl/Go2Pvcnn
env -u PYTHONPATH -u CUDA_VISIBLE_DEVICES /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest tests/test_m1_rl_reward_geometry.py -q
```

Expected: RED because `ame_baseline.m1_ame_rewards` does not exist.

- [ ] **Step 3: Implement named selection and reward functions**

Implement these public functions using `select_named_joint_state` with `M1_ASSET_JOINT_NAMES`, `M1_PLANNER_JOINT_NAMES`, and `M1_WHEEL_JOINT_NAMES`:

```python
m1_joint_vel_l2(env, asset_cfg)
m1_joint_acc_l2(env, asset_cfg)
m1_joint_torques_l2(env, asset_cfg)
m1_action_rate_l2(env)
m1_energy(env, asset_cfg)
m1_joint_pos_limits(env, asset_cfg)
m1_joint_position_penalty(env, asset_cfg, stand_still_scale, velocity_threshold)
```

For squared wheel angular quantities, multiply by `M1_WHEEL_RADIUS_M ** 2` so the term is measured as squared wheel-surface linear motion. Position and limit rewards use only the 12 planner joints. Torque and energy retain their physical SI meaning and include separately selected wheel values at scale 1.0.

- [ ] **Step 4: Run the focused tests**

Expected: all Task 1 tests pass.

### Task 2: M1 live-policy geometry collision reward

**Files:**
- Modify: `Go2Pvcnn/tracking/mdp/policy_geometry_rewards.py`
- Modify: `Go2Pvcnn/tracking/mdp/__init__.py`
- Modify: `Go2Pvcnn/tests/tracking/test_policy_geometry_rewards.py`

- [ ] **Step 1: Write a failing 16-to-12 M1 collision test**

Pass a 16-joint tensor in `M1_ASSET_JOINT_NAMES` order and use a fake M1 backend that asserts its FK receives exactly `M1_PLANNER_JOINT_NAMES` in 12 dimensions. Make one environment return a collision bit and assert the event is `[0.0, 1.0]`.

- [ ] **Step 2: Implement the backend-driven event**

Add `live_m1_policy_geometry_collision_event` and `m1_policy_geometry_collision_penalty`. Select the 12 planner joints by name, call `get_robot_backend("m1").fk`, expand live geometry through the existing collision adapter, and call the backend's collision mask so M1's 16 official wheel/calf/hip/thigh shapes and wheel support tolerance are used.

- [ ] **Step 3: Preserve Go2 behavior and run both test sets**

Run the existing Go2 geometry tests and the new M1 test. Expected: all pass without changing `policy_geometry_collision_penalty` behavior.

### Task 3: Wheel rolling reward and M1 config wiring

**Files:**
- Modify: `Go2Pvcnn/ame_baseline/m1_ame_rewards.py`
- Modify: `Go2Pvcnn/ame_baseline/m1_ame_env_cfg.py`
- Modify: `Go2Pvcnn/tests/test_m1_rl_reward_geometry.py`
- Modify: `Go2Pvcnn/tests/test_m1_ame_config_static.py`

- [ ] **Step 1: Write failing wheel rolling tests**

For four contacted wheels, assert zero penalty when wheel-center planar speed equals `M1_WHEEL_RADIUS_M * abs(wheel_angular_velocity)`, positive penalty for locked-wheel sliding, and no penalty for non-contact wheels.

- [ ] **Step 2: Implement `m1_wheel_rolling_residual_l2`**

Use M1 `FOOT_LINK` body velocities, the matching four `FOOT_JOINT` velocities, and contact masks. Penalize the squared difference between planar wheel-center speed and wheel surface speed only while contacted. This replaces generic `feet_slide`, which incorrectly treats normal wheel rolling as foot slip.

- [ ] **Step 3: Add `M1AmeRewardsCfg`**

Subclass `CrossLargeComplexPpoRewardsCfg`. Replace joint/action/energy/position/limit terms with Task 1 functions, replace geometry collision with `m1_policy_geometry_collision_penalty` at the existing `-10.0` weight, and replace `feet_slide` with the Task 3 rolling residual. Keep velocity/orientation semantics and weights unchanged. Retain M1 `FOOT_LINK` contact selectors for air-time/contact terms and the existing M1 undesired-contact selector; do not inherit any `joint_names=".*"` or `body_names=".*_foot"` term.

- [ ] **Step 4: Verify runtime config resolution**

Construct the M1 config inside Isaac Sim and assert all planner/wheel/body ids resolve in the documented order, action remains 16, policy state remains 12 planner joints, and Go2 config snapshots are unchanged.

### Task 4: Stability and obstacle behavior gates

**Files:**
- Runtime evidence: `/home/hexinkun/m1_rl/run_logs/`

- [ ] **Step 1: Run the full AME/AMP regression suite**

Expected: no failures, including Go2 tests.

- [ ] **Step 2: Run 8-env M1 reward probes**

Record per-term finite values on flat terrain, small box/stairs, and large obstacles. Acceptance: flat rolling does not accumulate `feet_slide`; planner posture/limits never include wheel angles; default stance has zero geometry collision; wheel support contact alone is not a collision.

- [ ] **Step 3: Run a fresh 1024-env single-process stability gate**

Run at least 120 iterations and require one PID, exit code 0, finite reward/value/policy metrics, and no restart.

- [ ] **Step 4: Run small-cross/large-avoid behavior evaluation**

Use fixed-seed evaluation episodes and record: small-obstacle crossing success, M1 body collision rate, large-obstacle collision rate, forward progress, and invalid-state termination rate. Start the official 10000-iteration run only after rewards are finite and both small-cross and large-avoid metrics move in the correct direction versus the pre-alignment baseline.

---

Self-review: the plan directly covers every reward rule in the attached M1 design that is active in AME, preserves algorithms and Go2 behavior, gives physical units/sources for new scales, and makes the final gate behavioral rather than merely “process stayed alive.”
