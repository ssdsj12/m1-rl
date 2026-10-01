# M1 evaluation rejects success followed by failure

## Purpose / Stage / Related Todo

Prevent a false-positive behavior acceptance when a robot reaches the goal then falls; evaluation bookkeeping, [T306.6d](../todo/T306-m1-ame-long-train-stability.md).

## Evidence / Procedure

Read-only review found `success` remained latched after bad_orientation termination when collision and nonfinite were false. Reproduced with a CPU tensor trajectory: old `collision_free_success_rate` stayed1 instead of0. RED:2 failed,4 passed (`test_m1_evaluation_metrics.py`); the second new test exposes missing separation of timeout versus failure termination.

Minimal fix: latch first-episode `terminated & done & alive`, exclude it from safe success, and report failure_termination_rate. Keep goal_reached_rate as the diagnostic 'ever reached' field. The evaluator passes IsaacLab's current `termination_manager.terminated` directly; it is not derived using `done & ~timeouts` because a failure and timeout can co-occur. Installed IsaacLab step/reset source confirms this buffer survives auto-reset. No policy/observation/reward contract changed.

GREEN: evaluation + M1 reward tests13 passed. Broader regression91 passed,1 skipped in10.43s: tests/ame_baseline,actor_critic_ame,ame_observations,ame_vec_env_and_cfg,M1 action/config/termination/reward/adapter/evaluation/exploration,tracking policy geometry,and USD mesh triangulation. The skipped case requires a live Isaac application. Existing reset-isolation and small-bypass/large-route tests remain passing. Real evaluator reruns are recorded below when complete.

## Git Refs / Key Files / Follow-up

Real8env x500-step hardened reruns all completed with exit0 and failure_termination_rate0. Flat safe1.0/4.175751m, small crossing0/1.034230m, large avoidance0/0.507398m. Outcomes match the prior runs, now with verified failure-mask wiring: [flat v2](../../run_logs/m1_eval_sem1wheel_flat120_v2.log), [small v2](../../run_logs/m1_eval_sem1wheel_small120_v2.log), [large v2](../../run_logs/m1_eval_sem1wheel_large120_v2.log). This closes the evaluation bug, not obstacle behavior.

Baseline/Candidate Ref4b5251f plus uncommitted M1 work. [Metrics](../../Go2Pvcnn/ame_baseline/m1_evaluation_metrics.py), [evaluator](../../Go2Pvcnn/scripts/evaluate_m1_ame.py), [tests](../../Go2Pvcnn/tests/test_m1_evaluation_metrics.py). Rerun the three fixed-seed scenarios with the new failure field before future behavior acceptance.
