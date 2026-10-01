# M1 initial exploration budget

## Purpose / Stage / Related Todo

Investigate policy collapse separately from simulator process stability; M1 PPO initialization, [T306.6a](../todo/T306-m1-ame-long-train-stability.md).

## Input / Procedure

The 1024 x 120 pilot uses the inherited Go2 action std=1.0. Its saved train_cfg.yaml confirms that value. M1 action units are 0.25rad leg targets and 1m/s wheel-surface speed. For independent Gaussian noise, E[||a_t-a_(t-1)||²]=2*d*std². The 16-dim action-rate weight -0.1 therefore has expected cost 3.2 before timestep scaling, versus maximum linear+yaw tracking reward 2.25. Stronger M1 leg gains also make large target noise physically aggressive. This is an initialization mismatch hypothesis, not proof that it is the only collapse cause.

## Metrics / Result

At pilot iteration 71, mean reward=-1.30 and mean episode length=9.30 steps; bad-orientation terminations remain approximately 98%. The process itself is still advancing without restarts.

RED: test_m1_exploration_cfg expected action-rate noise cost to stay below 10% of maximum tracking reward, but got 3.2; 1 failed, 1 passed. Candidate: M1-only init_noise_std=0.2 gives expected cost 0.128, initial leg noise 0.05rad and wheel-surface noise 0.2m/s. Go2 default remains 1.0. GREEN: exploration + action + evaluation metric focused suite, 10 passed in 1.39s.

## Conclusion / Follow-up

Only the config regression has passed; physical/noisy rolling and a fresh training A/B remain required. The currently running pilot keeps its loaded std=1.0; changing the source does not alter that process. Do not launch 10000 based only on this analytical fix, or label the collapsing pilot a successful behavior result.

## Git Refs / Key Files

Baseline Ref: 4b5251f plus floating M1 changes. Candidate Ref: same uncommitted worktree plus [M1 train config](../../Go2Pvcnn/ame_baseline/m1_ame_train_cfg.py) and [regression](../../Go2Pvcnn/tests/test_m1_exploration_cfg.py).
