# Matched standing feedforward comparison

Parent:[T306 leg-only-standing-comparison](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:d4074c9; Candidate Ref:commit containing this log.
Key file:probe_m1_contact_prepare.py. Diagnostic contract changes: replace
all-joint tracking_error with named12-leg leg_tracking_error, and add binary
--standing_effort_gain0/1 (CLI flag/value separated). Default gain1 unchanged.

## Evidence

Focused14-file regression107 passed in5.37s. Two sequential GPU7 flat8 seed2
experiments,32 warmup +100 standing steps each. Both use --headless --device cuda:0
--num_steps1 --standing_effort_steps100 with gain0 then1, all values separated.
Raw:/tmp/m1_standing_compare_0_20261007.log and
/tmp/m1_standing_compare_1_20261007.log. Both native0,100 samples,stopped=null,
cleared=true. No concurrent duplicate probe/training.

Final per-env maximum12-leg position error:

- gain0:[.03903,.04095,.03751,.03893,.03967,.04000,.03675,.03894]rad.
- gain1:[.02077,.02156,.02012,.02079,.02096,.02138,.01970,.02077]rad.

All8 improve, approximately46..48% reduction. Trace mincontact79.84N(gain0),
79.00N(gain1); maxaxis tilt.009302rad in both (includes initial standing state).
These are matched standing results, NOT proof of dynamic lift or crossing.
No independent physical torque measurement claimed.

## Next action

Leg-only-standing-comparison has positive evidence. Next child:feedforward-phase-
handoff, integrate guarded named efforts during PREPARE and LIFT without stale
PD/target use, abrupt contact-mask switch, or effort left across reset/exit.
Then actual8-environment single-leg lift and full obstacle gates. Do not promote
to training until actual rise/support/landing/collision criteria pass.
Own placeholder restored after both tests; other user ldc3227360 remains alive.
No display/driver changes, long training or upload.
