# M1 replacement-host checkpoint resume

## Purpose / scope

User supplied replacement host `a21472797434572800304964` and explicitly said
to continue training. Parent: [T306](../todo/T306-m1-ame-long-train-stability.md),
child `pure-ppo-learning/host-resume`. Previous deployment:
[density resume](2026-10-11-m1-density-resume.md).
This is an operational restart, not a terrain/reward/controller change.

## Evidence / boundary

At 2026-10-11 02:48 UTC the replacement host contained the original worktree,
runs and logs, but no live train/TensorBoard/probe; GPU0 used 1MiB.
Old log ended at1024, but the 10-28-16 run contained no saved PT.
Actual latest saved boundary remains 09-57-29/bb57e7d/model_1000.pt.
Resume therefore repeats1001--1024; it does not resume from an unsaved1024.

CPU checkpoint validation on this host: iter1000/next1001,39finite weights,
33finite optimizer states,16positive finite std, stage1/streak0 retained.
Checkpoint SHA256:26df6b4a1382d56c44fb7e365a5f9d8d3f630987445072928a4e22bd623f2c3c.
Geometry SHA256:7cdfff00c1700759f40c6e68ce6fb9e5120e6279c9bf5afc39f71e82baa1da3c.
Both match the previously verified deployment. The same12-file CPU regression
selection documented in the density deployment passed173 tests in3.85s.
No additional native probe was launched and no production source was edited.

## Launch / verification

2026-10-11 02:56 UTC: one-shot guarded launch produced PID948, cwd
`/root/quad/m1-rl/.worktrees/contact-recovery`. Command freshly verified:
2048env,cuda:0,flat-first,resume exactmodel1000,--keep_std,max_iterations8999.
M1_LOAD_OPTIMIZER=1, kernel flock and save100 remain enabled.
New run:`2026-10-11_10-56-34/bb57e7d`.
Log:`/tmp/m1-ppo-host-resume-20261011.log`.
Runtime confirms policy[2048,1589],critic[2048,1592],controllerppo,
mpc_teacherdisabled,imitation0 and checkpoint loaded.
TensorBoard PID1081 points to the new10-56-34 run on remote127.0.0.1:6006.
Local16006 tunnel was not modified and must not be claimed working without a check.
The old host/PIDs17722/17849 are historical and must not be reused.

## Follow-up / refs

At2026-10-11 02:57:59UTC actual iteration1001 completed; value loss.1343,
surrogate.0331 finite, GPU0 memory21862MiB. /proc948 confirmed
M1_LOAD_OPTIMIZER1,MAX_ITERATIONS8999,SAVE_INTERVAL100,NUM_ENVS2048.
Remote6006/data/logdir independently matched the new run; PID1081 verified.
Initial stage1/PT.last metrics are retained history, not new-layout success;
prelift/stable0 and no-attempt NaN are not success. First iteration50.27s
includes startup; observe steady throughput before diagnosing performance.
No learning or strict crossing success is implied by restart or CPU tests.
Keep2048,585mm,optimizer/std/course and strict prelift/clearance/recovery
contracts. No parallel GPU diagnostics. Continue monitoring real learning;
full-stage3 dynamic recovery remains OPEN.
Baseline/Candidate Work Ref:260b3a1cf4f2609dd983137bd1abbcd269ad1416.
Last Feature/Verified Feature:5a366ff; no feature code changed this turn.
Key files: existingrun_m1_pure_ppo.sh,model1000 and operational logs above.
