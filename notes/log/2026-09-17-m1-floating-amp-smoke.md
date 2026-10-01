# M1 floating AME-AMP smoke

## Purpose / Procedure / Inputs

Warm-start the new-contract AME-AMP entrypoint from the new AME model_1.pt (run 2026-09-17_13-19-47/4b5251f). NUM_ENVS=8, MAX_ITERATIONS=2, DEVICE=cuda:4, SAVE_INTERVAL=1, amp Python; no old 1585-wide checkpoint.

## Result

[Runtime log](../../run_logs/m1amp_floating_8x2.log): 640 total timesteps, two updates, Training Complete - m1_cross_large_complex_ame_amp, VALIDATION_EXIT_CODE=0.

## Conclusion / Follow-up

New observation/action contract and AME warm-start execute through AMP/PPO updates. This does not establish reference quality or obstacle competence; those remain T306.6.

## Stage / Related Todo

M1 AME physical environment, reward and training validation; [T306](../todo/T306-m1-ame-long-train-stability.md).

## Git Refs

Baseline Ref: `4b5251f`. Candidate Ref: `4b5251f` plus uncommitted M1 adaptations. These results are not evidence for a clean committed tree.

