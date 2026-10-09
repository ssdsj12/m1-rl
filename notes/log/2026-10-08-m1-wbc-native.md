# 2026-10-08 M1 native full-dynamics static consistency

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:2d1ee63. Candidate Ref:this observer commit.
Stage: native read-only WBC adapter verification, no controller/actuator change.
Key Files: [probe](../../Go2Pvcnn/scripts/probe_m1_contact_prepare.py),
[wiring test](../../Go2Pvcnn/tests/test_m1_wbc_probe.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-dynamics.md).

Added default-off --wbc_snapshot: after existing32warmup steps, read validated
full generalized M/gravity/Coriolis and compare gravity to mass-weighted body-COM
Jacobian; compare base translation inertia to total mass times identity. Log raw
matrices/vectors/names/velocities, then stop before PREPARE actions. No setters in
new observer. Existing physics, source collision and actuator settings retained.

RED: missing opt-in wiring assertion. GREEN:22tests (wiring+snapshot+Jacobian).
GPU7 command: amp/bin/python scripts/probe_m1_contact_prepare.py --num_steps 1
--wbc_snapshot --device cuda:0 --headless, CUDA_VISIBLE_DEVICES=7, M1_OBSTACLE_STAGE=none,
300s hard timeout and EXIT placeholder restoration. Exit0, stopped=wbc_read_only_complete.
Raw log:/tmp/m1_wbc_native_20261008.log, copied to local audit artifacts.

Eight rows: gravity residual max3.0517578125e-5 (generalized force components,
N/Nm by coordinate), translation mass residual max3.814697265625e-6kg,
symmetry error0, minimum M eigenvalue across rows0.003969839353483089.
Both predeclared1e-3 static tolerances pass. No PREPARE or lift samples generated.
Native backend supports the full APIs and matrices satisfy finite/SPD checks.
This confirms static gravitational sign against the verified COM Jacobian, not
all coordinate conventions or Coriolis/nonzero-velocity inverse dynamics.

Own placeholder99388 verified soleGPU7compute and stopped;240899 restored and
verified soleGPU7compute,10624MiB. No training, no X/VNC/GPUreset changes.
Next: independent velocity/energy and full generalized mass/frame oracle before
actuator sign response and QP. Stable crossing/landing/avoidance remain unproven.
