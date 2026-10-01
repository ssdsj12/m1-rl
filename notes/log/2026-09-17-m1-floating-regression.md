# M1 floating/reward regression

## Purpose / Procedure

Plain pytest in amp, with PYTHONPATH and CUDA_VISIBLE_DEVICES unset. Suite: tests/ame_baseline, test_actor_critic_ame, test_ame_observations, test_ame_vec_env_and_cfg, test_m1_ame_action_contract, test_m1_ame_config_static, test_m1_ame_terminations, test_m1_rl_reward_geometry, test_m1_parallelism_rl_adapter, tracking/test_policy_geometry_rewards, test_usd_mesh_triangulation.

## Result

82 passed, 1 skipped in 10.40s. The skipped test requires a live Isaac Sim application; real AME/AMP smokes cover that configuration separately. New evaluation metrics red: missing m1_evaluation_metrics module. Green: test_m1_evaluation_metrics.py, 4 passed in 1.29s. Tests cover terminal collision retention, ignoring later auto-reset episodes, rejecting small-obstacle bypass and requiring a side route for large obstacles.

## Conclusion / Follow-up

Fresh combined verification after adding evaluation bookkeeping: 86 passed, 1 skipped in 10.25s. Adding test_m1_exploration_cfg.py gives 88 passed, 1 skipped in 10.78s. The exploration-config candidate has its own [red/green record](2026-09-17-m1-exploration-budget.md).

Tensor contracts, rewards, terrain scan ordering, convex-face triangulation and evaluation bookkeeping pass their focused tests. Entire repository and final 10000-update training are not claimed verified.

## Stage / Related Todo

M1 AME physical environment, reward and training validation; [T306](../todo/T306-m1-ame-long-train-stability.md).

## Git Refs

Baseline Ref: `4b5251f`. Candidate Ref: `4b5251f` plus uncommitted M1 adaptations. These results are not evidence for a clean committed tree.
