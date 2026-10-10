# T306 / required-crossing reward and lane layout

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline bb57e7d; candidate codex/m1-contact-recovery plus preserved dirty edits.
User requests FRESH purePPO2048/10000/save100. Old8573 stopped, oldmodel1000
archived only: do not resume old weights/optimizer/curriculum.

## Changes and contracts

Stage1/2/3 two3cm/four6cm/eight10cm blocks now10x18cm cuboids, alternating
y=+/-.215, pitch1.8/1.8/.9m unchanged. Stage0empty and mixedrows4+ unchanged.
Progressive worldX obstacle slabs strip ALL positive reward rates, retain costs;
.3 single measured earlylift>=2cm once per encounter,2 stable far-side recovery.
Collision/done never gives event bonus. Lateral bypass cannot disable slab;
late valid recovery outside slab still earns completion reward.
Three other wheels must support during selected air phase. Every sampled
overlap needs>=3cm actual mesh-bottom clearance; one good frame cannot hide dip.
Telemetry: removed positive reward, bonus, summed events/collisions/samples,
true rollout minimum clearance, NaN when no samples (not success).
No MPC/teacher/forced actions/IK/WBC/servo changes;2048 and585mm initial geometry
retained; speed-error promotion gate remains removed.

## Verification / review

7RED->31GREEN, review fixes RED/GREEN, final affected suite134passed.
Installed Isaac RewardManager confirms _step_reward=value/dt.
Native4env passed geometry/reset/reward checks:3/6/10cm actual bounds,2/4/8
objects;24near-obstacle steps finite, positive rewards removed, no false bonus.
Final rerun /tmp/m1-required-native-final.log passed and exited0.
This verifies runtime wiring, NOT learned skill/video acceptance.
Full pytest attempted twice; final10collection errors: test_m1_sdf_probe,
test_m1_teacher_obstacle_hold, seven tests/evaluation modules, and
tools/m1_reference_validation/tests/test_clone_evidence. Missing pxr/evaluation
and legacy imports; /tmp/m1-required-full-suite-final.log. Not full-suite green.
Independent review found minimum averaged/stale logs; fixed snapshots, explicit
NaN, min/sum aggregation. Late recovery regraded important, regression fixed.
Paired-lift counterexample exposed permissive strict events; regression fixed.
Deferred minor: additional explicit failure/reset prelift-pulse fixtures.

## Rulings / risk

Only progressive early stages use cuboids; mixed shape diversity unchanged.
Strip all positive shaping in slabs to meet user's no-sliding-reward requirement;
cost is sparse exploration/stalling risk. Monitor stage1 prelift and recovery,
do not claim convergence. Existing dirty worktree retained, no merge/push.
Bounded native wiring probe substitutes for old-policy video because user now
requires FRESH training; actual policy/video acceptance remains OPEN.

## Deployment

Fresh PID10311 verified:2048envs/10000iterations/GPU0/flat-first, no resume or
checkpoint arguments. Run2026-10-10_18-49-19/bb57e7d;
log/tmp/m1-ppo-required-crossing-fresh-20261010.log. Iteration0/10000 observed;
model_0.pt exists5.7MB. Actual2048x1589/1592observations,16actions, controllerPPO,
teacherdisabled/imitation0, stage0obstacles0 assertion passed. TensorBoard10555
points this run; local16006API works. Monitor m1-ppo ACTIVE with fresh identity.
