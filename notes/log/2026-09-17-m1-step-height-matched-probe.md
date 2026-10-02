# M1 matched-height full-wheel diagnostic

Follow-up: [isolated probe A/B](2026-09-18-m1-probe-neighbor-contamination-fix.md) proves the72 residual geometry events below came from a neighbor's collision-filtered obstacle. Matching evaluator spacing8m retains0.05m all-wheel8/8 and0 resets, withgeometry events0. No training reward or collision mask was relaxed; the0.10m fixed-pose and learned obstacle gates remain failed.

## Purpose / Stage / Related Todo

Separate an inappropriate wheel-crossing reward from insufficient fixed-pose physical traversal; physical M1 contract, [T306.6e](../todo/T306-m1-ame-long-train-stability.md).

## Procedure / Inputs

Extended the existing bounded diagnostic script, not the training policy: `PROBE_OBSTACLE_HEIGHT_M` controls box height (default0.05m). Report per-environment minimum of the four final wheel-center x positions, relative to env origins. Full-wheel clearance requires every wheel center beyond obstacle rear edge1.1m plus wheel radius0.095958m. Resets are reported independently and must be0 for a valid full traversal claim. The historical root>1.2m assertion remains a contact/progress diagnostic, not full crossing acceptance.

Both runs: amp,GPU4,8env,seed42,600 steps,legs hold default stance,wheel action ramps to0.4,no stochastic action noise,box x0.9..1.1m. `TRAIN_ENTRYPOINT=Go2Pvcnn/scripts/probe_m1_rewards.py`, `PROBE_SCENARIO=small_contact`, single-run wrapper.

## Result

[0.10m log](../../run_logs/m1_step10_drive_probe.log): all-wheel clearance0/8,mean root progress0.816085m,max wheel z0.195926m,3722 near-obstacle env-steps,0 resets and0 geometry/undesired contacts. Per-env minimum wheel x:[0.3912,0.8046,0.3221,0.3728,0.8036,0.3641,0.3926,0.8045]m. Airtime exactly0,air-time variance mean-0.022577,joint torque mean-1.272580. All600 steps executed; the final progress assertion intentionally fails and wrapper reports exit1. This is a measured inability to complete this fixed-pose rolling maneuver, not an Isaac premature exit.

[0.05m control](../../run_logs/m1_step05_full_drive_probe.log): all-wheel clearance8/8,mean root progress3.083970m,minimum wheel x per env2.4386..2.9203m,0 resets,max wheel z0.146050m and1863 near-obstacle env-steps. Complete marker+exit0. Airtime remains0. The geometry proxy reports72/4800 nonzero env-steps (1.5%;mean weighted reward-0.15) while undesired contacts stay0; so this is a full physical traversal, not a completely proxy-collision-free traversal.

Added a per-official-shape diagnostic without changing any collision mask or weight. [Shape probe](../../run_logs/m1_step05_shape_probe.log) completed+exit0 with exactly the same trajectory metrics; the events come exclusively from `FBL_knee_box` and `FAR_knee_box`,72 env-steps each, not support wheels. Next compare these box proxies against USD/PhysX knee collision geometry and contact thresholds before calling this a false positive. Do not disable knee/body collision penalties merely because the physical maneuver finishes.

## Conclusion / Follow-up / Git Refs

The0.05m/300-step contact probe cannot prove whole-robot traversal of the0.10m evaluation step. Need M1-appropriate obstacle locomotion guidance, not only removal of wheel collision penalties. User-facing design question proposes signed commanded progress and forward-coupled wheel climb instead of inherited0.5s airtime; approval pending before changing reward semantics. Stop, wheel spin and stationary leg lifting must not yield positive progress reward; semantic2 must remain excluded.

Baseline/Candidate Ref4b5251f plus uncommitted M1 work. [Diagnostic script](../../Go2Pvcnn/scripts/probe_m1_rewards.py), [reward contract](../../Go2Pvcnn/ame_baseline/m1_ame_rewards.py).
