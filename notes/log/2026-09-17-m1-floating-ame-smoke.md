# M1 floating AME smoke

## Purpose / Procedure / Inputs

Fresh AME training with NUM_ENVS=8, MAX_ITERATIONS=2, DEVICE=cuda:4, SAVE_INTERVAL=1 through scripts/run_m1_validation.sh and the amp launcher.

## Result

[Runtime log](../../run_logs/m1ame_floating_8x2.log): policy=(8,1581), critic=(8,1584), action=16; iterations 0 and 1; 640 total timesteps; Training Complete and VALIDATION_EXIT_CODE=0. Initial policy reward -6.35 is not a behavior success claim. Final saved file is model_1.pt, not model_2.pt, because checkpoint labels are zero-based.

## Conclusion / Follow-up

PPO update and shutdown contract pass. Proceed to a fresh 1024-env single-process stability gate and fixed-seed behavior evaluation.

## Stage / Related Todo

M1 AME physical environment, reward and training validation; [T306](../todo/T306-m1-ame-long-train-stability.md).

## Git Refs

Baseline Ref: `4b5251f`. Candidate Ref: `4b5251f` plus uncommitted M1 adaptations. These results are not evidence for a clean committed tree.

