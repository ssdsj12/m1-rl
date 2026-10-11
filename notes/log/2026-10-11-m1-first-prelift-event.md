# First nonzero prelift count in the replacement-host run

## Purpose / scope / method

Read-only monitoring of [T306](../todo/T306-m1-ame-long-train-stability.md),
`pure-ppo-learning/host-resume`; [deployment](2026-10-11-m1-host-resume.md).
2026-10-11 03:09UTC: verified PID948 cmdline/cwd on host
a21472797434572800304964;2048env/currentmodel1000 resume remains running.
GPU21862MiB,stdout1045,remoteTensorBoard through1047,stage1/loss finite.
No new checkpoint yet, no stop/restart/native probe or production modification.

## New evidence

TensorBoard raw prelift_events1001--1046 contains exactly one nonzero sample:
iteration1030 value1. Stdout1030 independently prints1.0000. This is a count,
not rounded mean or normalized progress. Wrapper sums environments and runner
aggregate_metric sums rollout snapshots. Source check: single_prelift requires
before-overlap targetwheel ungrounded, wheelbottom>=lastloadedbottom+.02,
exactly3grounded wheels, not failed/colliding, and not previously rewarded.
Local/server dynamictracker and aggregation source hashes match:
fdcc2c6f86f98009ee7c1066e095c2e00185163c081097260e347dd5c265247e,
85ca3dcf2c0f30c858b5ce3be351f0c6013414298994ee0f69e176a7c8b0b2e2.

Raw progress_delta maximum1001--1046=2.33801929425681e-5 (1005);
at1030=7.953531167004257e-6. These are normalized progress, not meters.
Stablelandings stays0 through1046; curriculum strictsuccesses0 through1047.
The1030 rollout also has collision_frames8,clearance_samples40 and worst
bottomclearance=-.0314m, below required+.03m. Aggregates do NOT identify
whether the same environment/attempt generated both prelift and collision.
No video/trajectory confirmation of this specific event exists yet.

## Conclusion / follow-up / refs

One measured event is the first new >=2cm prelift signal observed in this run,
not stable learning, successful clearance, stable landing or10cm mastery.
Continue training and observe repeatability/strict recovery; preserve current
checkpoint lineage and no-concurrent-native rule. Do not stop for one sparse
event or use historicalmodel900 replay as current-policy diagnosis.
Baseline/Candidate:260b3a1;LastFeature/VerifiedFeature5a366ff unchanged.
Key files:currentrunTensorBoard/stdout,m1_dynamic_crossing.py,
m1_required_crossing.py,ame_env_wrapper.py,on_policy_runner.py.
