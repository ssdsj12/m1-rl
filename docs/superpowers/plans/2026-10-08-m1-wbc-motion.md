# M1 live contact-motion evidence before actuation

Parent [dynamic WBC design](../specs/2026-10-08-m1-dynamic-wbc-design.md).
Baseline0b73832. No controller or physical thresholds changed.

1. Capture ALL native contact-buffer entries, including zero-force speculative
   points, separation, measured material-point velocity relative to terrain.
2. TDD motion decomposition using actual COM/omega/point geometry, distinguish
   wheel-center velocity, tangential slip, normal separation and moving ground.
3. Native read-only probe, compare contact motion with zero-velocity assumptions.
   Do not use force>0 filtering to infer no other impending contacts exist.
4. Record evidence before deciding live-mode recovery/stance constraints.
   No actuation based on rest counterfactual, no retraining until physical gates.
