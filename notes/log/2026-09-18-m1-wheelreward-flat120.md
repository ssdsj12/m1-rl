# M1 wheel-reward pilot final flat evaluation

## Purpose / Stage / Related Todo

Check learned flat locomotion before obstacle acceptance. Fixed first-episode policy evaluation,[T306.6g](../todo/T306-m1-ame-long-train-stability.md).

## Inputs / Procedure

amp/physicalGPU4,8env×500steps,seed42,8m spacing,fixed forward command0.5m/s,no pushes. Policy[model_119.pt](../../logs/rsl_rl/m1_cross_large_complex_ame/2026-09-18_10-52-23/740f07e/model_119.pt) from completedfresh1024×120. Existing evaluator unchanged; all body collisions,non-timeout failures and invalid terminations exclude safe success.

Use`EVAL_SCENARIO=flat NUM_ENVS=8 MAX_ITERATIONS=500 DEVICE=cuda:4 TRAIN_ENTRYPOINT=Go2Pvcnn/scripts/evaluate_m1_ame.py CHECKPOINT=<above checkpoint> VALIDATION_LOG=run_logs/m1_eval_wheelreward_flat120.log bash Go2Pvcnn/scripts/run_m1_validation.sh`.

## Metrics / Result

[Runtime](../../run_logs/m1_eval_wheelreward_flat120.log) emitsM1_EVALUATION_COMPLETE andVALIDATION_EXIT_CODE=0;process exits before small evaluation launch. Safe success8/8;body collision episode/step0;invalid-state termination0;failure termination0. Mean maximum forward4.89728355m,lateral0.12297851m. Previous semantic1-wheel policy's hardened flat evaluation was4.1757507m and8/8;these are fixed-seed sample results,not generalization guarantees.

## Conclusion / Follow-up / Git Refs

Flat gate passes. Subsequent[small](2026-09-18-m1-wheelreward-small120.md)and[large](2026-09-18-m1-wheelreward-large120.md)evaluations bothcomplete+exit0 butcrossing/avoidance0/8;do not infer obstacle success from flat results. Baseline4b5251f+prior M1work,candidate740f07e+uncommitted wheel reward changes.
