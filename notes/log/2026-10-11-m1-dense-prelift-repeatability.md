# Dense-layout repeated prelift signals, no strict recovery yet

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md),
pure-ppo-learning/prelift-repeatability. [Deployment](2026-10-11-m1-lift-roll-self-learning.md).

## Read-only evidence, 05:46UTC

PID4921 cmdline/cwd still correct: production contact-recovery,
run13-17-21/bb57e7d,2048/cuda0/model300/9699/keep_std. GPU21868MiB.
TensorBoard raw scalars301–403: all103 value/surrogate losses finite,stage1.
prelift_events nonzero at320:1,322:4,323:3,347:2,366:1,375:1,
384:1,385:1,386:2,390:1,392:1. Total18 events across11 updates.
Independent stdout parser through403 gives exactly the same list/sum.
Counts are environment+rollout sums, not average heights. Existing definition:
single wheel bottom at least2cm above lastloaded before overlap, other3grounded,
not yet failed/colliding, not previously rewarded. No per-event video obtained.
stable_landings and curriculum strict_successes are0 for all103 updates.
Maximum raw normalizedprelift_progress_delta=.00034942393540404737;
403 rawdelta=.000015978075680322945, not meters or strict success.
Routepenalty403=.14499019086360931; reductions alone do not prove crossing.

## Saved checkpoint

Currentrun model400 CPU validated (CUDA uninitialized):iter400/next401,
39finite weights,33finite optimizerstates,16positive std,stage1/streak0/pending0.
SHA47889a881362023852693fb5b999ba48a0ee3bab7515e6e42240b086317d53ac.
PT.last is complete2048 episodes:pass.197265625,velocityerror.18460567407931305,
7126strict attempts,0strict successes. Forwardpass is not crossing success.
Policy std increased through PPO:leg.0170713–.0277493,wheel.0989633–.1057664;
no manualstd edits. No stop, restart, nativeprobe or production code change.

## Interpretation / next step

Repeated >=2cm prelift signals are substantive early exploration evidence,
not proof of stable learning or completed3cm/10cm crossing. Continue authorized
training; observe strict overlap clearance and stable recovery. User notified
once of18events/11updates; do not repeat this same evidence on future heartbeats.
Current checkpoint for any later authorized recovery is newest validated PT in
thisrun, not an automatic return to source300. No restart while4921 is active.
LastFeature/Verified6960a4b, documentation baselineb244024. No new implementation.
Tools:read-only EventAccumulator, stdoutparse, existing CPU checkpoint validator.
