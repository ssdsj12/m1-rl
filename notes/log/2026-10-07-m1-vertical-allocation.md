# M1 bounded vertical support allocation

Parent: [T306 whole-body-load-model](../todo/T306-m1-ame-long-train-stability.md).
Stage: isolated dynamics diagnostic, not training or actuator control.
Baseline Ref: a457f4f. Candidate Ref: commit containing this log.
Key files: m1_support_effort.py, test_m1_support_effort.py,
probe_m1_contact_prepare.py.

## Change relative to baseline

The previous version verified Jacobian coordinates only. This version computes
vertical support forces satisfying floating-base balance and joint effort limits.
Inactive supports receive zero force. Invalid/nonfinite/infeasible candidate rows
return valid=false and zero effort; torque is never clipped to pretend feasibility.
Sixteen floor-active minimum-norm candidates are considered. This is not an
exhaustive torque-constrained QP: rejection does not prove full infeasibility.
Assumptions: quasi-static flat support, world-Z forces at wheel centers, no
friction, contact moments or acceleration. Numerical base residual tolerance
is 1e-3 in the corresponding force/moment components, not a stability threshold.

## Tests

RED: five tests failed on missing module before implementation. GREEN: all five
pass, covering four-support balance/sign, three-support COM feasibility, torque
rejection, nonfinite/horizontal residual and absent support. Focused 13-file
regression (previous 12 plus test_m1_support_effort.py):100 passed in5.27s.
Command: amp Python -m pytest -q with those focused files, --tb=short.

## Runtime read-only smoke

GPU7, flat8 seed2,32 standing warmup steps, --num_steps 1 --dynamics_audit.
Raw evidence:/tmp/m1_vertical_allocation_20261007.log; native exit0.
All8 four-contact static allocations accepted. Maximum base residual2.274e-13;
maximum absolute computed effort15.531Nm. These are computed values, NOT measured
applied torque or achieved lifting. No effort target was written by this solver.
The probe retains position-only warmup and its existing one PREPARE step.
Own placeholder809511 restored as848694; verified alive. Other user ldc3227360
remained alive. No display/driver/reset changes, no new training or upload.

## Next gate

Child bounded-force-effort-allocation now has unit and four-contact runtime
evidence. Next: audit three-contact allocation after actual PREPARE; establish
named actuator mapping, bounded feedforward ramp, total PD+feedforward limits,
and unconditional clearing on reset/rejection/exit before physical application.
Then actual standing/single-leg lift, obstacle clearance/landing/collision,
recovery/bypass/video and policy learning. Full crossing acceptance remains open.
