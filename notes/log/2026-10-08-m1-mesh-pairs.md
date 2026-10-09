# 2026-10-08 exact opposite-face cleanup diagnostic

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), baselinec89d2cf.

## Cause investigation and bounded change

All original wheels contain five coincident triangle pairs (10 faces).
Keeping one face from each creates7boundary/4nonmanifoldedges; removing both
oppositely wound faces leaves zero boundary/nonmanifold/misoriented edges.
This is an exact cancellation, not coordinate welding/rounding in authored data.
All4wheel CPUchecks pass. Signed volume changes only-1.0842e-19m3; sampled
support functions across720azimuths x3cambers remain exactly equal.
Closed oriented edges do NOT establish absence of self-intersection.

Default-off diagnostic_sdf_clean_pairs applies only to in-memory sourceSDF
collision meshes. SourceUSD, points, materials,mass/inertia, control and safety
thresholds unchanged. Ambiguous/same-winding pairs and nonclosed remaining
surfaces rejected. No generic remeshing or simplified tire geometry.

## Tests

RED3missing-helper failures; GREEN3 pure tests. USD integration initially lacked
PhysxSchema registration; using installed schema resources resolved setup.
Then observed RED missing clean_pairs keyword; GREEN13 helper/USD/planner/
telemetry tests. Default geometry-preservation tests remain green.
Environment for CPUUSD tests additionally uses PXR_PLUGINPATH_NAME pointing to
omni.usd.schema.physx/plugins/PhysxSchema/resources; no installation changes.

## Physical comparison

Original5ms/SDF128/1mmrest full-cycle command plus explicit cleanup flag only
(translation-only entry capability is already current baseline).
Raw `/tmp/m1_clean_pairs_20261008.log`: rolling_support_rejected at90/ROLL0;
row2 FAR18.7209N and row3FBL26.0555N below30Nadvance floor. LIFTguard remains
valid, noROLL action orLAND. Cleanup is NOT sufficient and not promoted.
Placeholder13723 stopped after exact verification;62471 restored soleGPU7compute.
No training, sourceUSD or unrelatedGPU change.

Next inspect event-gated LIFT→ROLL settling within existing total budget. Current
fixed90step transition can reachROLL with measured support below advance floor;
geometry fixes alone cannot establish a stable handoff. Do not weaken guards or
average away transients. Whole crossing/video/policy acceptance remains open.
