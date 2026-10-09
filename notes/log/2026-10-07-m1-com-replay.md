# M1 authored FK / mass-weighted COM replay

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), anticipatory-support.
Baseline Ref:088036a. Candidate Ref:this evidence commit, no runtime changes.
Key file:[replay script](../../Go2Pvcnn/scripts/replay_m1_com.py).

## Method

Read original composed M1 USD mass, local COM and both joint frames. Compose
16 named revolute transforms, including nonidentity FBL_HIP parent rotation.
Read actual12leg/4wheel angles from completed current-SDF load-feedback log
`/tmp/m1_sdf_load_feedback_20261007.log`. Use planner FBL,FAR,RBL,RAR order,
not articulation's grouped-by-joint order. Per-pose whole COM is sum(m_i*c_i)/M.
Historical samples lack root quaternion: fit proper rigid transform by SVD
to root and four wheel centers, then compare predicted COM with native COM.
This uses measured wheel centers for attitude and is NOT independent attitude
validation. It does not estimate dynamic forces or prove controller feasibility.

Command: bundled USD Python/LD paths as [inventory](2026-10-07-m1-mass-tree.md),
amp Python `scripts/replay_m1_com.py /tmp/m1_sdf_load_feedback_20261007.log`.
Read-only CPU replay, exit0, no GPU use or physics/control modification.

## Result

792 row-samples,17bodies/16joints across LIFT and short ROLL.
Maximum five-point rigid-fit residual3.11837335e-6 m.
Maximum whole COM residual4.33002094e-6 m (step84,row7).
This supports authored joint sign/frame and mass model consistency at recorded
lifted poses. No tolerances were used to alter records or the model.

## Next and scope

Build tested named-input predictor for candidate joints/root pose; validate with
direct native root quaternion and individual body COM, not wheel-fitted attitude.
Then evaluate anticipatory PREPARE/LIFT reserve within unchanged guards.
Do not promote offline pose agreement to dynamic support or crossing success.
All actual obstacle-clearance, stable traversal/landing, bypass and policy gates
remain open. No training started; existing placeholder left running.
