# Fresh floating M1 1024-env single-process stability gate

## Purpose / Procedure / Inputs

Launch one fresh AME process in amp on physical GPU4, NUM_ENVS=1024, MAX_ITERATIONS=120, SAVE_INTERVAL=20, seed 42. Use scripts/run_m1_validation.sh; no resume, no supervision restart loop. tmux m1ame_floating_1024x120, initial PID 2468034 (always recheck process command line).

## Evidence / Current Result

[Runtime log](../../run_logs/m1ame_floating_1024x120.log). Completed all 120 updates, exact iteration sequence 0..119, one `Training Complete` marker and `VALIDATION_EXIT_CODE=0`; no restart. PID 2468034 was observed throughout intermediate checks and is now gone. Total training time 968.84s and 4,915,200 timesteps. GPU4 held about 13.5GB; other GPUs had approximately 396MB idle runtime contexts, not distributed PPO compute. All devices returned to approximately 4MiB after exit.

Read-only final audit: `model_119.pt` has `iter=119`, `next_iter=120`; all 138 tensors in model/optimizer/checkpoint are finite. All 35 TensorBoard scalar tags are finite. Final value loss 0.0237174, surrogate loss -0.00305221, std 0.575611, mean reward -0.809488, mean episode length 9.67 steps, bad-orientation terminations 0.985547. The shrinking episode length makes this a behavior failure despite finite improving-looking losses/rewards.

## Acceptance / Follow-up

The 120-update process-stability gate passes; it does not prove 10000-update stability. Evaluate the actual last checkpoint on flat/small/large. Do not start or declare the official 10000-update acceptance before checking the plan's behavior gate. Checkpoint model_119.pt represents 120 completed updates. The saved config used std=1.0; a separately validated std=0.2 candidate must be tested fresh, not resumed from this collapsed checkpoint.

## Stage / Related Todo

M1 AME physical environment, reward and training validation; [T306](../todo/T306-m1-ame-long-train-stability.md).

## Git Refs

Baseline Ref: `4b5251f`. Candidate Ref: `4b5251f` plus uncommitted M1 adaptations. These results are not evidence for a clean committed tree.
