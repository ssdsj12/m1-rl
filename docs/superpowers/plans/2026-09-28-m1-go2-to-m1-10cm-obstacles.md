# M1 active-chain conversion and 10 cm obstacle Implementation Plan

> **For agentic workers:** This plan is executed in the active remote `m1_rl/Go2Pvcnn` checkout with focused verification before any training restart.

**Goal:** Make the active M1 AME chain use M1 geometry and semantics, train on spaced 10 cm obstacles, and penalize real M1 geometry intersection with semantic obstacles.

**Architecture:** Keep `go2_pvcnn` as the repository compatibility namespace and preserve generic robot backends. Add the M1-specific terrain profile and layout policy in `M1AmeCrossLargeComplexEnvCfg`; route the existing geometry collision event through an explicit M1 reward wrapper; validate the layout with the actual semantic-course builder and validate behavior with a short PhysX trajectory probe.

**Tech Stack:** Python, Isaac Lab/Isaac Sim, PyTorch tensor planners, pytest.

---

### Task 1: M1 obstacle profile and layout safety

**Files:**
- Modify: `ame_baseline/m1_ame_env_cfg.py`
- Test: `tests/test_m1_obstacle_profile.py`

- [x] Set the M1-only semantic profile to `small: (0.10, 0.10)`.
- [x] Set M1 counts to 10/8/6 small obstacles by terrain class, retaining large obstacles on non-plane terrain.
- [x] Set reset half extent to `0.45 m`, spacing clearance to `0.80 m`, and tile margin to `0.50 m`.
- [x] Verify the real `build_course_anchors` path yields ten-centimetre obstacles outside the reset region and at least `0.90 m` center spacing.

### Task 2: M1 collision reward entry point

**Files:**
- Modify: `ame_baseline/m1_obstacle_rewards.py`
- Modify: `ame_baseline/m1_ame_env_cfg.py`
- Test: `tests/test_m1_ame_config_static.py`

- [x] Add `m1_obstacle_collision_penalty`, delegating to the M1 FK/scanner collision event and sanitizing its output.
- [x] Route `parallelism_geometry_collision` through this M1 function with weight `-18.0`.
- [x] Keep crossing/lift metrics separate from collision events.

### Task 3: Verification gate before retraining

**Files:**
- Test: `tests/test_m1_obstacle_profile.py`, focused M1 test set.
- Probe: `/tmp/probe_m1_cfg_contract.py` and the existing M1 PhysX probe.

- [x] Run Python compilation and focused static/planner/config tests.
- [ ] Run a short PhysX planner trajectory on the new 10 cm profile.
- [ ] Accept only one-leg swing, clearance above obstacle top, touchdown after obstacle, stable posture, and no collision event.
- [ ] Start long training only after the physical gate passes.
