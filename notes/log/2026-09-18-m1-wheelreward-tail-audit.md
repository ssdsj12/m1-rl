# M1 wheel-reward pilot tail and behavior audit

## Purpose / Stage / Related Todo

Compare learning signals after the approved reward change,without mistaking finite values for behavior success. Read-only TensorBoard/config comparison,[T306.6g.1](../todo/T306-m1-ame-long-train-stability.md).

## Inputs / Procedure

Oldrun[sem1wheel](../../logs/rsl_rl/m1_cross_large_complex_ame/2026-09-17_21-26-16/4b5251f),newrun[wheelreward](../../logs/rsl_rl/m1_cross_large_complex_ame/2026-09-18_10-52-23/740f07e),bothfresh1024×120. EventAccumulator withall scalar events; select actual iterationsteps100..119,not wall-time tags. Independent agent analysis was checked by the main agent's freshCPU read. Savedenv_cfg recursive comparison has onlyfour changedpaths: rewards/feet_air_time,rewards/air_time_variance,rewards/small_obstacle_progress,rewards/small_obstacle_climb. The finite-validity converter code fix is additional and not represented by YAML.

## Last20 Means

| Metric | Old | New |
| --- | ---: | ---: |
| track_lin_vel_xy |0.568902|0.572942|
| geometry collision |−1.584558|−1.628046|
| flat orientation |−0.012728|−0.014418|
| joint position |−0.209593|−0.214623|
| joint torques |−0.775605|−0.878601|
| noise std |0.333822|0.367371|
| bad orientation |0.001432|0.012518|
| episode length |981.479|974.879|
| total reward |−42.979165|−46.283057|

Newprogress mean0.00386370 andclimb mean0.0000904140;both20/20 nonzero. Their last20linear slopes are+0.000218 and+0.000001761 perupdate. Small signals are genuinely present,not console-rounding zeros. Bad-orientation mean is8.74×the oldbaseline;newtail itself is roughlyflat rather than escalating,while noise std keeps increasing. Totalreward/posture/torque/geometry show adverse signals; finite tensors and approximately975-step episodes do not support a new numerical blow-up at this horizon.

## Result / Conclusion / Follow-up

All three real fixed evaluations complete+exit0:[flat](2026-09-18-m1-wheelreward-flat120.md)8/8,forward4.89728m;[small](2026-09-18-m1-wheelreward-small120.md)0/8,1.07456m;[large](2026-09-18-m1-wheelreward-large120.md)0/8,0.50969m. No collision/invalid/failure termination in anyscene. New reward wiring and120-update runtime are verified; learned crossing/avoidance are not improved on this seed. Training-timeTB lacksvalid-semantic1 opportunity/conditional exposure. Next bounded diagnosis measures these gates on the fixedsmall trajectory without changing reward/config/policy; this trajectory alone cannot establish training-distribution frequency. Do not launchformal10000or sweepweights from these means.

## Git Refs

Baseline4b5251f+priorM1work,candidate740f07e+uncommitted implementation. Keyfiles[m1_obstacle_rewards](../../Go2Pvcnn/ame_baseline/m1_obstacle_rewards.py),[evaluator](../../Go2Pvcnn/scripts/evaluate_m1_ame.py). No production code changed during this verification.
