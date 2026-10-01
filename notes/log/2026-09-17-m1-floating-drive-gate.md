# M1 floating-base and rolling-drive gate

## Purpose and Procedure

Run scripts/probe_m1_rewards.py through the amp headless launcher on GPU4, seed 42, 8 environments, flat ground, 300 physics-control steps. Legs hold the balanced training pose; wheel surface speed ramps to 0.4m/s. Pass requires no resets, mean progress >0.2m and post-warmup illegal-body/geometry contact fraction <0.05.

## Evidence / Result

- Earlier probes exposed fixed_base=True, then incorrect root API ownership, then insufficient leg support and a backward-offset support polygon. Training-only spawn conversion releases root_joint and migrates ArticulationRootAPI to BASE_LINK.
- Wheel angle limits are continuous; policy remains 16 actions with named legs/wheels.
- [Old-gain control](../../run_logs/m1_drive_control.log): damping 0.5, progress 0.002482m, zero resets; flat rolling assertion fails, VALIDATION_EXIT_CODE=1.
- [New-gain probe](../../run_logs/m1_drive_gain_probe.log): damping 5.0, progress 1.604376m, zero resets; undesired_contacts and geometry collision both zero; VALIDATION_EXIT_CODE=0. Actual USD wheel effort limit remains 50Nm. This gain is simulation-calibrated, not a manufacturer parameter.
- [Joint-property diagnostic](../../run_logs/m1_drive_diag.log): wheel joint friction=0. [PhysX diagnostic](../../run_logs/m1_collider_diag2.log): real wheel stiffness=0 and damping=0.5. [Mesh diagnostic](../../run_logs/m1_mesh_diag.log): wheel geometry axis/extent agrees with the M1 wheel envelope.

## Conclusion and Follow-up

Physical flat rolling passes. This is scripted control, not learned obstacle behavior or 10000-update stability. Preserve those separate gates.

## Stage / Related Todo

M1 AME physical environment, reward and training validation; [T306](../todo/T306-m1-ame-long-train-stability.md).

## Git Refs

Baseline Ref: `4b5251f`. Candidate Ref: `4b5251f` plus uncommitted M1 adaptations. These results are not evidence for a clean committed tree.

