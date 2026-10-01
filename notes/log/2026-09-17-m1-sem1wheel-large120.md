# M1 semantic1 wheel-contact pilot: large evaluation

## Purpose / Stage / Related Todo

Check large obstacle avoidance after the semantic1 wheel-contact fix; AME behavior gate, [T306.6c](../todo/T306-m1-ame-long-train-stability.md).

## Procedure / Input / Result

amp,GPU4,8env,seed42,500 steps, fixed0.80m high x0.60m long x1.20m wide semantic2 box centered at x1.5m. Model119 from [fresh pilot](2026-09-17-m1-semantic1-wheel-120-training.md), `EVAL_SCENARIO=large`. [Runtime log](../../run_logs/m1_eval_sem1wheel_large120.log).

Avoidance/goal/safe success0, forward0.507398m, lateral0.027027m; collision episode/step rate0 and invalid-state rate0. Complete marker+exit0. It stops before the box instead of taking a side route. Large avoidance remains a separate open behavior requirement; do not count stopping as avoidance. Original evaluation predates the explicit failure-termination metric; zero success is unaffected by the known false-positive loophole.

## Git Refs / Key Files

Hardened rerun: [v2 log](../../run_logs/m1_eval_sem1wheel_large120_v2.log),same numerical results,failure_termination_rate0,complete+exit0. Stopping is not a reset/termination artifact.

Baseline/Candidate Ref4b5251f plus uncommitted M1 work. [Evaluator](../../Go2Pvcnn/scripts/evaluate_m1_ame.py), [metrics](../../Go2Pvcnn/ame_baseline/m1_evaluation_metrics.py).
