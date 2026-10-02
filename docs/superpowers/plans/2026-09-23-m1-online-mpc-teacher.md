# M1 Online MPC Teacher Continuation Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue training from the existing M1 AME checkpoint with an online MPC teacher whose rollout control share decays to zero while preserving PPO learning.

**Architecture:** Keep the AME policy and checkpoint dimensions unchanged. The rollout runner obtains the current MPC reference through the existing trajectory manager, converts it to the 16-D M1 action, and samples a fixed teacher-control mask per episode. The schedule is explicit and resume-relative, so the final policy can run independently at teacher ratio zero.

**Tech Stack:** Python, PyTorch, Isaac Lab, RSL-RL, pytest.

---

### Task 1: Lock the teacher schedule contract with tests

**Files:**
- Modify: `Go2Pvcnn/tests/test_m1_online_teacher_schedule.py`

- [ ] **Step 1:** Test default 1.0 warmup, midpoint 0.5, late 0.0, and explicit resume-relative values.
- [ ] **Step 2:** Run focused tests and verify failure before implementation.

### Task 2: Implement configurable resume-relative schedule

**Files:**
- Modify: `Go2Pvcnn/rsl_rl/rsl_rl/runners/on_policy_runner.py`
- Modify: `Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py`

- [ ] **Step 1:** Add configurable start/end and warmup/decay parameters.
- [ ] **Step 2:** Use the same helper for rollout blending and metrics.
- [ ] **Step 3:** Add CLI options without changing checkpoint dimensions.
- [ ] **Step 4:** Run focused tests and compile checks.

### Task 3: Resume checkpoint and smoke-test rollout

**Files:**
- Modify: `Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh`

- [ ] **Step 1:** Add approved checkpoint and GPU7/Xorg defaults.
- [ ] **Step 2:** Run two-iteration smoke test and inspect log for Vulkan/segfault errors.
- [ ] **Step 3:** Launch continuation and verify teacher-ratio metrics.

### Task 4: Verify autonomous handoff

**Files:**
- Modify: `docs/superpowers/specs/2026-09-23-m1-online-mpc-teacher-design.md`

- [ ] **Step 1:** Verify zero-teacher evaluation uses only policy actions.
- [ ] **Step 2:** Record collision, crossing, and early-lift metrics.