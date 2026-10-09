# 2026-10-08 true multipoint contacts and grouped wheel load

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:82fa957. Candidate Ref:this contact-adapter commit.
Stage: WBC contact geometry and load contract; no contact control yet.
Key Files: [geometry](../../Go2Pvcnn/ame_baseline/m1_wbc_contacts.py),
[QP](../../Go2Pvcnn/ame_baseline/m1_wbc_qp.py),
[probe](../../Go2Pvcnn/scripts/probe_m1_contact_prepare.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-contacts.md).

## Implementation and CPU evidence

Point Jacobians shifted from actual wheel COM by angular-Jacobian cross offset.
Normal/tangent frames right-handed, per-point owner retained. No collapse into
wheel center or force-weighted single point. Material velocity test verifies
forward-moving wheel center plus spinning wheel can give zero bottom-point speed.
Distinct point locations preserve distinct moment arms.

QP optional group_ids/min/max impose summed per-wheel normal bounds. Two points
per wheel with max60N perpoint and wheelmin90N can support98.1N/wheel, without
incorrectly requiring90N at every point. Excess group demand fails without effort.
RED6missing adapter/group tests plus RED observer wiring; GREEN52regressions.
CPU pytest WBC contacts/QP/free/dynamics/probe + existing point-Jacobian suite.

## Native evidence

Existing --wbc_snapshot observer creates4wheel contact views in env0 before32step
warmup, reads positive normal-force points at native physics dt, checks valid
buffer ranges/no repeated indices and vector force closure. Distinct records
with coincident positions remain separate because native forces sum correctly.
Normals are validated, not silently flipped; no fictional friction forces.

GPU7 raw log:/tmp/m1_wbc_contacts_20261008.log, copied to local artifacts.
Command probe_m1_contact_prepare.py --num_steps1 --wbc_snapshot --device cuda:0
--headless; 300s timeout, original collision/actuator settings. Exit0; no PREPARE/lift.
Wheel point counts[2,3,2,2],9total. Normal-force closure max7.62939453125e-6N
(threshold1e-3); point velocity reconstruction error9.395251382438019e-9.
Read-only geometry verification, not a dynamic rolling/stance result.
Placeholder354723 verified/stopped;532072 restored and verified soleGPU7compute,
10624MiB. No training, display, driver or unrelated process change.

## Remaining work

Rolling acceleration/Jdot*v not yet supplied to QP; never fix all wheel centers
in place or difference changing contact patch IDs. Next derive/test that contract,
read effective material friction, then native support and single-leg stages.
Only env0 geometry sampled here; no all-environment contact coverage claim.
Complete obstacle/landing/avoidance and policy-only gates remain open.
