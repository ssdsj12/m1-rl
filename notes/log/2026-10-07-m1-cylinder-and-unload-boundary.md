# Cylinder comparison and final UNLOAD observation fix

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), loaded-contact child.
Baseline Ref:c3a7a2a. Candidate Ref:containing commit.
Key files:m1_wheel_collision_probe.py,m1_rolling_speed.py,
probe_m1_contact_prepare.py and cylinder/selection/unload-boundary tests.

## Diagnostic scope

Allow existing opt-in cylinder profile for complete lift/land diagnostic, not
just standing. No phase budget/contact/pose guard relaxed. Source USD unchanged.
Add optional selected_leg to isolate one leg across8rows; None retains four-leg
coverage. Do not substitute onelegcoverage for allleg acceptance.

## First two physical probes

Matched fixed-physics baseline,5ms,gain5,90lift/20roll/90land/100settle,
rearreserve40/front35,only shoulder->cylinder. Raw:/tmp/m1_cylinder_lift_20261007.log.
Mixed-leg8env exits0 with unload_timeout,0LIFT; only RBLrows2/6 reachstreak5.
Mass/inertia/material JSON exactly matches rear-preload-drive baseline.
Cylinder therefore untested forrolling at this point, not a rollingfailure.

Then selected_leg2 RBL-only, same otherwise. Raw:/tmp/m1_cylinder_rbl_20261007.log.
Again timeout, row0streak4 while otherrows>=5 atpreaction99. Code executes
action100 but never consumes its new observation before declaring timeout.

## Actual bug fix / tests

At natural budget exhaustion only, consume fresh final postaction observation,
recompute static allocation and effort error without applying new effort/action,
check actualcontact/pose/non-supportcontact and increment/reset streak once.
Still require5consecutive fresh frames,100actions/2smaximum, existing thresholds.
No extra action or duplicate staleframe. Any earlier safety/reset failure still
bypasses this check. This corrects timing, not physics acceptance.

RED cylinder1failure/selection5/boundary1; GREEN final49passed1.72s including
unload gate, boundary, selection, geometry and rolling regressions.

## Matched bug verification and rolling result

Raw:/tmp/m1_cylinder_rbl_boundary_20261007.log; session24783 terminalexit0.
M1_UNLOAD_FINAL_CHECK executed_actions100, allreadytrue,
streak[5,7,6,6,6,6,6,6], fresh efforterror .0193.. .0209Nm.
Selectedforces2.14..2.28N, remaining support>=36N atthatboundary.
No extra action was required to pass readiness.

Then actual lift and12rolling actions occur; atpreaction102,
stopped=rolling_support_rejected, allIKvalid/reason0, minFARsupport29.372N<30.
Measured rise .154830.. .154844m. Rootprogress-.685..-.697mm, no effective travel.
This cylinder candidate is not a solution; it also weakens support. Physical
success remains false even though shell exits0. No realobstacle/video/training.

## Next / resource state

Retain source assets and defaultdiagnostic settings. Loaded-contact/wholebody
dynamics remains unresolved; do not infer that another arbitrary tire surrogate
or rewardweight will fix it. Boundaryfix is retained independently of cylinder
failure. Further work must preserve actualenvelope and contact evidence, not
relax safety or count process completion/airborne spin as crossing.
Placeholder exact lifecycle2786123->2808766->2823659->2857178, finalverified.
No display/driver/unrelatedGPU or dirtyoriginal checkout changes.
