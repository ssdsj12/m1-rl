# 2026-10-08 M1 rolling support substep attribution

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), baseline3e44adf.

## Improvement

Extend existing default-off roll_substep_audit with native named wheel normal
forces, mass-weighted whole-body COM velocity and root angular velocity for all
eight environments. This is read-only instrumentation, no actuator or gate change.
RED missing com_velocity; GREEN153 regression tests. The test executes the actual
nested observer with nonuniform masses and reordered named wheel indices.

## Physical verification

Same GPU7 bounded command as continuous-ramp comparison plus roll_substep_audit.
Exit0; stops at global96/ROLL6 rolling_support_rejected, no landing/crossing.
Every lift_samples field exactly equals the baseline, confirming observer did not
change this trajectory. Placeholder4102845 stopped after verification;
4135886 restored and verified sole GPU7 compute process. No training.
Raw `/tmp/m1_roll_substeps_20261008.log`, full local artifacts copy.

## Evidence

Whole-COM central differences at20ms through step95 predict only small inertial
load differences (row7 FBL static43.255N versus zero-angular-momentum43.240N at95).
This approximate model cannot explain the next endpoint12.214N; do not treat it
as a controller or exact inverse dynamics (omits angular momentum).

Native5ms samples during executed action95, row7/FBL support:
43.8025,43.9282,46.2919,12.2139N.
Last-substep COM velocity changes
[.00625684,-.00181037,.01002853] to [.00638912,-.00014080,.00571662]m/s.
Thus actual vertical acceleration approximately-.86238m/s2, lateral+.33391m/s2.
Root angular velocity changes [-.0188291,-.0149749,.0105535] to
[-.0494314,.0023380,.0162553]rad/s over5ms.
This is a physical short-timescale transient, not altered cached reporting.
Earlier three samples being healthy does NOT justify averaging away the guard.

## Architectural next action

Do not implement feedforward COM compensation from the low-frequency root or
COM estimate alone. Resolve contact/actuator coupling at the final substep:
native contact patches/friction, wheel velocity/effort, stance joint PD and
angular-momentum response. Existing data establishes timing, not unique cause.
No threshold relaxation, scalar gain sweep, obstacle success or training claim.
