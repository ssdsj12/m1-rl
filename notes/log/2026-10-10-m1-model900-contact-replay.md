# T306 / model900 current-policy contact diagnosis

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
`pure-ppo-learning/required-crossing/policy-contact-stall`.
Baseline: implementation0286e95, published notes3cc82b3; server HEADbb57e7d
plus deployed persistent reward. Candidate: no production change.

## Safe checkpoint and pause

2026-10-10 23:30 CST: TensorBoard raw601--913 (313 iterations) had maximum
prelift_events0 and stable_landings0. Raw incremental progress maximum was
0.0002363998064538464, not exactly zero and not a distance in meters.
Clearance samples do exist (maximum rollout25676); do not call all samples zero.

CPU validated current run model_900.pt:5,911,163bytes,iter900,next901,
finite model state, optimizer33 state entries,16 finite standard deviations,
curriculum version1/stage1/streak0. PT `last` is a complete2048-episode window:
forward/full-episode pass.7333984375,strict64 attempts/0successes. This is not
the mixed pending-window scalar described in the [telemetry audit](2026-10-10-m1-curriculum-metric-window.md).

Checkpoint: logs/rsl_rl/m1_cross_large_complex_ame/2026-10-10_22-09-27/bb57e7d/model_900.pt.
Exact PID14800 cmdline/cwd and PT were rechecked before SIGINT. Process exited;
GPU0 returned to1MiB. No force kill or unrelated process manipulation was used.
Training is PAUSED for current-policy diagnosis, not completed. No old watcher
or old checkpoint lineage may restart. Eventual authorized same-lineage resume
is next901 +9099 updates to total10000,2048env,optimizer/std/curriculum retained.

## Current diagnostic execution

After GPU release, PID15658 launched the unchanged
[contact collector](../../Go2Pvcnn/scripts/probe_m1_policy_contact.py),
model900,stage1,4 diagnostic environments,seed42,mean and sampled actions,
1000 steps each,eval/frozen BatchNorm. This is not training with fewer envs,
not an exact reproduction of2048-row train-mode BatchNorm statistics, and not
a controlled successful action demonstration.

Artifacts: /tmp/m1-contact-replay-900.jsonl and .log.
Temporary CPU reduction: /tmp/m1-audit-contact900.py (local parent directory
copy); it excludes auto-reset frames and released post-state rows from bound
encounter statistics. Production rewards, terrain, controls, std and success
thresholds were not modified. Final2003 JSONL records and COMPLETE marker were
verified, both15658 and14800 absent, GPU0 back to1MiB. No training is running.

## Measured current-policy results

Each mode has3996 non-reset environment-frames. All8 environment/mode pairs
had zero2cm prelift events, strict crossings and recovery completions. This is
not merely four-decimal printing. Mean env2/3 have3/4 actual attempts; mean0/1
and all sampled environments have none.

| Mode/env | Attempts | Before selected-airborne/three-other-loaded frames | Root mean(m) | Max joint error mean(rad) |
| --- | ---: | ---: | ---: | ---: |
| mean0 | 0 | no encounter | .553875 | .562476 |
| mean1 | 0 | no encounter | .553095 | .557850 |
| mean2 | 3 | 0 | .552752 | .548036 |
| mean3 | 4 | 5, only2 with finite loaded reference | .552467 | .546468 |
| sampled0 | 0 | no encounter | .554351 | .557326 |
| sampled1 | 0 | no encounter | .553977 | .554685 |
| sampled2 | 0 | no encounter | .554322 | .558930 |
| sampled3 | 0 | no encounter | .554414 | .557056 |

Mean3 only earned total0.1453001 normalized progress units (~.04359 bonus),
not a successful lift. Its finite-reference safe single-wheel before-rise
maximum is5.961mm. Mean2 maximum before-rise is.588mm. Mean3 has one rear-wheel
encounter that begins airborne and never acquires a loaded reference before
overlap; that encounter correctly cannot establish actual rise from contact.

First failed attempts (mean2 step305,mean3 step303) enter overlap with no
early_lift: wheel bottoms -.000873m/-.001953m and top .03m, so top clearances
are -.030873m/-.031953m. Both collision flags/geometry and non-support contact
terms are zero at this first failure. The strict gate fails for real low wheel
position and missing early lift, not a spurious collision preempting a lift.
Later wheel-on-block bumps cannot certify pre-contact lift.

