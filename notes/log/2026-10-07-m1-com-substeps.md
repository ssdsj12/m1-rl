# M1 mass-weighted COM motion during support loss

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), dynamic-support child.
Stage: diagnostic UNLOAD; no controller or training change.
Baseline Ref: 8216867. Candidate Ref: containing commit.
Key files: probe_m1_contact_prepare.py, test_m1_unload_telemetry.py.

## Improvement relative to baseline

Extend the existing opt-in 5ms observer with mass-weighted body COM linear
velocity, root angular velocity and named XYZ normal-contact force. Root
velocity alone is not whole-robot COM velocity. Existing actuator commands,
phase gates, collision geometry, acceptance bounds and defaults are unchanged.
The test executes the actual nested observer AST against nonuniform masses
and shuffled wheel indices, not a separate reimplementation.

## Verification

RED: missing com_velocity KeyError. GREEN: new telemetry test plus existing
substep observer tests, 3 passed in 1.36s. Installed articulation_data.py confirms
body_com_lin_vel_w uses link COM velocities. ContactSensorData explicitly says
net_forces_w is normal force only, not total friction-inclusive force.

Physical command: previous support-substeps command unchanged, GPU7, 8env,
100 PREPARE / 100 UNLOAD budget, source SDF128 with 1mm rest/2mm contact,
phase_wheel_hold, settled height-only correction; only observer fields added.
Raw /tmp/m1_com_substeps_20261007.log, session80517 terminal exit0.
All unload_samples compare exactly equal to baseline. Same
unload_com_rejected at53; no LIFT or crossing acceptance.
Raw field wheel_force_xyz was subsequently renamed wheel_normal_force_xyz
to avoid falsely implying friction is measured; numerical computation unchanged.

## Evidence and limits

At final substep of action48 and52 respectively, COM velocity (m/s):
- row0/FBL selected: [0.010848,0.010313,0.006323] ->
  [0.006779,-0.002563,0.005533].
- row1/FAR selected: [0.010608,-0.009140,0.005796] ->
  [0.004819,0.005397,0.004528].
Over80ms mean horizontal acceleration is approximately
row0[-0.05086,-0.16095], row1[-0.07236,+0.18172] m/s2.
Root roll rates at52: row0 -0.059906, row1 +0.038088 rad/s.
Normal-force XY components are approximately zero on the flat floor. They
do NOT prove absent traction: the API omits tangential friction.
Wheel-hold commands at52 remain roughly17..27mm/s on the three supports.
These observations establish nonstatic motion during unloading, not that
wheel traction is the unique root cause. Root angular velocity is not whole
robot angular momentum. Do not substitute root acceleration into a COM model.

## Next

Dynamic-support child: inspect friction-capable contact query / momentum balance
before changing static support allocation. Need coordinate commanded COM,
support load and attitude during selected-leg release. No further blind gain,
height, acceptance-threshold or root-shift relaxation. Later obstacle5cm
clearance, landing4cm, six-obstacle/video/bypass/policy gates remain unverified.

Only exact own placeholder3692792 stopped;3835014 restored and verified.
No other GPU, display, driver or training changes. Notes aligned. Local commit
only; no upload success claimed.
