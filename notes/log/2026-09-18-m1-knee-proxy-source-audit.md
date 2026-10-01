# M1 front-knee proxy and contact measurement source audit

Follow-up: [event replay and isolation fix](2026-09-18-m1-probe-neighbor-contamination-fix.md) closes the72-event issue as a probe neighbor-obstacle ownership mismatch, not a demonstrated source-hull false positive. Runtime reporter threshold is now confirmed1N. The source measurements below remain valid limitations; the next-step section records the historical state before that replay.

## Purpose / Stage / Related Todo

Investigate the72/4800 geometry events from the completed0.05m full-wheel probe, without weakening penalties or changing the pending reward design. M1 geometry/measurement contract, [T306.6f](../todo/T306-m1-ame-long-train-stability.md).

## Inputs / Procedure

Read-only CPU USD inspection in amp, no Isaac application or GPU job. Open the source M1 USD; transform each enabled front-knee collision mesh into its body-link frame; require exactly one mesh per knee authored as convexHull. Use scipy ConvexHull and the production `get_robot_backend('m1').surface_points_builder` (float64 CPU) to compare source geometry and actual reward proxy samples. The audit does not mutate the USD or stage. [Script](../../Go2Pvcnn/scripts/audit_m1_knee_proxy.py), [raw output](../../run_logs/m1_knee_proxy_cpu_audit.log).

Runtime setup uses amp Python with PYTHONPATH set to the installed `isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310` directory and LD_LIBRARY_PATH to its `bin`; invoke `Go2Pvcnn/scripts/audit_m1_knee_proxy.py`. No additional package installation was required.

An independent source audit traced current contact selectors, thresholds and sampling through installed IsaacLab45, then the primary agent directly checked the relevant source excerpts. No physical contact A/B was performed this pass.

## Geometry Results

Both FBL_knee_box and FAR_knee_box:

- Enabled source collision mesh:282342 vertices, authored approximation convexHull.
- Proxy AABB vs link-local source AABB maximum boundary difference:1.1921e-8m. This rules out a simple local bounding-box dimension/center typo, not a live FK pose error.
- Source convex hull volume0.0026637633m³; proxy box volume0.00362213775m³; ratio1.359782 (35.98% more volume).
- All26 production box surface samples lie outside the source convex hull by the1e-5m tolerance. Maximum signed supporting-plane gap0.0348021m.
- USD knee/foot joints have Y axes, identity local rotations and translations matching the FK constants: knee `(0,±0.0442,-0.26)`, wheel `(0,±0.0592,-0.28)`.
- CPU audit completed successfully. These are source-hull comparisons, not verification of PhysX's cooked hull/contact offsets and not proof that every one of the72 runtime events is false.

## Contact Measurement Results

`undesired_contacts` selects the12 ABAD/HIP/KNEE links using sensor-owned body indices and counts links whose maximum recent net-normal-force norm is strictly greater than1N. Wheels/base are not in that reward term. The data sums normal forces per link; it excludes tangential friction and can in principle hide opposing normal forces on the same link.

The current sensor uses history_length3 at physics_dt0.005s, while decimation4 means reward is computed every0.020s. Installed SensorBase immediately updates a history-enabled sensor each physics substep; ContactSensor rolls3 entries. Thus only substeps4/3/2 remain at reward time; a contact confined to substep1 can be omitted. This is a measurement limitation identified from source, not an observed explanation of the72 events.

Another layer: asset `activate_contact_sensors=True` is passed by installed `sim/utils.py:293` as the second positional argument of `schemas.activate_contact_sensors(prim_path, threshold=0.0)`, then written into the PhysX contact reporter's float threshold. The source call therefore supplies1N rather than the helper's default0N. Actual runtime stage value and its effect on the GPU tensor reporting path remain unverified. The sensor's separate force_threshold only controls air/contact-duration state and must not be conflated with the reward threshold.

Key installed-source anchors: `isaaclab/envs/mdp/rewards.py:260`, `sensors/contact_sensor/contact_sensor.py:355`, `sensors/sensor_base.py:183`, `sim/utils.py:293`, `sim/schemas/schemas.py:472`. Repository anchors: [contact config](../../Go2Pvcnn/go2_pvcnn/tasks/teacher_elevation_trajectory_mpc_semantic_env_cfg.py), [reward selector](../../Go2Pvcnn/ame_baseline/m1_ame_env_cfg.py), [reward threshold](../../Go2Pvcnn/tracking/cross_large_complex_ppo_env_cfg.py).

## Conclusion / Next Step

Correct wording for the earlier probe:72 knee-proxy collision samples did not trigger the current1N/3-frame undesired-contact reward. A zero reward is not proof of no physical contact. Do not disable knee collision or widen semantic1 tolerance to knees based on that zero.

One remaining useful bounded diagnostic is a same-config8env x600-step replay that captures only the hit events: live FK vs named PhysX knee poses, production hit-point indices in knee-local/world coordinates, named raw contact history and actual stage reporter thresholds. Compare those event geometries with the source convex hull, noting cooked-hull uncertainty. This adds evidence only; no reward, physics material, collider or threshold change. The user has not yet approved the new progress/climb reward semantics.

## Git Refs / Scope

Baseline/Candidate Ref4b5251f plus existing dirty M1 work. This pass adds a diagnostic script and notes only. No training launch, no restart supervisor, no change to policy/observation/action/reward behavior. Formal10000 and learned obstacle acceptance remain open.
