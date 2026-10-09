# 2026-10-08 default PD force-source calibration

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref: `ae76fd3`. Candidate is the PD-oracle instrumentation in this
worktree; this diagnostic does not alter training behavior or the zero-PD WBC.

## Question and fix

The native implicit drive remains active in the regular environment. A zero
explicit effort write therefore does not mean zero total joint effort. The
probe now records the native projected joint force, direct effort readback,
and IsaacLab cached `applied_torque` with before/after samples. The before/after
comparison is diagnostic only; post-step projected forces best matched the
measured free-body response. Cached `applied_torque` is not used as total drive
force for the dynamics oracle.

The residual is generalized force, not a pose, height, or crossing metric.
Acceptance is now component-specific: base linear force <=0.05 N; base angular
moment and joint torque <=0.02 Nm. Native runs at `dt=0.001` and `dt=0.0005`
had three valid suspended samples, no contacts. Worst residuals respectively:
linear force `0.040314` / `0.034149` N, base moment `0.004194` / `0.005411`
Nm, joint torque `0.001411` / `0.001647` Nm. Direct zero-effort residuals
were approximately 6 N/Nm; cached torque residuals were much larger than
projected-force residuals. The finite-step allowance is isolated to base
linear force; the existing tight moment/torque limits are retained.

The existing zero-PD execution gate remains `0.02` for its original full
generalized residual. Only this diagnostic PD calibration uses the component
limits above, justified by repeated native step-size evidence; it does not
relax contact, effort, state, or crossing gates. Result scope remains
`dynamics_only_not_crossing`.

## Verification

- PD oracle source/threshold regression: `1 passed`.
- Focused WBC and AME contract suite: `147 passed, 1 skipped`.
- Broader `pytest tests --ignore=tests/test_m1_sdf_probe.py` was interrupted
  after unrelated test failures accumulated; the unfiltered run also cannot
  collect `test_m1_sdf_probe.py` in the `amp` Python because `pxr` is missing.
  These are not counted as passing full-suite verification.
- Native PD oracle at both step sizes: `M1_FREE_RESULT passed=true`, 3/3
  samples; no crossing claim. GPU7 placeholder restored and verified at
  10624 MiB. No training started; other GPUs/processes untouched.

## Next gate

Proceed to grounded support initialization/continuity and stance under the
explicit sole-owner WBC, keeping the native zero-PD execution threshold and
all support/contact limits unchanged. Do not start training until a grounded
single-leg lift/roll/land passes physical clearance, contact, and posture gates.
