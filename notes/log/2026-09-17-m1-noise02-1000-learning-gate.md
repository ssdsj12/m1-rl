# M1 1000-update learning-horizon gate

## Purpose / Stage / Related Todo

Distinguish an early-stage policy from persistent obstacle-stopping failure; M1 AME learning validation, [T306.6b](../todo/T306-m1-ame-long-train-stability.md). A120-update policy now passes flat but neither obstacle case. Current evidence does not isolate a reward-weight bug. Extend the development learning horizon before changing unrelated weights or curriculum.

## Procedure / Inputs

One fresh process, amp, physical GPU4, 1024 env, MAX_ITERATIONS1000, SAVE_INTERVAL100, seed42, init_noise_std0.2; no checkpoint/resume, no automatic restart. tmux `m1ame_noise02_1024x1000`, [runtime log](../../run_logs/m1ame_noise02_1024x1000.log), scripts/run_m1_validation.sh. Same config/code as120-update low-noise pilot; only maximum iterations and checkpoint interval change. All three preceding evaluations exited before launch.

## Metrics / Current Result

COMPLETED in one process, PID3161771, amp Python, devicecuda:4. Exact iterations0..999, one completion marker, exit0, total40,960,000 timesteps and7919.74s. [Saved config](../../logs/rsl_rl/m1_cross_large_complex_ame/2026-09-17_17-13-30/4b5251f/train_cfg.yaml) confirms std0.2. `model_999.pt` has iter999/next_iter1000; all138 checkpoint tensors and35 TensorBoard scalar tags are finite.

Behavior degrades after the early survival gain. Mean episode length is953.21 at iteration100,807.66 at200,12.72 at400, and70.05 at999. Bad-orientation terminations rise from0.024 at100 to0.9839 at400 and finish0.8826. Final std0.3081, reward-0.6286, geometry-collision reward-0.0122, speed error0.0444. Finite low final losses reflect short failing episodes and do not establish learning success.

Sequential fixed-seed evaluation of `model_999.pt`: [flat](../../run_logs/m1_eval_noise02_flat1000.log) goal/safe1.0, forward3.932765m; [small](../../run_logs/m1_eval_noise02_small1000.log) crossing/goal0, forward0.788769m; [large](../../run_logs/m1_eval_noise02_large1000.log) avoidance/goal0, forward0.542853m. All evaluations complete+exit0 with zero invalid-state terminations. The obstacle outcome is unchanged from120 updates.

## Acceptance / Follow-up

The gate fails behavior acceptance and shows late collapse. Investigate the reward conflict where forward wheel contact with a small obstacle is reported by geometry collision at weight-10 while obstacle airtime is only+0.1 and threshold0.5s. Confirm with a tensor/physical contact probe before changing semantics. Also audit scanner perception, spawn clearance and terrain exposure. Formal10000 remains gated by obstacle behavior improvement.

## Git Refs / Key Files

Baseline/Candidate Ref4b5251f plus uncommitted M1 changes. [Training config](../../Go2Pvcnn/ame_baseline/m1_ame_train_cfg.py), [single-run wrapper](../../Go2Pvcnn/scripts/run_m1_validation.sh).
