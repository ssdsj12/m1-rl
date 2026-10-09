# Anticipatory reference integration and first physical comparison

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), anticipatory-support child.
Baseline Ref: e52c698. Candidate Ref: this commit. Stage: experimental flat-contact probe,
not teacher/PPO or learned crossing. No upload claimed.

## Delta from previous version

- `m1_anticipatory_support.entry_plan` uses frozen entry root/attitude/anchors,
  named wheel coordinates and authored M1 masses. 2401 candidate poses x 17 heights;
  every sample must retain 35 N / 20 mm static support, existing IK/pose bounds.
- `fixed_reference_step` executes a fixed entry goal through the existing
  0.05 m/s2, 0.04 m/s, 80 mm reference ramp and 0.5 rad/s joint slew.
- Opt-in `--anticipatory_prepare` reuses this goal in PREPARE and UNLOAD;
  legacy late-COM transfer cannot overwrite it and UNLOAD does not ramp twice.
  Final PREPARE gate requires reference convergence AND existing measured gates.
  Runtime currently rejects nonzero selected attitude changes; it never ignores them.
- `load_usd_model` reads original authored frames/masses without stage modification.
  Source inventory comparison allows 1e-10 quaternion string-rounding difference.
- Defaults unchanged; no safety threshold relaxation. PREPARE remains approved 4 s,
  other phase budgets unchanged. Original dirty checkout preserved.

## Verification

TDD RED: missing fixed-reference helper / entry-plan function (previous context),
missing USD loader, missing runtime opt-in. Integration helper tests subsequently pass.
Synthetic model initially asserted all rows feasible despite non-M1 zero local COMs;
corrected the test to independently verify accepted forecasts and rejected-pose fallback,
not production thresholds. Synthetic feasibility is not actual M1 acceptance.

74 passed with amp Python, OMP/MKL=2 and bundled USD library paths:
`test_m1_fixed_prepare`, `test_m1_anticipatory_wiring`, `test_m1_usd_model`,
`test_m1_prepare_budget`, `test_m1_prepare_gate`, `test_m1_lift_forecast`,
`test_m1_anticipatory_support`, `test_m1_mass_predictor`, `test_m1_com_trajectory`,
`test_m1_unload_gate`, `test_m1_unload_reference`, `test_m1_wheel_hold`.

Physical GPU7 probe: 8 envs flat, source SDF128/rest1mm, fixed physics,
PREPARE200, UNLOAD100 budget, LIFT90/ROLL20/LAND90, SETTLE100,
lift160mm, vertical0.12m/s, phase effort + wheel hold, existing ROLL load feedback
and COM trajectory, plus new `--anticipatory_prepare`. Exit0 is normal diagnostic
termination, NOT success. Log `/tmp/m1_anticipatory_prepare_20261008.log`, SHA256
`48c2c0d04c758be933f1233cba79b32d889a09c8c10e4904ea33987c03a6152d`.

## Physical result and cause

- All8 entry plans eligible with zero extra attitude.
- PREPARE200 completed, final all8 measured ready and reference ready;
  final support-plane margins31.69..44.82mm, no non-support contact.
- UNLOAD66 samples, LIFT37 samples; stopped `lift_effort_rejected` at LIFT36.
  No ROLL/LAND, `landing_complete=false`. Actual selected rise52.62..56.59mm.
- Allocation invalid only row0/FBL; row4/FBL is near the same boundary.
  Independent geometry calculation: row0 nominal static support36.446N,
  actual geometry static support29.99065N (<30N); native allocator rejects.
  Measured normal contact32.727N is dynamic and does not override static feasibility.
  Row4 actual static30.13859N. Not a 150Nm actuator saturation result.
- Row0 root tracking error[-5.188,-8.890,-4.245]mm; COM error versus nominal
  [-5.699,-10.010,-3.535]mm. Support-wheel XY anchor drift reaches18.150mm;
  across8 max support drift13.65..18.15mm. Using actual COM with frozen anchors
  falsely estimates49.669N for row0: moved support geometry matters critically.
- Pure entry-static planning therefore does NOT solve dynamic support. This candidate
  stops earlier than previous late-feedback flat lift; keep it opt-in, no promotion.

Read-only reproducer: `scripts/audit_m1_anticipatory_run.py <probe-log>`; computes
nominal vs measured geometry support and tracking errors. No actuation or GPU needed.

## Resource / follow-up

Verified own placeholder656674 exact command, stopped only it. Probe session22512
exited0; placeholder3872161 restored and verified as sole GPU7 compute application.
No training started; GPU3-7 unrelated tasks, XLaunch/Xorg/VNC and drivers untouched.

New open child: support-anchor drift / compliance during anticipatory hold.
Next identify lateral support-motion mechanism and bounded measured-geometry feedback
before another full-height attempt. Do not add shift, reduce force threshold, extend
other phase budgets, or call reference convergence actual pose convergence.
Obstacle-envelope clearance, rolling, landing, bypass and policy-only remain unverified.
