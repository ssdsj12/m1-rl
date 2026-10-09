# 2026-10-08 M1 WBC execution adapter contract

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md). Stage: isolated
WBC actuator handoff, before grounded-support execution.

## Purpose

Close the code-level gap between a valid CPU WBC solution and a safe native
effort write. Preserve the user-approved order: strict crossing success first;
balance recovery is measured only after crossing succeeds.

## Change

Added `Go2Pvcnn/ame_baseline/m1_wbc_execution_adapter.py`. It accepts only a
single-env, valid 22-coordinate acceleration / 16-joint effort / nonempty 3-D
contact-force result with bounded dynamics residual; checks exact event identity,
native simulation clock and step count, zero implicit stiffness/damping, effort
limits derived from the stricter PhysX/config values, and same-episode previous
explicit-total effort. Slew (20 Nm/s) and residual (0.02) are fixed policy, not
caller parameters. The initial command is also bounded from measured native
prewrite total effort; after every write the adapter reads native force back and
returns only that measured command as valid next-tick history. Failed readback
must stop before the caller advances simulation.

## Verification

- Red: the new tests failed because the execution adapter did not exist.
- Green: adapter/QP tests -> 35 passed; full focused WBC regression after
  follow-up guards and CPU-oracle budget correction:
  `pytest -q tests/test_m1_wbc_*.py` -> 142 passed.
- The native clock guard was derived from the installed Isaac Sim API source:
  `current_time_step_index` and `current_time` are native simulation counters.
  CPU test covers a caller claiming step zero after native simulation advanced.
- A separate bounded one-env ground-contact probe ran on GPU7 and observed all
  four native wheel contacts by tick 8, but only as transient touchdown. It did
  not establish stance, balance, crossing, clearance, landing, or recovery.
  The user's `sleep.py` placeholder was restored afterward. No training ran.

## Conclusion and next step

This makes actuator handoff reject stale or blended commands, but does not
compute grounded initial support or prove physical stability. The contact probe
found zero native forces for seven ticks followed by highly unequal touchdown
loads; it is not stance evidence. Next implement a measured same-state handoff
from settled support to explicit WBC torque without advancing physics between
disabling implicit PD and applying its measured equivalent. Verify named 16-DOF
order, sustained support, and slow roll before four isolated single-wheel
crossing gates. Do not start PPO training before those physical gates pass.

Baseline: `0768d96`; candidate files in the current isolated
`codex/m1-contact-crossing` worktree. No commit yet at time of this log.
