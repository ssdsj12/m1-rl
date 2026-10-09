# M1 floating-base dynamics convention audit

Stage: whole-body-load-model prerequisite; parent
[T306.whole-body-load-model](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:`818c427`; Candidate Ref:commit containing this log.
Key files:`m1_dynamics.py`, `test_m1_dynamics.py`, `probe_m1_contact_prepare.py`.

## Local source and actual runtime evidence

Installed PhysX get_jacobians supplies world spatial velocities; floating-base
has six base columns plus sixteen M1 joints. get_gravity_compensation_forces
includes the floating base, unlike deprecated generalized_gravity_forces.
Runtime shape confirmed:[8,17,6,22] Jacobian and[8,22] gravity compensation.
Masses differ per env40.06..43.84kg because inherited mass randomization remains
active with fixed seed2. This is recorded, not a nominal-identical robot claim.

Read-only GPU7 audits after32 standing steps, --num_steps1 --dynamics_audit
(CLI flags and values separated by spaces), flat8 seed2, no lift or efforts:

1. /tmp/m1_dynamics_audit_20261007.log, native0. Raw Jacobian weighted by mass
   reproduces gravity compensation within3.052e-5; erroneously adding origin-to-
   COM correction gives2.46..2.92 residual. Base translation block exactlyidentity.
   Raw wheel linear Jacobian differs from independent double-precision M1 FK
   central difference by~.007845. These results identify COM rather than link
   origin as the linear-velocity point used by this runtime.
2. /tmp/m1_dynamics_origin_audit_20261007.log, native0. Convert via
   J_point=J_COM_linear + cross(J_angular, point-COM). Wheel-origin Jacobian now
   agrees with M1 FK derivative within8.045e-5 for all8rows. Gravity audit unchanged.

No force commands were applied. The mismatch was discovered while preparing a
new dynamics path; older position-only lift did not use these Jacobians, so this
does NOT prove that its failure was caused by Jacobian convention.

## Reusable conversion and tests

Added point_linear_jacobian with explicit[B,L,6,D]/[B,L,3] shapes, matching
dtype/device, finite evidence checks, preserved DOF ordering. Three RED tests
failed because module absent; GREEN covers rotation sign/point offset, identity,
translation invariance, and malformed/nonfinite data rejection. Full12-file
focused suite95 passed in5.88s, exit0 (previous11 plus test_m1_dynamics.py).
Final probe consumes this helper rather than a copied formula. Its static-effort
telemetry is explicitly a wheel-center-force proxy, not an effort command or
complete inverse dynamics: contact moments/actual contact points/inertia remain.

## Final smoke and next gate

Final module smoke:/tmp/m1_dynamics_module_smoke_20261007.log,native0;
helper-linked runtime retains maxwheel-origin derivative error8.045e-5 and
gravity error3.052e-5. Still no lift or extra effort command.
Next: independently test bounded support-force allocation and tau=g-J^T f,
including floating-base residual, inactive contact, infeasible unilateral load,
torque limits, named-joint mapping and ramp/reset ownership before applying
anything. Gravity-only compensation is not enough to claim support of body load.
Then bounded physical standing/individual lift gates; full crossing/recovery/
landing/collision/video/bypass/PPO remain unverified. No long training or push.

## Resources

Exact own placeholder762874 restored784570 for first audit;784570 restored794477
for origin audit. Other user ldc3227360 remains alive. Final module smoke uses
794477 and restored809511, verified alive. No driver/display/reset or unrelated job changes.
