# Phase-isolated wheel drive gain comparison

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), traction child.
Baseline Ref:a72b16f; Candidate Ref:containing commit.
Key files:m1_rolling_speed.py,probe_m1_contact_prepare.py,test_m1_roll_drive.py.

## Evidence motivating the test

Prior env3 step100 main FAR/RBL wheels carried~189/170N, with estimated drive
1.47/2.01Nm, no50Nm clipping. Actual patch normal moments about axle were
.09/-.04Nm at that snapshot (not total contact moment or dynamics balance).
Velocity targets were positive, actual instantaneous velocities did not imply
sustained angle change. Drive-gain adequacy remained a falsifiable hypothesis.

## Change / contract

Add default-off --roll_wheel_damping5|20 diagnostic. Nondefault requires bounded
roll cycle and fixed physics. Keep baseline5 duringPREPARE/UNLOAD/LIFT, apply20
onlyatROLL, restore5beforeLAND/SETTLE. Use Isaac articulation damping write API
and update implicit actuator estimator damping together; print actual backend
array at transitions. No position stiffness, friction, torque limit, source
asset or production training change. This is diagnostic, not a claimed fix.

## Tests

RED2 missing helper/flag; GREEN16focused. Full focused load-transfer, reserve
wiring, moving-load,COMtrajectory,single-lift,settle,roll-drive,rolling-speed,
rolling-reference suite90passed13.14s. git diff check clean.

## Physical verification

Same prior8env seed2 no-obstacle fixed-physics shoulder baseline, .1cap20step
ramp (actualpeak.036), rearreserve40/front35,90lift/90land/100settle; only add
--roll_wheel_damping20. GPU7/cuda0, max300s; shell session98235 exited0.
Raw:/tmp/m1_roll_drive_gain_20261007.log, local roll-drive-gain.log.

Backend transitions show20allwheelDOFs atstep90ROLL and5at110LAND.
stopped=null; landing_complete=true; finalstep244;8/8streak5.
Minimum rolling support33.42443N. Last rolling progressmm:
[-.953934,-.048317,-1.150949,-.829685,-.946330,-.042088,-1.149241,-.831611].
Step100 loaded-wheel drive estimates broadly4..10Nm (e.g env3
FBL2.452,FAR5.514,RBL7.753; env2RBLselected excluded, FAR6.183,RAR10.491).
Sampled netangles still tiny; best env3FBL.016981rad, many .001.. .004rad.
No effective traversal. Estimated torque is not directly measured full-step
motor impulse, and sample qdot is instantaneous; do not treat as torque proof.

## Decision / next

Higher gain does not restore locomotion in this window. Keep default5 and no
further speed/gain-only escalation. Investigate constraints and substep angle /
velocity consistency to distinguish contact projection from actual wheel motion.
The stable three-support baseline is useful but cannot substitute for full
source-geometry obstacle crossing/clearance/landing/avoidance/video/policy gates.
No training. Exact placeholder2623404 stopped,2662902 restored and verified.
No unrelated process/display/driver or original dirty checkout changes.
