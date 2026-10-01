# M1 wheel-reward pilot final large-obstacle evaluation

## Purpose / Stage / Related Todo

Test learned avoidance of non-crossable0.80m obstacles. Fixed first-episode policy evaluation,[T306.6g](../todo/T306-m1-ame-long-train-stability.md).

## Inputs / Procedure

amp/physicalGPU4,8env×500steps,seed42,8mspacing,command0.5m/s,no pushes. Box centerx1.5m,height0.80m,length0.60m,width1.2m. Checkpoint[model_119.pt](../../logs/rsl_rl/m1_cross_large_complex_ame/2026-09-18_10-52-23/740f07e/model_119.pt). Existing evaluator unchanged; launched only aftersmall exit. Safe bypass requires lateral clearance through the whole passage and no collision/failure.

`EVAL_SCENARIO=large NUM_ENVS=8 MAX_ITERATIONS=500 DEVICE=cuda:4 TRAIN_ENTRYPOINT=Go2Pvcnn/scripts/evaluate_m1_ame.py CHECKPOINT=<above checkpoint> VALIDATION_LOG=run_logs/m1_eval_wheelreward_large120.log bash Go2Pvcnn/scripts/run_m1_validation.sh`

## Metrics / Result

[Runtime](../../run_logs/m1_eval_wheelreward_large120.log) hasM1_EVALUATION_COMPLETE andVALIDATION_EXIT_CODE=0;process is gone. Avoidance0/8;goal/safe success0;body collision episode/step0;invalid/failure terminations0. Mean maximum forward0.50968838m,lateral0.01260114m. Prior semantic1-wheel baselineforward0.50739849m andavoidance0/8. The policy still stops rather than bypassing; zero collision is not successful avoidance.

## Conclusion / Follow-up / Git Refs

Runtime gate passes; large-obstacle behavior gate fails. The new shaping is deliberately vetoed aroundsemantic2 and is not a new large-obstacle navigation objective. Do not infer a cause from this alone or weaken safety penalties. Finish exposure diagnosis before proposing further learning changes. Baseline4b5251f+priorwork,candidate740f07e+uncommitted wheelreward implementation.
