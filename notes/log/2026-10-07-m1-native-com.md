# Direct native-pose COM verification

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), anticipatory-support.
Baseline Ref:6f391fd. Candidate Ref:this commit. No control-law change.

## Change and tests

Probe LIFT/ROLL records direct root_quat_w, named body_com_w in addition to
existing joints/root/wholeCOM. AST telemetry contract observed RED (missing
root quaternion), then GREEN; telemetry and lift-mask tests3passed.
Read-only replay uses direct quaternion instead of wheel-fitted attitude for
independent body and whole COM comparison. Original fit retained separately.

## Physical comparison

Exact baseline flags from current-SDF load-feedback comparison, GPU7 only,
eight environments,100PREPARE/100maxUNLOAD/90LIFT/20maxROLL steps,
sourceSDF128/rest1mm, phasewheelhold, unloadcomramp, rollloadfeedback/comtrajectory.
Raw `/tmp/m1_native_com_20261007.log`; session60341 terminalexit0.
Stopped rolling_load_proposal_rejected as baseline,99phase samples/792rows.
All force, actualjoint, root, wholeCOM and targetheight arrays exactly equal
baseline `/tmp/m1_sdf_load_feedback_20261007.log`; equal lengths verified.
Direct wholeCOM maxerror4.26517377e-6m; direct individualbodyCOM max3.66561472e-6m.
17body/16joint authored model agrees with native at these recorded poses.
Own placeholder134617 stopped after exact command check; restored424671 verified.

## Conclusion and next

This closes wheel-fitted-attitude ambiguity for the replayed poses. Next tested
candidate joint/root predictor and anticipatory support reference within original
bounds. Agreement is kinematic, NOT dynamic support or obstacle-crossing proof.
Current rolling support rejection remains; no training/learned-policy claim.
No display/driver changes, no other GPU operations. Notes synchronized.
