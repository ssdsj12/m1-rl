# M1 WBC Free-body Actuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute inline in the existing worktree.

**Goal:** Validate single-owner torque and generalized bias without ground contact before WBC integration.
**Architecture:** A separate diagnostic creates8suspended M1s, zeroes drive gains in its own config only, and applies bounded small efforts for3physics ticks. Compare measured velocity change with full inverse dynamics; no training, no existing live scene altered.
**Tech Stack:** installed IsaacLab/PhysX, amp Python, PyTorch, pytest.

## Scope and files

Create `Go2Pvcnn/scripts/probe_m1_wbc_free.py` and `Go2Pvcnn/tests/test_m1_wbc_free.py`.
Add `free_dynamics_residual` to `Go2Pvcnn/ame_baseline/m1_wbc_dynamics.py`.
Evidence links under T306; no production actuator or source USD edit.

## Task steps

- [ ] RED: synthetic exact residual and malformed dimensions; AST confirms config gains0,
  suspended root,3ticks, native drive gain checks, no training imports or env.step.
- [ ] Implement `residual=M@(v1-v0)/dt+gravity+coriolis-[zeros6,tau]` with finite,
  matching shape/device/dtype and positive dt guards. No threshold hidden inside helper.
- [ ] Create env using existing M1 config,8flat environments, dt=0.001 or0.0005,
  decimation1, no push, seed2. Set all actuator stiffness/damping0 before creation.
  After reset suspend base at z2m, native DOF friction/drive gains logged. Initial
  joint speed per environment in [-.15,.15]rad/s, root angular speed<=.1rad/s.
- [ ] One zero-effort physics tick initializes caches; snapshot before each of3ticks.
  Apply tau amplitude10*dt Nm with signs0,+1,-1 (max20Nm/s slew). Use
  set_joint_effort_target, robot.write_data_to_sim, sim.step, scene.update.
  Require native stiffness/damping zero and native applied command equals requested.
- [ ] Log22component residual, measured acceleration, C, drive gains, contact force,
  root height, effort limit, requested/native command and seed/dt. Reject any contacts,
  nonfinite states or exceeded authored effort/velocity limits. No crossing success label.
- [ ] CPU tests and compile, then boundedGPU7run with exact own-placeholder trap.
  Residual predeclared maxabs<=0.02 N/Nm per row; require contact max<1e-6N.
  If residual fails, inspect friction, gyroscopic handling, coordinate acceleration
  and finite-difference convergence, not relax tolerance. Repeat at halfdt if needed.
- [ ] Record result and commit; controller integration remains gated on actual evidence.

This is a free-body interface test, not an exception to terrain crossing safety.
There is no policy rollout, no terrain interaction, no source physics edit or live
training restart. Runtime production keeps all prior settings until later validated switch.
