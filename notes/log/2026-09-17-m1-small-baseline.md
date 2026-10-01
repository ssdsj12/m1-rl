# M1 small-obstacle baseline

## Purpose / Procedure / Inputs

Fixed seed 42, 8 environments, 500 steps, amp/GPU4, EVAL_SCENARIO=small; 0.10m high x 0.20m long x 1.2m wide box at x=1.5m. Checkpoint is the two-update AME model_1.pt from run 2026-09-17_13-19-47/4b5251f. External push and curricula disabled for comparison.

## Result

[Evaluation log](../../run_logs/m1_eval_baseline_small_v2.log): small_crossing_rate=0, goal_reached_rate=0, body_collision_episode_rate=0, invalid_state_termination_rate=0, mean_max_forward_m=0.0272482; M1_EVALUATION_COMPLETE and VALIDATION_EXIT_CODE=0.

## Conclusion / Follow-up

Evaluation executes but the baseline has not learned crossing. Collision is read from pre-reset reward buffers. Passing a finish x coordinate outside the box corridor is not counted as crossing. The initial invocation pointed to nonexistent model_2.pt, was interrupted before evaluation and excluded from results; model_1.pt is the verified existing final checkpoint.

## Stage / Related Todo

M1 AME physical environment, reward and training validation; [T306](../todo/T306-m1-ame-long-train-stability.md).

## Git Refs

Baseline Ref: `4b5251f`. Candidate Ref: `4b5251f` plus uncommitted M1 adaptations. These results are not evidence for a clean committed tree.

