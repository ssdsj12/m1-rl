# Post-PREPARE three-support allocation audit

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), whole-body-load-model.
Baseline Ref:edce545. Candidate Ref:commit containing this log.
Key file:probe_m1_contact_prepare.py. Stage:read-only diagnostic, no torque command.

## Change and verification

Refresh Jacobian, gravity and wheel origins AFTER PREPARE; resolve the selected
wheel mask and compute hypothetical three-contact static allocations at10N and
30N floors. Emit named articulation order and margins to avoid stale warmup data.
Focused13-file suite100 passed in5.31s. No solver/control behavior change.

Physical command: amp Python scripts/probe_m1_contact_prepare.py --device cuda:0
--headless --num_steps 100 --transfer_speed .04 --max_root_shift .08 --dynamics_audit.
GPU7 only, flat8 seed2; raw:/tmp/m1_post_prepare_allocation_20261007.log; exit0.
Original PREPARE readiness8/8, stopped=null, actual margins21.59..27.80mm.
Hypothetical three-support10N floor:valid8/8. Selectedleg0..3 repeated twice.
30N floor:onlyrows3,7 valid (selectedleg3); sixotherrows rejected. Their weakest
computed support25.61..26.42N. Thus the existing20mm geometric gate does NOT imply
the30N lifting-load floor. This is model evidence, not measured three-leg lift.
Max computed required effort33.137Nm; no effort was applied.

## Actuator lifecycle source finding

Installed IsaacLab articulation.reset resets actuators and external wrench, but
does not clear joint_effort_target. set_joint_effort_target fills a persistent
buffer consumed by write_data_to_sim. ImplicitActuator computes approximate
PD+feedforward effort; it does not return measured physical torque. Therefore an
eventual feedforward owner must clear targets on rejection/reset/exit and validate
combined estimated effort, not only the standalone support solution.

## Next action

New child:post-lift-load-readiness under whole-body-load-model. PREPARE must target
a feasible three-support load distribution matching LIFT's30N floor, within
existing bounded shift/IK constraints. Do not relax30N merely to pass or apply
effort to the six rejected poses. Then ramp/clear ownership and bounded standing/
single-leg physics. Crossing/landing/collision/bypass/PPO remain unverified.
No long training or upload. Placeholder848694 restored867441, verified alive;
other user ldc3227360 remains alive. No display or driver changes.
