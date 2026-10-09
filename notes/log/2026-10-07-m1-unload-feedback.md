# Measured-contact unloading reference

Parent:[T306 measured-unload-control](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:d6ed585; Candidate Ref:commit containing this log.
Key files:m1_unload_reference.py,test_m1_unload_reference.py,probe_m1_contact_prepare.py.

## Change versus baseline

Optional selected-wheel reference feedback uses .0002m/(N*s)*(force-5N), speed
bounded.01m/s,height bounded.02m. It holds when unloaded, rejects invalid input;
IK/limits/.5rad/s joint slew, pose/contact/allocation guards remain. Other wheel
anchors/root reference fixed. Achieved commanded unload height carries into LIFT,
not reset tozero. Not integrated into training, no success based on reference.

## First test

Three missing-module RED tests then GREEN; focused16files115passed5.08s.
Flat8seed2 GPU7,100PREPARE+100UNLOAD budget+200LIFT budget; --unload_feedback added
to existing phase-effort command (speed.04,bound.08,load floor enabled).
Raw:/tmp/m1_unload_feedback_20261007.log,native0. Stopsunloadstep14 allocation
row6invalid; about2.8mm reference. Target effort still8..12Nm away. Zero LIFT.
Own1081679 restored1113188. Other ldc3227360 no longer present on later read;
this task did not operate on that process. Do not claim it remains alive.

## Timing correction and second test

Add per-row effort_settled input; initially false, then prior UNLOAD effort gap<=1Nm
required before reference advance. REDunexpectedkeyword then GREEN,116focusedtests
pass5.35s. Same physical command andbounds, raw:
/tmp/m1_unload_settled_feedback_20261007.log,native0.
Stopsunloadstep68 allocationrow4invalid,0LIFTsteps. Selectedforces18.30..31.18N,
reference1.78..4.21mm, effortgap.004..017Nm. Improved unloading but no5N readiness.
Both runs clear=true. Own1113188 restored1125373 and verified alive.

## Next

New child coordinated-unload-com under measured-unload-control: selected-leg
shortening changes support geometry/COM during unloading, but root command was
fixed at PREPARE exit. Apply existing bounded mass-aware root transfer concurrently
with held/advancing unload height, preserve original entry bound and fixed stance
anchors. Verify live load feasibility before advancing, not larger gains or lower
30N/5N thresholds. Then actual lift/crossing/recovery/landing/bypass and PPO gates.
No long training, upload, display/driver changes or GPU reset.
