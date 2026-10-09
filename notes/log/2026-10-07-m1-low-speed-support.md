# Low-speed shoulder-model support comparison

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), rolling-support-control.
Baseline Ref: 0ed471e. Candidate Ref: containing commit.
Key files: probe_m1_contact_prepare.py, test_m1_roll_speed_cli.py.

## Hypothesis / scope

Test whether reducing the existing rolling speed cap alone preserves the weak
support during a complete shoulder-model lift/roll/land diagnostic. This is a
flat diagnostic, not obstacle acceptance or a production tire change.

Readback of prior /tmp/m1_shoulder_cycle_20261007.log: all eight rows have negative
forward progress (-0.509..-0.918 mm) at step102. Row3 lifted RAR and its FBL support
dropped from35.437N at roll entry to29.982N. Measured reference transport exists,
but there is no live COM/load redistribution in the rolling branch. Existing
lift_support_transfer cannot simply be enabled with world-frame rolling.

## Change / tests

First attempt failed CLI parsing before simulation (only0/.1 accepted), log
/tmp/m1_shoulder_speed002_20261007.log. Placeholder restored automatically.
Added only .02m/s to diagnostic choices; default.1 and upper limit unchanged.
Actual CLI declaration executed in regression test: RED1 failure on invalid
choice, GREEN13tests pass1.42s (CLI, rolling-speed, reserve wiring).

## Physical procedure / evidence

Same8env seed2 shoulder cycle as previous log: M1_OBSTACLE_STAGE=none,
PREPARE100/.04/.08, phase_effort, UNLOAD100/feedback/COM/force0/minspeed.003/
world_pose/vertical_only, LIFT90/.16/.12, ROLL20/ramp, LAND90/search.005,
SETTLE100. Only runtime difference --roll_speed .02 (previous cap.1; short
baseline ramp actually peaks.036m/s, not.1).
Raw: /tmp/m1_shoulder_speed002_physics_20261007.log. Process exit0, but physical
result stopped=rolling_support_rejected, landing_complete=false, step104.
15 pre-action rolling samples imply14 executed rolling actions, vs12 baseline.
Row3 FBL29.921N violates unchanged30N floor; row7 counterpart30.300N.
All eight progress values remain negative (-0.515..-0.845mm).

## Conclusion / next

Lower cap alone delays rejection by only2 actions; it does not restore support
or forward traversal. Do not promote lower speed as a fix, weaken30N, extend
airtime, or start training. Next moving-reference/control audit must account for
measured load redistribution and three-support wheel traction, especially rear
leg lifts. Static8/8lift/land remains distinct from successful traversal.
GPU7 placeholder2299107->2325171(parser attempt)->2339056(physical probe);
final exact own process verified. No unrelated processes/display/driver changes.
