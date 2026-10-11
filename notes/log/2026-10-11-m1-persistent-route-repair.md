# M1 persistent route penalty repair / same-lineage resume

## Purpose / authorization / scope

User explicitly confirmed “确定，这不是昨天确定好了的吗” on 2026-10-11.
Do not repeat the approval request. Repair the scanner-dependent route-cost hole
and resume pure PPO after verification. Parent: [T306](../todo/T306-m1-ame-long-train-stability.md),
child `pure-ppo-learning/required-crossing/policy-contact-stall/corridor-visibility`.
[Model900 diagnosis](2026-10-10-m1-model900-contact-replay.md) is the input evidence.
This does not reopen the already-fixed positive post-slab reward gate.

## Contract / implementation

- Stage1--3 only: persist approached authored wheel-track obligations until
  identity-matched per-wheel strict recovery, reset/done, or course change.
- For each pending wheel/block pair, measure world-Y overhang of the actual
  wheel footprint: `abs(wheel_y-block_y)+projected_half_width-block_half_y`.
  `max(clamp(overhang/.30,0,1))` replaces existing corridor cost at unchanged -1
  weight. Multiple wheels/blocks do not stack. No new positive shaping term.
- Nominal half-width .02325m and block half-width .09m give .06675m free wheel
  center deviation. This is not a root-Y .22m tolerance. Rotation uses real
  quaternion projection, including wide-footprint overhang even at center.
- Pre-step stage/cost snapshot survives terminal reset and is consumed by
  RewardManager; stage0 and mixed4 retain legacy scanner-based avoidance.
- Strict receipts, persistent positive reward suppression, safe world-height
  prelift progress, collisions and strict success thresholds unchanged.
- No MPC, teacher, imitation, action injection, WBC, IK, servo or std edits.
  585mm initial geometry and training2048env preserved.4env is diagnosis only.

## Verification

### TDD and CPU

New seven behavioral tests first failed against old code (7failed/10passed):
missing persistent method and real reward function returning zero after scan loss.
After implementation:168passed in2.91s across persistent-route/persistent-reward,
dynamic-crossing/receipts/required-crossing/obstacle-rewards/learning-curriculum/
flat-first-terrain/recovery-runtime tests. One older AST fixture needed the new
route metric local; no expectation weakened.

Final repeat including five AME checkpoint/resume tests:173passed in4.26s.
`git diff --check` also clean. Repository collection limitations below remain.

Command from remote worktree:
`OMP_NUM_THREADS=1 PYTHONPATH=Go2Pvcnn:Go2Pvcnn/rsl_rl /opt/conda/envs/env_issacsim/bin/python -m pytest -q --tb=short <nine test files>`.

Full repository attempt still stops at the ten historical collection errors:
`test_m1_sdf_probe`, `test_m1_teacher_obstacle_hold`, seven `tests/evaluation`
modules, and `tools/m1_reference_validation/tests/test_clone_evidence.py`.
Missing runtime/import dependencies are not a passing full suite.
Full output: `/tmp/m1-route-full-pytest-20261011.log`.

### Recorded model900 physical-motion counterfactual (CPU)

`/tmp/m1-verify-route900.py /tmp/m1-contact-replay-900.jsonl` reconstructs the
unchanged saved final PPO reward before replacing only the corridor term.
Uses real previous-step wheel XYZ/quaternion, authored course, per-step reset;
first frame and terminal frames excluded from counts. No simulated learning.

| Mode | evaluated env-frames | formerly missed cost now charged | cost integral | max original reward reconstruction error |
| --- | ---: | ---: | ---: | ---: |
| mean |3992|2625|50.8176528537|3.3386e-8|
| sampled |3992|2685|53.7|1.2567e-8|

Both modes retain zero strict recovery. Asserted final reward delta exactly
equals this one negative term's delta.5310 closed loophole frames are NOT
crossing success or policy improvement evidence.

### Independent review

Read-only `review_persistent_route_fix` reviewed actual three-file production
diff, three test files and lifecycle/reward consumption context. Verdict Ready,
no Critical/Important/Minor findings. Did not independently rerun CPU or native.
Native consumption ordering/GPU behavior and learning capability explicitly
remain separate verification responsibilities.

### Native geometry / reward wiring

4env `probe_m1_flat_first.py` exited0 with `M1_FLAT_FIRST_RESULT`.
Verified actual block heights3/6/10cm, counts2/4/8, pooled world top equals
native scanner top, policy shape[4,1589], neutral recovery4/4 for final20steps.
Stage1 post-slab off-lane route cost[1,1,1,1], no receipts/bonus, final rewards
[-.026542,-.028079,-.027023,-.026192]. RewardManager's existing corridor term
matches negative pre-step cost. Stage0/mixed4 snapshot disabled and legacy term
unchanged. Diagnostic placements are not learned locomotion/crossing.

### Fixed-policy native replay / terminal reward accounting