The body is about9.7cm above nominal root .4560008m; that is NOT wheel lift.
Sampled low-contact-force wheel bottoms can reach3.44cm away from any eligible
obstacle, sometimes with multiple wheels unloaded. Such motion is not rewarded
or counted as a single-wheel crossing. Instant contact<10N alone is not proof
of clearance or loss of all physical support.

Independent lane audit: mean1 front/rear wheel-center spacing changes from
.414/.413m atstep0 to.291/.297m at20 and.268/.270m at100. Knee delta is roughly
-.52..-.57rad with ABAD inward deviations. Stance NARROWS, not widens. No
controlled joint/pose counterfactual was run, so no single-joint causal claim.
At FBL X closest to first block2.9m, rootY is -.5205/-.2249/-.0908/-.0334m for
mean0..3 and -1.6663/-1.1322/-.8302/-.5439m for sampled0..3. Actual FBL Y for
mean0/1 is -.5011/-.1220m versus authored obstacle+.215m. Missed lanes are real.

## Remaining directional penalty hole and bounded proposal

The persistent positive-reward repair remains effective: all980 mean-mode
post-last-slab frames have nonpositive final PPO reward, sum negative; zero
strict receipts. This is NOT recurrence of the old finite-slab positive exploit.

However existing `m1_small_obstacle_corridor_penalty` calls instantaneous
`m1_obstacle_presence` and returns zero when small is no longer scanned.
Mean0/1 have814/682 frames with abs(rootY)>.22m but ZERO corridor penalty;
sampled0..3 have849/836/838/705 such frames and ZERO corridor penalty.
Mean2/3 do receive152/74 penalty frames, so this is not globally disconnected.
The scanner-gated penalty fails specifically along bypassing trajectories.
Removing positive forward shaping after approach does not itself supply a
directional cost that guides the policy back toward the authored wheel lanes.

Bounded reward design presented for confirmation, NOT implemented: stage1--3
route penalties use live authored course/origin and persist until required
receipts, independent of immediate small-obstacle visibility. Preserve all
existing no-sliding-positive constraints, measured lift/high-water rewards and
strict2cm/3cm success gates. Stage0 and freely routed mixed4 remain unchanged.
Replay the recorded bypasses as failing regression cases, test state/episode/
terrain transitions and no-lift-no-success, then native wiring before same900
resume. Exact lane tolerances/weights require design review; do not simply
assume old22cm band guarantees contact with narrow blocks. No new pose clamp,
manual std, force/servo/controller intervention is proposed. Fixing route
exposure alone is not proof that PPO will learn the single-wheel action.

Under brainstorming bounded-design gate, await confirmation of this new
reward behavior. Do not blindly resume unchanged training or keep adjusting
unrelated coefficients. Real single-wheel exploration/support and learned10cm
crossing remain separate OPEN questions, not solved by these measurements.

## Gate audit

Incremental prelift requires a bound encounter, before-near-edge lane overlap,
selected wheel contact norm<=10N, exactly three other measured loaded wheels,
unfailed/collision-free state, finite loaded baseline and newly exceeded world
bottom high-water. It does NOT require2cm rise or nominal-pose recovery first.
Thus failed recovery pose alone cannot explain zero incremental learning signal.
High-water also advances on loaded/unsafe rise, avoiding retroactive reward.
An already failed/used encounter cannot earn by lifting after contact.

Collision telemetry combines geometry and non-support contact reward terms;
it is not a wheel-only PhysX collision inventory. Wheels can hit/roll on a block
with collision=false, but insufficient per-overlap wheel-bottom clearance still
fails strict crossing. Wheel contact force below10N alone is not proof of lift.

Pure PPO and585mm initial geometry retained. Actual10cm crossing remains OPEN.

23:42 CST heartbeat: no human design confirmation received. Read-only process
check found neither training nor contact probe, checkpoint900 still5,911,163bytes.
Corrected the stale notes/index.md headline to point at this paused state;
production code and processes unchanged. No repeated approval notification.
