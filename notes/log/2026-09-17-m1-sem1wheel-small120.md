# M1 semantic1 wheel-contact pilot: small evaluation

## Purpose / Stage / Related Todo

Check learned small-box crossing after the semantic1 wheel-contact fix; AME behavior gate, [T306.6c](../todo/T306-m1-ame-long-train-stability.md).

## Procedure / Input / Result

amp,GPU4,8env,seed42,500 steps, fixed0.10m high x0.20m long x1.20m wide semantic1 box centered at x1.5m. Model119 from [fresh pilot](2026-09-17-m1-semantic1-wheel-120-training.md), `EVAL_SCENARIO=small`. [Runtime log](../../run_logs/m1_eval_sem1wheel_small120.log).

Crossing/goal/safe success0, forward1.034230m, lateral0.015769m; collision episode/step rate0 and invalid-state rate0. Complete marker+exit0. The policy approaches farther but stops. Earlier0.05m open-loop contact probe is not equivalent to a full0.10m crossing; run matched height/full-wheel diagnostics before attributing all remaining failure to reward. Original evaluation predates the explicit failure-termination metric; zero success is unaffected by the known false-positive loophole.

## Git Refs / Key Files

Hardened rerun: [v2 log](../../run_logs/m1_eval_sem1wheel_small120_v2.log),same numerical results,failure_termination_rate0,complete+exit0. Stopping is not a reset/termination artifact.

Baseline/Candidate Ref4b5251f plus uncommitted M1 work. [Evaluator](../../Go2Pvcnn/scripts/evaluate_m1_ame.py), [M1 rewards](../../Go2Pvcnn/ame_baseline/m1_ame_rewards.py).
