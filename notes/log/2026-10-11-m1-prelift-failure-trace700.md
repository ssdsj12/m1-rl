# model700: first measured failure after prelift

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),
pure-ppo-learning/forward-progress-regression/attempt-failure-trace.
Follow-up to [aggregate diagnosis](2026-10-11-m1-zero-crossing-diagnosis.md).
User requested the concrete reason an actual lifted wheel fails.

## Safe boundary and unchanged contracts

The one-shot helper validated current run13-17-21/model700 on CPU before sending
SIGINT only to the freshly identified PID4921. Both exited, GPU returned1MiB.
Checkpoint SHA256 ef9e9833040ca93a6932a24001cc5ddddb817007cfec574ef1cfb2ac1fe40d7d;
iter700/next701,39finite weights,33finite optimizer states,16positive std,
stage1/streak0/pending0. PT.last complete2048 episodes:pass0,462attempts,0success.
No rollback to300/600, no change to rewards/controller/std/585mm/strict gates.

Diagnostic scripts live outside production under /tmp/m1-*trace*20261011.py.
Hooks copy actual outer/inner tracker inputs and states, including first-failure
conditions, measured wheel bottoms, forces and route alignment. Four CPU parity
cases (valid, support loss, low clearance, early touchdown) reproduce identical
tracker outputs/state with and without hooks. No forced actions or PPO updates.

## Replay conditions and completeness

First:64env,seed42,eval/frozen BatchNorm,mean/sample1500steps each.
Mean67attempts/0prelift/0crossings;62first fail low-clearance plus missing early
lift,5no failure observed. Sampled18attempts/0prelift/0crossings,all18leave the
encounter. This small evaluation replay did not reproduce training prelift.
Artifact /tmp/m1-prelift-trace700-20261011.jsonl:3005records plus COMPLETE log;
PID6047 exited before the next native process. Not a substitute for training
batch/BatchNorm conditions.

Second:2048env,seed42,1000steps sampled,model.train(),actor then critic forward
as in PPO rollout,without gradient/optimizer updates. BatchNorm buffers evolve
only in the disposable process, never saved to checkpoint. This is a fixed
policy diagnostic from reset, not an exact historical training trajectory.
All2048 environments simulated; detailed trace selection starts on actual
prelift events (max128 environments,only1selected), not forced motion.
PID6254:310attempts/1prelift/0crossings/0recoveries.1003JSONL records/COMPLETE,
process exited/GPU1MiB before training resume. Terminal rows excluded.

## Matched sequence: sampled env283, obstacle3300, wheel0 FBL (left front)

Same encounter, no reset, no collision flag or non-wheel contact force:

| Step | Relative time | Left-front bottom | Four wheel force norms, FL/FR/RL/RR (N) | Result |
| --- | --- | --- | --- | --- |
|51|0|22.032mm|0/222.676/70.832/128.906|prelift event; unfailed|
|52|+.02s|21.808mm|0/0/0/0|first failure: support_loss only|
|53|+.04s|14.436mm|0/0/95.776/278.087|two rear supports,still failed|
|54|+.06s|.148mm|0/0/52.177/217.439|left front falling back near ground|
|55|+.08s|loaded again|197.438/0/348.866/106.490|premature touchdown also true|

At51 rise from last loaded bottom22.295mm; obstacle top30mm, so wheel bottom
has not reached the60mm required during overlap. It remains246.073mm before
the near edge,244.557mm at first failure52. No overlap occurred anywhere in
this encounter; it releases after lateral departure. The first failure is
not obstacle impact, low overlap clearance, or nominal-pose recovery.

Important telemetry distinction: at the prelift event, matches_lane=false,
target-relative lateral offset151.259mm. single_prelift_event counts an early
rise during a still-bound encounter without requiring current lateral match;
prelift_progress_delta DOES require lane match and is0 at51. This is not a
positive off-lane reward leak. The counter alone is not proof of a directed
crossing lift. Later lateral departure grows past415mm by211.

Measured wheel forces all0 at52 trigger the existing >10N contact definition;
do not claim all wheels rose far into the air. Other wheel bottoms then are
6.067/1.571/-2.097mm. Subsequent samples also lack right-front support, so this
trace does not maintain the requested three-wheel rolling support. The
observed brief lift/load fluctuation/early return is consistent with bouncing
or unstable weight transfer, but exact physical cause of the contact-force
drop is not isolated by a controller/solver counterfactual or video.
Do not extrapolate this single reproduced event to all2281historical events.

## Artifacts / checks

- Full2048 trace:/tmp/m1-prelift-trace700-rollout-20261011.jsonl,
  SHA0afc558f36c48735a2e4e1337e5447468b4aced9d7dbadee82e697229d3b6fcc.
- Reduced trace:/tmp/m1-prelift-trace700-rollout-summary.json,
  SHA55812f5baa3d730f323c3aef7cd8f171548895b1150bb4be706bb80b35151ae9.
- Local ignored copy:results/diag_prelift700/m1-prelift-trace700-rollout-summary.json.
- /tmp/m1-trace700-runtime-manifest.json checked identical checkpoint and eight
  runtime module byte hashes before trace and before resume.

## Resume / open follow-up

After both probes exited and GPU1MiB, guarded launch PID6507 resumes exact700,
next701+9299 to exclusive10000,2048env/cuda0/save100/optimizer1/keep_std/stage1.
Run2026-10-11_15-16-31/bb57e7d;log/tmp/m1-ppo-after-trace700-20261011.log.
07:18:30UTC completed701–702, value losses.0358/.0204 and surrogate.0084/.0026
finite,GPU21868MiB. Cmdline/cwd/environment verified2048/cuda0/9299/optimizer1/
keep_std/save100. TensorBoard6661 remote6006/data/logdir independently matches
new15-16-31 run; old5109 replaced, local16006 not revalidated or modified.
No production changes; original long-training preference retained.

Concrete trace is obtained, but learning problem remains OPEN. Child
attempt-failure-trace/three-wheel-load-loss: explain repeated actual support
loss if further traces show it. Related child off-lane-prelift-telemetry:
keep prelift counts separate from lane-valid rewarded progress. Neither
authorizes changing reward, contact threshold, servo or strict success gates.
Baseline/Candidate feature6960a4b,no feature diff;Current Work Ref
codex/m1-ppo-repair-upload,HEAD b244024 plus uncommitted diagnostic notes.
Key files:existing m1_dynamic_crossing.py/m1_strict_crossing.py and disposable
observer/reducer/lifecycle scripts. Existing monitor notes and old watchers retained.
