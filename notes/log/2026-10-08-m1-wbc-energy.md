# 2026-10-08 full mass / velocity / energy oracle and inertia-frame correction

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:029a543. Candidate Ref:this energy-oracle commit.
Stage: WBC model verification; read-only observer, no actuator changes.
Key Files: [snapshot/oracle](../../Go2Pvcnn/ame_baseline/m1_wbc_dynamics.py),
[probe](../../Go2Pvcnn/scripts/probe_m1_contact_prepare.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-dynamics.md).

Independent full mass: sum m*Jlinear.T*Jlinear + Jangular.T*Iworld*Jangular,
plus16joint armatures. Native world COM spatial Jacobian used. Measured link
velocities compared with J*[root COM linear/angular velocity, joint velocity].
Independent measured rigid-link energy plus armature compared with .5*v.T*M*v.

## Tests and initial negative result

Five RED tests missing oracle, then27GREEN across snapshot/wiring/Jacobian.
GPU7 same32warmup, --num_steps1 --wbc_snapshot --device cuda:0 --headless,
300s bound, no PREPARE/lift. Original actuator/collision/physics unchanged.
First /tmp/m1_wbc_energy_20261008.log exit0 but fullM error0.00902176 exceeds
predeclared1e-3; velocity error5.96e-8 and energy3.10e-5J. Not accepted.
Placeholder240899 stopped then260072 restored.

## Root-cause isolation

Installed get_inertias doc says COM-local. body_com_pose_w implementation composes
link rotation with principal inertia frame. Hypothesis: returned inertia instead
expressed in actor axes about COM, so principal frame rotation double-rotates it.
Read-only comparison /tmp/m1_wbc_inertia_frames_20261008.log, same8poses:
COM-frame candidate0.00902176 vs actor-frame3.8147e-6 fullM residual.
Raw inertia, COM quaternion and matrix difference logged. This supports the
installed-backend convention, not a universal claim about all versions.
Placeholder260072 stopped then266113 restored.

## Fix and final verification

AST regression RED proves observer used COM rotation. Fixed observer uses
link/actor rotation for inertia_world; rejected COM hypothesis retained as a
separate diagnostic field.28tests pass. No mass/inertia/sourceasset modified.
Fresh /tmp/m1_wbc_energy_fixed_20261008.log exit0,8rows:
fullM max3.814697265625e-6; link velocity max5.960464477539063e-8;
energy max2.2351741790771484e-8J. All predeclared thresholds pass without changes.
Raw logs copied to local audit artifacts. Placeholder266113 stopped then275143
restored, verified soleGPU7compute10624MiB. No training or display/driver changes.

Result verifies full mass and velocity frame consistency for these native poses,
including nonzero measured velocities. Does not validate Coriolis bias or actuator
force response. Next velocity-dependent compensation oracle/actuator ownership,
then constrained QP and complete physical crossing. All crossing gates remain open.
