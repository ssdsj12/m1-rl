# M1 lift-roll: user-directed PPO self-learning

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md).
Previous evidence: [diagnostic repair](2026-10-11-m1-placement-diagnostic-repair.md),
[model300 selection](2026-10-11-m1-model300-restart-selection.md).

## User decision and scope

User explicitly said “长训先” and “让它自己来折腿，学习跨障碍物”.
This supersedes making a static folded-leg fixture pass before training.
Invalid empty-ground fold controls remain inconclusive_fixture, not accepted
and not physical impossibility. PPO discovers joint actions/coordination;
no swing trajectory, teacher, MPC, imitation, IK, WBC, extra servo, action
takeover or manual std change. Strict prelift/3cm overlap/stable recovery stay.

## Change and verification

Existing equal8+70fill geometry/roles are deployed: same XY/footprints/counts
across stages1–3, only heights3/6/10cm change; stage0/mixed4 unchanged.
Training flat-first selector changes from m1_progressive to m1_lift_roll.
Selector RED:1failed/9passed (old selector); GREEN:233tests across the same
17files as diagnostic repair passed in4.15s. Earlier native96 recovery
placements/live map/role/reset evidence remain, not dynamic learning proof.

Four runtime file SHA256 values checked before/after deployment:

- m1_mixed_course.py:0af49f5c8dd0edaa809847241ad9a7f0928e9cc31484b469c627e6184e8f5395
- m1_course_registry.py:39cf064044485f1a7f51a082b5eca6ce43b1ac4dd1b3a45b322736cbd875840d
- m1_lift_roll_layout.py:8ba0f8fcb9f0c164e7e7c16df36dbec7781e6a2e12153686cde38deae012784f
- semantic_course.py:88bf446b70fa0390c5df5f8d803c08b6eb875596a0245d631863132a1d685e58

Guarded deployment checked old hashes, no train/native process and GPU0=1MiB.
Backup `/tmp/m1-before-lift-roll-train300.tar` SHA256
dc645866dbde113747630bef9d1fa79e06b5fea338c8ae8be5dafd5a8eaa3d61.
Old4/6/8 rollback needs old mixed_course, not only selector.

## Launch evidence

Host a21472797434572800304964; production contact-recovery worktree.
User-selected18-49-19/bb57e7d/model300 freshly CPU checked:39finite weights,
33finite optimizer states,16positive std,stage1,next301,architecture1589/1592.
SHA4437ed429f6c2339284efb567b1dda5aabab83f59823bc376f80d23ebccdc075.
model1400 backup retained.301+9699 updates to exclusive10000;
2048env/GPU0/save100/M1_LOAD_OPTIMIZER1/keep_std/course retained.

One-shot launch PID4921, log `/tmp/m1-ppo-lift-roll-model300-20261011.log`.
05:17:46UTC /proc cmdline/cwd confirmed exact settings; scene2048 initialized,
simulation starting. Existing kernel flock remains. Startup is not a completed
PPO update. No concurrent native diagnostics or old watchers permitted.

## Open evidence / publication

05:19:42UTC runtime:policy(2048,1589),critic(2048,1592),controllerppo,
teacherdisabled/imitation0, exactmodel300 resumed. Savedenv_cfg confirms
placement_strategy:m1_lift_roll,train_cfg save_interval100; /proc confirms
M1_LOAD_OPTIMIZER1/MAX_ITERATIONS9699/NUM_ENVS2048. GPU21854MiB/98% utilization;
first update not yet printed. TensorBoard5109 switched to13-17-21 run,
remote6006/data/logdir independently matches. Local16006 actively refused;
no network/tunnel changes made, do not claim old browser chart is live.
Independent read-only review found noCritical/Important selector/launch issues.

Full2048 update capacity/finite losses and selected layout require this run's
runtime evidence. Learning requires video plus strict events, not start,
forward pass, empty NaN or rounded-zero metrics. Static negative evidence stays.
Base Work Ref5e60159; prior diagnostic implementation6c82648. GitHub target
m1-10-11; last verified remote900f249, previouspush443failed.
