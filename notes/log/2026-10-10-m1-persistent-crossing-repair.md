# M1 persistent crossing reward repair

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
`pure-ppo-learning/required-crossing/policy-contact-stall`.
Baseline: cd638f4 implementation / 5af7a29 publication, server HEAD bb57e7d
with the deployed diff. Candidate: this repair; source hashes and final
deployment evidence recorded below. Human explicitly approved repair and resume.

## Contract and bounded scope

The [model600 replay](2026-10-10-m1-model600-contact-replay.md) established
zero strict recovery but positive post-slab PPO reward. Replace the finite
slab gate with an episode-persistent obligation for each approached obstacle.
Required wheels are authored straight-route tracks, not the policy's drift:
M1 order FBL/FAR/RBL/RAR, +Y requires FBL/RBL, -Y requires FAR/RAR.
Both wheels need actual strict recovery receipts for that obstacle identity.
Attempt start, first touchdown, lateral bypass, far exit and retreat cannot
unlock the reward. Future unapproached obstacles do not block flat approach.
Done and registry replacement clear episode state; pre-step snapshot protects
terminal rewards from Isaac auto-reset. Only progressive stages 1--3 use this
gate; empty flat stage0 and freely routed mixed terrain retain their scope.

Actual single-airborne-wheel rise is rewarded through the measured obstacle
top plus required clearance (minimum3cm), retaining .3 per .02m rather than
weakening the millimeter-level signal. First loaded reference freezes target
and budget; world-bottom high-water prevents recontact/bobbing replenishment.
3/6/10cm blocks from zero bottom therefore have maximum .9/1.35/1.95 lift
reward per encountered wheel, not unbounded reward. Loaded climbing never
earns lift reward. >=2cm prelift telemetry and strict crossing remain separate.
Recovery still pays2 only after actual strict crossing and stable recovery.

No changes to controller, actions, std, nominal585mm stance, servos, strict
clearance/recovery criteria, curriculum promotion thresholds, observation
representation or terrain. PurePPO/2048env/GPU0/save100 retained. Resume only
this fresh lineage's model600 with optimizer/std/course, not the old8573 run.

## TDD and isolated verification

- Persistent gate RED8 failures (missing API + full-height increment clipped),
  GREEN8. Actual wrapper pre-step RED1/8passed, then9passed after wiring.
- Receipt/full-height RED29 failures; GREEN55 (36new +19existing dynamic).
- Integrated candidate initially240passed in3.43s; additional mixed-stage and
  terminal/reset integration regression passed10/10 in1.42s.
- Review confirmed slot/wheel captures are independent of inner reset, current
  registry is copied, pre-step reward mask survives auto-reset. Added the
  suggested stage0/1/4 mixed batch and next-episode regression.
- Two further anti-farming RED failures reproduced deferred credit after
  paired-wheel rise (.5 units) and reward on retreat/release (2.5 units).
  Advance observed high-water without paying unsafe rise and mark abandoned
  before payment. Final focused57passed2.27s, final integrated243passed3.43s.
  Independent final code review found no blocking issue.

Staging: /tmp/m1-bypass-integrated; remote CPU Python env_issacsim,
OMP_NUM_THREADS=1 and candidate Go2Pvcnn first on PYTHONPATH.
Full repository baseline still has10 historical collection/dependency errors
documented in [previous repair](2026-10-10-m1-recovery-prelift-pooling-repair.md);
the targeted suite is not a claim of full repository green.

## Saved-real-trajectory counterexample

[CPU verifier](../../Go2Pvcnn/scripts/verify_m1_required_reward_replay.py)
consumed all2003 records from /tmp/m1-contact-replay-600.jsonl. It preserves
saved physical events and deltas, changing only reward gating; this is NOT
a new policy rollout or a geometry reconstruction. Both modes have zero
saved strict crossing/recovery. Legacy actual final reward was reconstructed
within3.73e-8; candidate retains all negative costs exactly.

| Mode | Positive post-slab frames: old -> candidate | Net post-slab reward per environment: old -> candidate |
| --- | --- | --- |
| Mean | 1489/1489 -> 0/1489 | [12.1015,10.3777,12.1838,12.3165] -> [-2.5621,-2.8064,-2.5281,-2.3524] |
| Sampled | 1407/1480 -> 0/1480 | [7.5836,6.5314,6.8811,8.3367] -> [-7.0361,-8.1598,-6.2839,-7.6291] |

No attempt is promoted to success and no negative cost is removed. The old
policy still lacks verified lifting; changing rewards is not instant learning.

## Native verification and deployment

