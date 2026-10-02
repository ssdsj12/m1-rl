# M1 wheel reward fresh1024×120 learning pilot

## Purpose / Stage / Related Todo

Measure whether approved wheel-appropriate reward shaping improves M1 behavior after physical and8env integration gates. M1 AME learning,[T306.6g](../todo/T306-m1-ame-long-train-stability.md).

## Inputs / Procedure

amp/physicalGPU4,1024env,120updates,seed42,initial policy std0.2,save_interval20,fresh/no checkpoint. Existing terrain/reset/command curriculum and all safety terms are unchanged. Start only after previous Isaac process exits. Single tmux`m1wheel_1024x120`,one Python PID2060785,not a restart loop.

```bash
env -u CHECKPOINT NUM_ENVS=1024 MAX_ITERATIONS=120 DEVICE=cuda:4 SAVE_INTERVAL=20 VALIDATION_LOG=run_logs/m1_wheel_reward_1024x120.log bash Go2Pvcnn/scripts/run_m1_validation.sh
```

## Live Evidence (not completion)

[Runtime log](../../run_logs/m1_wheel_reward_1024x120.log),[run directory](../../logs/rsl_rl/m1_cross_large_complex_ame/2026-09-18_10-52-23/740f07e).

Atiteration30: same Python PID,noise std0.25,mean reward1.67,mean episode989.14,bad_orientation0.0068. GPU4 observed72%/13528MiB; iteration25-27 throughput5623..5644envsteps/s,collection5.45..5.48s,learning1.78..1.82s. Prior sem1-wheel pilot tail was5294..5321steps/s; this is an observational comparison,not a controlled benchmark.

AtTBstep33: all scalar values finite;new progress nonzero31/34,max0.00348227,min-0.00549829;new climb nonzero28/34,max0.0000314953. Console printing0.0000 does not mean exactly zero. Checkpointsmodel_0.pt/model_20.pt present.

Saved config starts XY commands each[-0.1,0.1],yaw[-1,1],10%standing;limit XY ranges are[-1,1]/[-.5,.5]. This is the serialized initial config,not proof of unchanged live command ranges; the velocity curriculum must be inspected before attributing weak reward exposure to low-speed commands. Do not alter this in-flight A/B run.

Read-only follow-up confirmed the inherited`lin_vel_cmd_levels`is still enabled: every20envsteps,an eligible episode's normalized velocity-tracking reward>1.2 can expand x/y bounds by0.1 toward limits. ActualTBstep63 reports`Curriculum/lin_vel_cmd_levels=1.0`(initialstep0=0.1),so live x upper range has reached its limit. The pilot is not stuck at initial±0.1 commands. Atstep63 progress=-0.00155395(maxsofar0.01139782),climb=0.0000237591(max0.0000435925); the console rounded zeros are still not exact zeros. Per-opportunity exposure/amplitude may need diagnosis after behavior evaluation,not an in-flight weight sweep.

The samePID2060785 continues throughiteration63 without restart. Automatic heartbeat`m1-gpu4`has been reactivated every10minutes with exact current run and sequential post-completion audit/evaluation instructions. Normal progress remains quiet; meaningful completion/failure/behavior results notify the user.

## Completion Audit

Heartbeat follow-up confirms the process completed: exactiterations0..119 in order,exactly oneTRAIN_PROCESS_START,Training Complete andVALIDATION_EXIT_CODE=0. Finalmodel_119.pt hasiter119/next_iter120. All138 recursively collected checkpoint tensors and all values in35TB scalar tags are finite. Saved cfg has oldairtime/variance=null,progress1.0/climb0.5 with the new function bindings. No M1 training process remains; the sequential fixed-scene evaluation is the next stage.

Lastiteration119 metrics: episode975.36,meanreward-50.74444,noise_std0.37867045,bad_orientation0.01225586,geometry reward-2.30703545,progress0.00070766,climb0.00010317,livevelocity curriculum1.0. These finite values are not evidence of obstacle success; compare full behavior evaluation,not the reward alone.

## Acceptance / Next Step

The120-update process/artifact gate passes. Sequential finalmodel119 evaluations are now complete+exit0:[flat](2026-09-18-m1-wheelreward-flat120.md)8/8safe success,[small](2026-09-18-m1-wheelreward-small120.md)0/8crossing,[large](2026-09-18-m1-wheelreward-large120.md)0/8avoidance. All collision/invalid/failure rates are0; forward4.89728/1.07456/0.50969m. The policy still stops before obstacles. [Tail comparison](2026-09-18-m1-wheelreward-tail-audit.md) confirms nonzero new signals but increasednoise/bad-orientation risk. Next is bounded gate/exposure diagnosis,not blindlongertraining. No simultaneousIsaac,no resume/restart supervisor,and noformal10000until behavior improves. This120-update pilot is not10000completion.

Baseline4b5251f+prior work,candidate740f07e+uncommitted reward implementation. [Implementation and test evidence](2026-09-18-m1-wheel-reward-implementation.md),[physical probe](2026-09-18-m1-wheel-reward-physical-probe.md),[8envsmoke](2026-09-18-m1-wheel-reward-smoke.md).
