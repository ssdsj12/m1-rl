# Dense model600 complete-window audit

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),
pure-ppo-learning/prelift-repeatability and related forward-progress-regression.
Previous [403 audit](2026-10-11-m1-dense-prelift-repeatability.md).

## Evidence 06:47UTC, read-only

PID4921 cmdline/cwd still correct,2048env/GPU0/run13-17-21,21868MiB.
Raw TensorBoard301–640:340 finite value/surrogate-loss samples,stage1 throughout.
Prelift events301–403=18;404–600=2035 across166/197updates;
601–640=198 across36/40updates; total2251 across213updates.
stable_landings and strict_successes remain0 across all340updates.
Recent prelift rate is lower than404–600, so do not claim monotonic improvement.
640 raw normalizeddelta1.765576598700136e-5,routepenalty.9251894354820251.
Lower value loss/reward changes are not proof of progress/crossing.

CPU validation of currentrun model600: SHA
c4bd276ee7202a50c4fc15840df09032c2c01043a3de64ef59d42c388864ee59,
iter600/next601,39finite weights/33finite optimizer states/16positive std,
stage1/streak0/pending0,CUDA uninitialized. Policy learned std values retained,
leg.0368066–.0621652,wheel.155558–.1643844,not manually changed.
PT.last is a complete2048-episode window:forwardpass0,velocityerror
.26607298060836393,3106strict attempts,0successes. This differs from model400's
complete-windowpass.197265625 and is not a partial-window display artifact.
It indicates forward-task regression, not a proven specific posture/collision
cause; no current trajectory/video diagnosis exists. Scalar metrics cannot
establish whether low progress is standing, circling or lateral avoidance.

## Action / interpretation

User directed long training and autonomous exploration; no numerical crash,
no stop/restart/nativeprobe/reward/std/controller change this turn. More prelift
events have not converted into strict clearance/stable landing. Follow complete
windows and latest saved policy, not historical600 from a different run.
If this persists, seek current-policy trajectory evidence at a safe saved
boundary; never run native concurrently with the22GB training process.
Notify once of current early-event growth plus complete-window regression;
do not repeatedly notify unchanged zero-success state.
Source:raw EventAccumulator,stdout cross-check,existing CPU PT validator.
LastFeature/Verified6960a4b; production unchanged; localmonitor notes uncommitted.
