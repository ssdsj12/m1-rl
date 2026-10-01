# M1 wheel-reward pilot final small-obstacle evaluation

## Purpose / Stage / Related Todo

Test learned0.10m crossing after the approved reward pilot. Fixed first-episode policy evaluation,[T306.6g](../todo/T306-m1-ame-long-train-stability.md).

## Inputs / Procedure

amp/physicalGPU4,8env×500steps,seed42,8mspacing,command0.5m/s,no pushes. Box centerx1.5m,height0.10m,length0.20m,width1.2m. Checkpoint[model_119.pt](../../logs/rsl_rl/m1_cross_large_complex_ame/2026-09-18_10-52-23/740f07e/model_119.pt). Existing hardened evaluator unchanged; no training or concurrentIsaac.

`EVAL_SCENARIO=small NUM_ENVS=8 MAX_ITERATIONS=500 DEVICE=cuda:4 TRAIN_ENTRYPOINT=Go2Pvcnn/scripts/evaluate_m1_ame.py CHECKPOINT=<above checkpoint> VALIDATION_LOG=run_logs/m1_eval_wheelreward_small120.log bash Go2Pvcnn/scripts/run_m1_validation.sh`

## Metrics / Result

[Runtime](../../run_logs/m1_eval_wheelreward_small120.log) hasM1_EVALUATION_COMPLETE andVALIDATION_EXIT_CODE=0; process exited beforelarge launch. Small crossing0/8;goal/safe success0;body collision episode/step0;invalid/failure terminations0. Mean maximum forward1.07456160m,lateral0.07643959m. Prior semantic1-wheel baselineforward1.03423047m withcrossing0/8. This small forward difference is not crossing improvement; the robot stops before the box.

## Conclusion / Follow-up / Git Refs

Runtime gate passes; learned small-obstacle gate fails. Collect semantic1 opportunity and conditional progress/climb exposure on this same policy before changing weights. Baseline4b5251f+priorwork,candidate740f07e+uncommitted wheelreward implementation. Formal10000not launched.
