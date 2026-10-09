# Separate live support feedback from fixed IK anchors

Stage: AME PREPARE; child [T306.contact-transfer.front-feasibility](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref: `1f26d2a`; Candidate Ref: commit containing this evidence.
Key files: `m1_load_transfer.py`, `test_m1_load_transfer.py`,
`probe_m1_contact_prepare.py` under Go2Pvcnn.

## Root-cause evidence

Offline independent half-plane projection over the saved speed04 trajectory:
`/tmp/m1_analyze_prepare_bounds.py /tmp/m1_contact_prepare_flat_speed04_8x100_20261007.log`.
At step53 env0, live margin4.01mm; a frozen support polygon predicts only6.52mm
additional COM translation to meet hard20mm, while measured polygon needs15.99mm.
Env1: frozen polygon needs0mm, measured needs10.06mm. Controller and gate used
different geometries after wheel drift. For front rows, rigid-translation estimate
of total root displacement to meet hard20mm is59.5..60.6mm; soft30mm target needs
69.3..69.9mm. These are geometry-only estimates, not safe dynamic-motion guarantees.

## Implementation

`transfer_target` now requires explicit `support_w` measured positions for stability
projection. `anchor_w` remains frozen and is used only for IK. No default fallback
to stale support positions. Probe passes the same observer wheel positions used
by readiness assessment. Missing/nonfinite support data refuses advancement.
No displacement/speed/stability threshold changed in this update.

## Verification

RED: two tests failed because `support_w` was missing from the API. GREEN:
69 focused tests passed in3.18s using the same 10 test files listed in
[prior physical log](2026-10-07-m1-prepare-physical.md).
Tests verify projection changes with measured support motion while IK still
roundtrips to unchanged original anchors; invalid row does not affect other rows.

Actual GPU7 seed2 flat8x32, speed.02m/s, bound.06m, joint slew.5rad/s:
`/tmp/m1_contact_prepare_live_support_8x32_20261007.log`.
All32 control samples completed; native exit0; proposals valid8/8; no stop.
Final readiness4/8 (rear legs), rear margins27.99..31.04mm, front margins
-18.57..-11.33mm. This physically exercises live support wiring and the prior
satisfied-target freeze, but does not establish front PREPARE success or crossing.
No lift, training or video acceptance claim. No full substep collision oracle claim.

Exact placeholder466385 stopped; restored placeholder502175 observed alive.
Other user ldc PID3227360 remains alive. No display/driver changes or GitHub push.

## Next

Resolve measured COM response and bounded feasible displacement/time for front
legs without lowering the20mm readiness gate. Current6cm displacement cap and
2cm/s default cannot be assumed sufficient merely because IK is reachable.
Full phase coordinator, strict metrics, bypass, physical per-leg/video testing
and policy-only learning remain open. Do not train on this partial controller.
