# M1 wheel reward fresh8env×2 training smoke

## Purpose / Stage / Related Todo

Verify PPO consumes the new M1 reward configuration, saves valid checkpoints and ends normally. AME integration,[T306.6g](../todo/T306-m1-ame-long-train-stability.md).

## Inputs / Command

amp/physicalGPU4,fresh8env,seed42,2 updates,save_interval1,no checkpoint and no restart. Began only after[physical probe](2026-09-18-m1-wheel-reward-physical-probe.md) completed and process was gone.

```bash
env -u CHECKPOINT NUM_ENVS=8 MAX_ITERATIONS=2 DEVICE=cuda:4 SAVE_INTERVAL=1 VALIDATION_LOG=run_logs/m1_wheel_reward_smoke_8x2.log bash Go2Pvcnn/scripts/run_m1_validation.sh
```

## Result / Artifact audit

[Runtime log](../../run_logs/m1_wheel_reward_smoke_8x2.log),single PID2051916. Exact iterations0,1;Training Complete+VALIDATION_EXIT_CODE=0. Policy8×1581,critic8×1584,action16. Process exits;GPU4 returns5MiB/0% before next launch.

Run[2026-09-18_10-49-48/740f07e](../../logs/rsl_rl/m1_cross_large_complex_ame/2026-09-18_10-49-48/740f07e),model_1.pt hasiter1,next_iter2. Recursive audit finds138 checkpoint tensors,all finite;TensorBoard35 scalar tags,all values finite. Saved env_cfg binds progress/climb to new functions atweights1/.5 and old airtime/variance are null. TB contains both`Episode_Reward/small_obstacle_progress`and`Episode_Reward/small_obstacle_climb`.

## Conclusion / Follow-up / Git Refs

Integration smoke passes,not a learning-performance or10000-completion claim. Fresh1024×120 is next before fixed behavior evaluation. Baseline4b5251f+prior work,candidate740f07e+uncommitted reward changes.
