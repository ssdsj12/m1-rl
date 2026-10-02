# M1 large-obstacle baseline

## Purpose / Procedure / Inputs

Same checkpoint/seed and 8 x 500-step protocol as the [small baseline](2026-09-17-m1-small-baseline.md), with EVAL_SCENARIO=large and a 0.80m high x 0.60m long x 1.2m wide box. Successful avoidance requires forward completion, a clear side corridor during passage and no body collision.

## Result

[Evaluation log](../../run_logs/m1_eval_baseline_large.log): large_avoidance_rate=0, goal_reached_rate=0, body_collision_episode_rate=0, invalid_state_termination_rate=0, mean_max_forward_m=0.0272482; M1_EVALUATION_COMPLETE and VALIDATION_EXIT_CODE=0.

## Conclusion / Follow-up

No learned avoidance yet. Compare a trained pilot checkpoint using the same seed, box and measurement rules.

## Stage / Related Todo

M1 AME physical environment, reward and training validation; [T306](../todo/T306-m1-ame-long-train-stability.md).

## Git Refs

Baseline Ref: `4b5251f`. Candidate Ref: `4b5251f` plus uncommitted M1 adaptations. These results are not evidence for a clean committed tree.

