# 2026-10-08 M1 articulated acceleration bias

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), child of dynamic rolling
support. Stage: read-only WBC kinematic adapter and bounded suspended oracle.
Baseline Ref:eecc94f. Candidate Ref:this kinematic-bias commit.
Key Files: [adapter](../../Go2Pvcnn/ame_baseline/m1_wbc_kinematics.py),
[tests](../../Go2Pvcnn/tests/test_m1_wbc_kinematics.py),
[native probe](../../Go2Pvcnn/scripts/probe_m1_wbc_free.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-kinematics.md).

## Contract

Single-row named model/state input, actor orientations and world angular velocities.
Base generalized linear acceleration is root COM acceleration, NOT root actor
origin acceleration. Recursion computes body origin, COM and angular bias at
zero generalized acceleration. Root origin centripetal correction, parent angular
cross joint velocity, and parent/child joint-offset lever arms are retained.
Reject nonfinite input, improper rotations, bad quaternions, mismatched/duplicate
names, invalid/cyclic trees, inconsistent native angular velocities (>1e-5rad/s).
No gravity double-counting, no controller/actuator ownership change.

## CPU verification

10 RED tests failed because adapter absent, then GREEN. Independent two-joint
3D central-difference oracle including nonidentity joint frames and offset rootCOM,
h=1e-4s, tolerance2e-6m/s². Exact zero velocity/root centripetal cases1e-12.
Permutation and malformed-input rejection included. Separate probe RED verifies
opt-in native acceleration oracle wiring; GREEN suite63passed in2.05s.
Command: PYTHONPATH=. OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
amp/bin/python -m pytest -q tests/test_m1_wbc_kinematics.py
tests/test_m1_wbc_contacts.py tests/test_m1_wbc_qp.py tests/test_m1_wbc_free.py
tests/test_m1_wbc_dynamics.py tests/test_m1_wbc_probe.py tests/test_m1_dynamics.py.

## Native verification

GPU7 only, exact placeholder532072 verified solecompute then stopped; EXIT trap
restored650836, confirmed soleGPU7compute10624MiB. No other GPU/process/config change.
Existing suspended free-body probe, new opt-in --kinematic_bias, --device cuda:0
--headless, defaultdt.001s, timeout300s. Eight M1s z2m, nativePD0, initial nonzero
joint/root velocities, unchanged3 diagnostic efforts0,+.01,-.01Nm.
Before each step, compute bias from authored M1 model and actual native actor
rotations/angular velocities. After step, compare measured COM/angular velocity
difference with native J*measured_generalized_qdd+bias, all17bodies x8rows x3ticks.
Predetermined tolerances .02m/s² linear and .02rad/s² angular, not changed after run.

- Maximum linearerror:0.0007429122924804688m/s².
- Maximum angularerror:0.0013516470789909363rad/s².
- Bias nontrivial:max0.1131623312830925 (components have linear/angular units).
- Omitting bias produces combined component max0.11285360157489777; preserve
  separate linear/angular units for acceptance, combined max only counterfactual.
- Existing full free-body dynamics resultpassed=true,3samples; no contact.
- Raw:/tmp/m1_wbc_kinematic_20261008.log, copied to local artifacts.

## Conclusion and follow-up

Kinematic acceleration mapping verified for tested native motions; NOT a support
or crossing test. Native source USD, production actuator defaults and displayed
scene unchanged. Effective friction and rolling contact-migration derivative
remain open before native stance. Fixed material-point acceleration is generally
nonzero for smooth pure rolling: do not lock it to zero or difference patch IDs.
No long training started, no model success claim. Goal remains open.