First candidate native mean/sampled1000steps each completed (2003JSONL records),
/tmp/m1-bypass-native-600.jsonl. Actual wrapper reward matched the persistent
contract within2.98e-8. All1489mean and1480sampled post-slab frames were
nonpositive; strict prelift/crossing/recovery remained0. Source module paths
were candidate /tmp/m1-bypass-integrated, not old production. SSH disconnected
during shutdown; completion marker, all records, absent process and1MiB GPU
were independently verified, rather than claiming shell exit0.

The subsequent final-version stage/reset probe initially failed its diagnostic
post-last-slab placement assertion: stage2/3's far end reaches the existing
tile timeout envelope. Retained the training boundary, corrected the probe
to test post-slab placement only in stage1, and reran final-version checks.
This placement failure is not evidence of a CUDA or reward wiring error.
Follow-up node `terminal-obstacle-space`: inspect whether rear-wheel completion
at the last10cm obstacle has sufficient physical room before boundary; do not
weaken the boundary or claim all8obstacles are complete. It does not prevent
resuming the authorized current stage1 learning, but is open before stage3
whole-course acceptance.

Final native passed: /tmp/m1-persistent-final-native.log contains
M1_FLAT_FIRST_RESULT, no traceback; process exited/GPU1MiB before deployment.
Stage0 counts0, stages1/2/3 counts2/4/8 and actual USD heights3/6/10cm;
all5stage/reset paths cleared gate/receipt state.100neutral settled steps
and24near-block plus4post-slab steps passed, observation4x1589. Healthy nominal
recovery4/4 in last20steps. Actual stage1 post-slab rewards were
[-.0064774,-.0080917,-.0070416,-.0061397], blocked1.0, receipts0, no bonus.
This diagnostic placement is not policy locomotion or crossing acceptance.

Deployed final expanded regression260passed5.04s, including purePPO/dense
layout/checkpoint contracts. Production core hashes equal reviewed/final
native candidate and local files:

- dynamic: fdcc2c6f86f98009ee7c1066e095c2e00185163c081097260e347dd5c265247e
- reward: d1c4c2def8e21d98a87e9a2b803b07ceb509780afa1b3bfef8ad7a2075700715
- wrapper: 4588f4276323ca8401e703ba806b7f26ad21302fa157f93151bb6bc91640628f

Scoped rollback backup: /tmp/m1-persistent-backup.0WuNYe. No source hot-patch
of running training, no unrelated process termination. One explicit launcher
revalidates checkpoint600/next601/stage1/finite weights/optimizer, absence of
training/probes, final native marker and GPUfree>22500MiB; existing flock also
prevents duplicate jobs. Resume9399updates/2048env/keep_std/load_optimizer,
flat-first/save100. Actual PID/run and TensorBoard identity recorded next.

Verified actual training PID14800 (cmdline/cwd and /proc environment),
run2026-10-10_22-09-27/bb57e7d, /tmp/m1-ppo-persistent-crossing-20261010.log.
Actual observations2048x1589/1592,16actions; controllerPPO,mpc_teacher disabled,
imitation0. Iterations601 and602 completed; GPU0 21922MiB, no CUDA/OOM/traceback.
The log embeds the three source hashes above. Starting at601, not fresh and
not old8573; next scheduled100-boundary save is700. Existing model600 remains
the validated recovery checkpoint. Startup does not prove learned crossing.
Current stage1, no new verified strict success. Early iterations before first
obstacle have zone0/delta0/clearanceNaN; course window fields include restored
historical window state until new complete episodes, not instant new success.

TensorBoard PID14933 replaced only verified old12864; local16006 data/logdir
matches the new run and scalar endpoint reports stage1 at601/602. Heartbeat
m1-ppo updated ACTIVE/10min with current process, scope and unresolved learning
checks; no unchanged-state notifications. No concurrent native probe remains.

Last verified running iteration615/10000 (PID14800 Rsl), stage1/zone1.0,
no new2cm prelift event yet. Actual learning remains unverified.

Implementation and evidence committed locally as0286e95 on the dedicated
upload mirror. Publishing to ssdsj12/m1-rl:m1-10-10 failed twice because local
GitHub443 connection timed out (first also LFS lock verification endpoint).
Last successfully queried remote ref before attempt was5af7a29; do not claim
0286e95 is already online. A per-command locksverify=false retry did not
change persistent Git/network configuration and also timed out. Server code,
tests and resumed training are deployed independently and unaffected. Retry a
normal non-force push when GitHub connectivity returns; exclude untracked
old one-shot pause/restart scripts and do not upload PT files.

Key files: m1_dynamic_crossing.py, m1_required_crossing.py,
ame_env_wrapper.py, focused regression tests, contact replay/verifier scripts.
Learning acceptance remains OPEN: real early single-wheel lift, every sampled
wheel-bottom top clearance>=3cm, stable landing and video plus strict metrics
for10cm obstacles. No test count or runtime startup proves this capability.