Mean and sampled each4env1000steps completed with2003JSONL and explicit
`M1_CONTACT_REPLAY_COMPLETE`. SSH transport reset at completion, so client
exit status was not used as proof. Independent reconnect verified full output,
both probe processes absent and GPU0 back to1MiB, then CPU audit passed.
`/tmp/m1-audit-route-native.py` verifies snapshot versus actual negative reward
term and reconstructs final PPO reward on all8000env-frames, including eight
terminal reset frames. Summary:`/tmp/m1-route-native-audit-20261011.json`.

| Mode | env-frames | charged frames | terminal frames | attempts |2cm events|strict recovery|max final reward reconstruction error|
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
|mean|4000|2855|4|7|0|0|3.3386e-8|
|sampled|4000|2689|4|0|0|0|1.3615e-8|

Mean980post-slab frames all nonpositive. The old fixed policy still does not
cross correctly; this is native reward wiring evidence, not successful learning.

### Deployment / startup

Original train14800 and probe15658 absent; GPU0 1MiB before this pass.
Backed up three original production files in `/tmp/m1-route-backup.HYAEAU`.
Candidate deployed to the existing remote worktree, no process hot reload claim.
4env geometry/reset/reward evidence:`/tmp/m1-route-native-20261011.log`.
Model900 mean/sample replay output:`/tmp/m1-route-replay-900-20261011.jsonl` and`.log`.
Same-lineage checkpoint freshly revalidated before resume:
`logs/rsl_rl/m1_cross_large_complex_ame/2026-10-10_22-09-27/bb57e7d/model_900.pt`.
Required resume: next901 +9099 updates to total10000,2048env,GPU0,save100;
optimizer/std/course retained, no older checkpoint or watcher restart.
Fresh CPU PT verification at2026-10-11T01:54:22Z confirms iter900/next901,
39finite weights,33optimizer states,16positive finite std,actor1589/critic1592,
stage1 with last complete2048/pass.7333984375/64attempts/0success. Production
SHA256 verified before launch; no model mutation.

At2026-10-11T01:57:24Z the one-shot guarded launcher verified no train/native
process and GPU0<100MiB, then invoked existing kernel-flock training wrapper.
New PID16830,log`/tmp/m1-ppo-persistent-route-20261011.log`,2048envGPU0,
next901+9099,total10000/save100,M1_LOAD_OPTIMIZER=1,--keep_std,flat-first.
Subsequently verified `/proc/16830/cmdline` and cwd match the exact2048 resume;
live envM1_LOAD_OPTIMIZER=1,NUM_ENVS2048,MAX_ITERATIONS9099,COURSE_PROFILEflat-first,
SAVE_INTERVAL100,DEVICEcuda:0. Runtime confirms controller=ppo,mpc_teacher=disabled,
imitation_coef=0,policy[2048,1589],critic[2048,1592],loaded correctmodel900.
Completed901--905/10000 observed; GPU0 21862MiB/24564MiB.
Run:`logs/rsl_rl/m1_cross_large_complex_ame/2026-10-11_09-57-29/bb57e7d`.
Early901--905no2cm/stablelanding; no learning claim, no immediate stop from
these first pre-obstacle rollouts. Do not interpret four-decimal delta as raw0.
The launcher is not a watcher and refuses to overwrite its existing log.

TensorBoard14933 cmdline/logdir verified before SIGTERM; replaced only this
task-owned process with16981 pointing09-57-29run,port6006host127.0.0.1.
Both remote6006 and existing local127.0.0.1:16006 `/data/logdir` verify newrun.
No display/tunnel/network/globalGit settings changed.

## Open follow-up / boundaries

- Learning single-wheel prelift / three-wheel support and strict10cm crossing
  remains OPEN. No reward signal or body-root height is proof of wheel lift.
- Stage3 terminal-space deficit .488708m in nominal+X posture is still OPEN.
  Whole-row -.6m is an unimplemented candidate, not a boundary relaxation.
- Curriculum pending/last metric means are not full windows; inspect PT.last
  when needed. Speed error remains informational, not promotion threshold.
- Native probes must exit and GPU release before2048 training; no concurrent
  probe during~22GB training. Preserve unrelated display/GPU7/processes.

## Git refs / key files

Baseline Ref / previous publication: `3cc82b349515223efc4e200a15a3aaba764b042b`.
Candidate / Last Feature / Last Verified implementation Ref:`a8923f2`.
Remote worktree baseline`bb57e7d` plus historical and this deployed diff;
no hot modification after training startup. Current Work Ref:
`codex/m1-ppo-repair-upload` local,`codex/m1-contact-recovery` server.
Normal non-force GitHub push ofa8923f2 to`m1-10-10` failed443 connect timeout
after21s; initial publication not confirmed. This does not affect server runtime.
Key files:`m1_required_crossing.py`, `ame_env_wrapper.py`, `m1_obstacle_rewards.py`,
route/reward/runtime tests, native flat-first and contact probes.
