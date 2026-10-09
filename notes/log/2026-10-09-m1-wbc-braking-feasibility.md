# WBC braking: exact feasible intervals and task-ramp counterfactual

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), new child
execution-physical/handoff-transient/braking-allocation.
Baseline223a0ec; diagnostic scripts in `/tmp`, no actuator edits in this audit.

## Fresh input capture

Transparent wrapper `/tmp/m1_capture_wbc_solver_inputs_20261009.py` records
original solve arguments/results at selected native steps; forwards all inputs
and outputs unchanged. Same500tick run onGPU0, default objective and bounds.
Log `/tmp/m1_wbc_solver_capture_20261009_EbP1VE.log`, SHA256
`df682d5cd889125768bef6b58b31cf271ceb3e61b5395b32b1eae6c7e07b305c`.
Run terminated on numerical lock-stage rejection atfeedback483 (firstQPstage
solved; second said inconsistent). Do not equate this with proven physical
infeasibility. Samples294/400/700 captured;790 not reached. No live probe remains.

## Exact one-step LP audit

`PYTHONPATH=Go2Pvcnn python /tmp/m1_audit_wbc_feasibility_20261009.py LOG STEP`
assembles the same fullM/h/J/contact/friction/group-force/acceleration/torque
constraints. Min/max xdd and fixed requestedxdd use scipy HiGHS, not task weights.
Separation rows empty in these samples; full3D rolling rows retained.

| Native step | desiredxdd | feasible xdd interval, m/s2 | exact target feasible |
| --- | ---: | --- | --- |
|294(snapshot-only damping target)|-.011293|[-.247089,-.211554]|no|
|400(actual support solve)|+.035027|[-.212919,-.177606]|no|
|700(actual support solve)|+.118669|[-.155906,-.121748]|no|

Min/max independent residuals <=3.1e-9. Late-step objectives cannot achieve
braking in one frame under the observed torque history. This does not mean the
slew bound should increase or that all future trajectories are infeasible.
294native-capacity minimumL-infinity change for exact xdd is.245301Nm, NOT9.9Nm;
the older9.9Nm was a chosen QP internal-force allocation, not a necessity proof.
That LP can exploit angular acceleration -5.62rad/s2 and is NOT an accepted command.

## Frozen-model ramp, not dynamic simulation

`/tmp/m1_audit_wbc_task_ramp_20261009.py LOG 700` repeatedly solves the same
frozen matrices with20Nm/s*.001s torque increments, no state integration.
All hard contact/friction/support/acceleration constraints preserved. Only
soft task ordering differs. By iteration29:

- all22equal: xdd-.026665 (still opposite target);
- sixbase before16joint damping: xdd+.118669, base target approximately met;
- translation thenangular thenjoints: xdd+.118669 but large intermediate angular
  acceleration (about-2.76rad/s2), not selected for physical comparison.

Base-first maxjointaccel rises to~29rad/s2 in this frozen sequence; therefore
this result is a hypothesis for the native physical gate, not stability proof.
It explains why a one-frame priority shadow can miss a multi-step effect.
Next bounded comparison uses opt-in base-first, same torque/contact/gate limits.
Default/training controller unchanged; no policy or crossing acceptance.
