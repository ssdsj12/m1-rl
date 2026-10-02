# M1 wheel reward real8env physical signal gate

## Purpose / Stage / Related Todo

Verify approved progress/lift rewards produce finite real-physics signals while preserving collision behavior. M1 reward/physics integration,[T306.6g](../todo/T306-m1-ame-long-train-stability.md).

## Procedure / Input

amp Python,physicalGPU4,8env,seed42,600 steps,8m env spacing,0.05m semantic1 box atx0.9..1.1m,default legs and wheels ramp toaction0.4. Disable external pushes as in previous probes. Optional`PROBE_COMMAND_X=0.5`sets fixed forward command for reward calibration. No policy learning, checkpoint, restart or concurrent Isaac job.

```bash
env NUM_ENVS=8 MAX_ITERATIONS=600 DEVICE=cuda:4 PROBE_SCENARIO=small_contact PROBE_COMMAND_X=0.5 TRAIN_ENTRYPOINT=Go2Pvcnn/scripts/probe_m1_rewards.py VALIDATION_LOG=run_logs/m1_wheel_reward_probe_8x600.log bash Go2Pvcnn/scripts/run_m1_validation.sh
```

## Metrics / Result

[Runtime log](../../run_logs/m1_wheel_reward_probe_8x600.log): one entrypoint PID2045605,actual runtime`envs/amp/bin/python`,devicecuda:4. Physical policy/critic/action contract8×1581/8×1584/16. Complete marker and wrapperexit0; process exits.

- Full four-wheel crossing8/8,mean root forward3.0999999m,reset0.
- Geometry collision and undesired-contact reward both0 across4800 env-steps.
- `small_obstacle_progress`: weighted mean0.22949117,p95_abs0.96817762,nonzero2105/4800.
- `small_obstacle_climb`: weighted mean0.00241410,p95_abs0.01659759,nonzero1061/4800.
- Every observed state/reward/per-term tensor finite (probe asserts each step). Old airtime terms absent from active rewards.
- Same final wheel locations as isolated pre-reward-change probe: reward changes did not alter the externally prescribed physical trajectory. Command-related tracking/posture reward changes are expected from explicit0.5 command override.

This passes real signal wiring, not learned obstacle behavior or0.10m crossing. It does not validate large-obstacle avoidance.

## Follow-up / Git Refs

Fresh8env×2 PPO update smoke next; only then fresh1024×120 learning pilot and fixed evaluation. Baseline4b5251f+prior M1 work; candidate740f07e+uncommitted implementation. [Implementation record](2026-09-18-m1-wheel-reward-implementation.md).
