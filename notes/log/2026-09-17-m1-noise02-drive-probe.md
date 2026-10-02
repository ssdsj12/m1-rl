# M1 low-noise physical exploration gate

## Purpose / Stage / Related Todo

Test whether std=0.2 exploration remains physically stable while rolling; M1 action/control, [T306.6a](../todo/T306-m1-ame-long-train-stability.md).

## Procedure / Inputs

amp, GPU4, 8 env x 300 steps, seed42, flat. `TRAIN_ENTRYPOINT=Go2Pvcnn/scripts/probe_m1_rewards.py`, `PROBE_ACTION_STD=0.2`, via single-run validation wrapper. Legs hold the training stance plus Gaussian noise; wheel target ramps to0.4m/s plus noise. Push disabled and no reset velocities. Same physical config as the [no-noise rolling gate](2026-09-17-m1-floating-drive-gate.md).

## Metrics / Result

[Runtime log](../../run_logs/m1_noise02_drive_probe.log): mean forward displacement1.704161m, resets0, undesired-contact/geometry-collision rewards zero, all observations and per-term rewards finite; complete marker and exit0. Mean weighted action-rate cost=-0.129018, consistent with analytical -0.128. Weighted torque cost=-0.458052; linear+yaw rewards0.955411+0.324048. The noise-free probe advanced1.604376m; this small difference is not evidence for a learned improvement.

## Conclusion / Follow-up / Git Refs

Candidate noise passes the physical gate. It does not establish learned stability: next run is a fresh 1024x120 A/B with only the initial noise changed. Baseline/Candidate Ref:4b5251f plus uncommitted M1 work. Key files: [probe](../../Go2Pvcnn/scripts/probe_m1_rewards.py), [train config](../../Go2Pvcnn/ame_baseline/m1_ame_train_cfg.py).
