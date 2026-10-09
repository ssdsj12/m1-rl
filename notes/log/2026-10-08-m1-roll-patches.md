# 2026-10-08 M1 rolling contact patch attribution

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), baselineec17048.

## Change

Read-only roll_substep_audit now captures row7 named wheel contact patches and
articulation position/velocity targets, actual states and computed torques.
No source USD/control/gate changes. RED missing row7_contacts; GREEN7 observer,
contact-buffer and substep tests. Existing named force and mass weighting covered.

## Baseline physical evidence

GPU7 original128 SDF command unchanged. All lift_samples exactly equal to ec17048;
same ROLL6 rejection, no LAND. Placeholder4135886 stopped;4162027 restored.
Raw `/tmp/m1_roll_patches_20261008.log` SHA256
aae637a57f21f480e5ecfa740dce28213dc61c20d8f4508f2b65f22abc272db0.

Row7 FBL action95 native5ms patches: six candidate contact points each sample;
active normal-bearing counts3,1,2,2. Total normal43.8025,43.9282,46.2919,12.2139N.
At the final transition minimum separation changes .987116mm to1.182089mm,
normal-bearing positions change. Wheel joint velocity .228317→.250187rad/s;
computed wheel torque1.32441→1.31961Nm; legABAD/HIP/KNEE
[-.66620,-1.25571,-4.36185]→[-.53451,-1.32724,-3.96267]Nm.
All position/velocity targets exactly unchanged across the four substeps.
Thus target jumps and torque saturation are not supported by this evidence.
Contact patch/discretization coupling is a hypothesis, not yet unique cause.

## Controlled comparison

Compare source SDF256 versus128 only, same rest/contact offsets, mesh source,
mass/inertia, controller, gains, timestep, budgets and guards. This tests collision
discretization, not a parameter/gain sweep. No long training or promotion before
physical result. Source asset remains unchanged.

Result:256 rejects LIFT5, row3 FBL9.62363N under unchanged10Ncontact guard,
before anyROLL. Mass/inertia/material invariant output exactly equals128 run.
Raw `/tmp/m1_roll_sdf256_20261008.log` SHA256
73535dd5660f86f7e9d951f53bed852d0cea5d5b988af1d04b82b85f4d083e35.
Higher resolution is NOT a fix and is not promoted; original128 defaults remain.
Placeholder4162027 stopped for comparison;4171104 restored sole GPU7compute.
The paths diverge early, so this cannot establish a unique ROLL failure cause.
Next source collision-surface continuity/contact-controller coupling, not another
resolution/gain sweep. No training, landing, obstacle or policy success claimed.
