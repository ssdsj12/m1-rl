# 2026-10-08 rolling continuity diagnostic

## Change versus 1adefe7

Default-off `--roll_continuous_ramp` starts the scalar rolling profile from the
maximum incoming held-wheel command instead of assuming zero. The per-wheel
0.2m/s2 slew remains authoritative; this is not identical per-wheel initial speed.
Reject an incoming speed that cannot stop by the existing deadline. No contact,
effort, posture, phase budget or height thresholds relaxed. Default path unchanged.

## Verification

- RED: five new tests failed before implementation (missing initial API/flag).
- GREEN: 149 regression tests pass; git diff --check passes.
- Baseline previous run: 20 ROLL steps, LAND11 contact loss at 8.193N.
- Existing zero-start ramp comparison: ROLL3 rejects; row1 RBL27.86675N.
  Its zero-start assumption brakes a pre-existing nonzero hold command.
- Continuous-start comparison: initial0.0304629933m/s, completes six ROLL
  actions; pre-action step96 rejects row7 FBL12.213946N (<30N advancing floor).
  Margin0.0376684m, tilt[0.003035,-0.001469]rad, so geometrical support margin
  and near-level body do not guarantee dynamic support force.
- All eight measured rises159.974..160.275mm; no LAND, no crossing proof.
  Exit0 means diagnostic finished, not acceptance. No training started.
- GPU7 placeholder4066928 was verified/stopped for this comparison;
  restored4102845 verified sole GPU7 compute process. Other GPUs untouched.

## Artifacts

- `/tmp/m1_land_ramp_20261008.log`
  SHA256 5cf4157090fa96efe9e76bf2e63cbbe74d111bbb056ffdaf2d0deed38627ab38
- `/tmp/m1_roll_continuous_20261008.log`
  SHA256 2812b598b674ab83e4fa87f31a7b841bfd1c03bb9692fdc1053e06e79a5de23d
- Full local copies in m1_probe_audit/artifacts.

## Next architectural child

Three speed/handoff comparisons do not solve measured support transients. Do not
continue gain/profile sweeps or lower force floors. Audit inertial/load transfer
and couple wheel acceleration/braking to measured support and COM trajectory,
including landing handoff. Existing static allocation cannot certify dynamics.
New ramp remains diagnostic-only; do not promote it as physical improvement.

See [T306](../todo/T306-m1-ame-long-train-stability.md).
