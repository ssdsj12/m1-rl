# M1 approach gate audit, 2026-10-01

## Purpose / stage / related node

Investigate repeated teacher-assisted crossing failures without another
parameter sweep. Stage: AME teacher action gate, child T306.approach-gate.

## Procedure and inputs

`PYTHONPATH=. /home/hexinkun/miniconda3/envs/amp/bin/python /tmp/audit_m1_approach_gate.py`
from the Go2Pvcnn root. Script compiles the exact current
`AmeRslRlEnvWrapper.get_mpc_teacher_action` method from its AST, retaining
production action conversion and safety helpers. Fake sensor/manager inputs:
upright stationary robot, finite single-leg reference, broad small candidate
true, large candidate false, near trigger false for all three calls. CPU only;
no physics, PPO updates, display changes or GPU process interruption.

## Evidence

Calls 0/1/2: teacher valid true throughout; max absolute leg action
0.0 / 0.0799999982 / 0.0799999982. The initial fallback-used flag is consumed
on the first call; `initial_roll = initial_fallback & ~small_trigger` therefore
stops suppressing legs on call 1 despite no near obstacle. This demonstrates
a lifecycle gate defect, not measured contact timing in PhysX.

## Corrections to previous explanations

- Active factory creates `batch_mpc_planner.manager.MpcTrajectoryManager`;
  its `plan_segment` uses the parametric M1 serial enforcement. Changes in
  `extension/parallelism/planner.py` do not establish a fix for that path.
- A 32-frame horizon already contains four sequential swing windows;
  resetting at its end does not inherently skip the other three legs.
  Changing the replan interval to 128 may instead hold the final cached frame.
- A single debug action sample cannot prove realized lift/clearance or that
  a particular slew limit is the cause of failure. Earlier claims were too strong.
- Current crossing metric remains a candidate-disappearance/any-wheel-clearance
  proxy; it does not independently certify all-foot crossing and stable touchdown.

## Resource state

Fresh process check: placeholder PID 2138492; no train_m1 process. User's GPU7
placeholder unchanged. Other GPU jobs untouched. No new physical run.

## Result and next step

Reproduction confirmed, production defect not fixed in this audit. After
multiple unsuccessful changes, require explicit lifecycle ownership and
fixed-policy diagnostic traces rather than another long training restart.
Cover approach, near-trigger activation, swing completion, touchdown, reset,
large-obstacle cancellation and reacquisition. Then fix the minimal gate,
run regression and physical smoke. Full crossing/avoidance goal remains open.

## Git refs / key files

Baseline and candidate: current uncommitted remote worktree (unchanged production).
Key file: `Go2Pvcnn/ame_baseline/ame_env_wrapper.py`.
Diagnostic: `Go2Pvcnn/tests/diagnostics/audit_m1_approach_gate.py`.
Do not overwrite prior last-verified feature refs with this diagnosis.
