# Single-wheel LIFT: implementation and negative physical evidence

Stage: contact-driven diagnostic LIFT. Parent:
[T306.contact-transfer.single-lift](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref: `6c7d94f`; Candidate Ref: commit containing this log.
Key files: `m1_single_lift.py`, `test_m1_single_lift.py`, `probe_m1_contact_prepare.py`.

## Change relative to previous version

Previously the diagnostic stopped after PREPARE. Added an opt-in vertical
single-wheel target with frozen other-wheel anchors and prepared root reference.
Three nonselected supports must exceed10N, tilt/rate stay bounded, measured COM
remain inside their planar triangle. PREPARE still requires20mm and five frames.
The caller rechecks fresh readiness before lifting. Diagnostic aborts on invalid
proposal, support/collision guard or episode reset; this is NOT recovery.

Actual M1 IK, joint limits and .5rad/s slew apply. Fixed .08m/s Cartesian advance
initially failed slew tests; backtracking reduces Cartesian progress rather than
clipping joint angles or raising limits. Maximum target rise18cm is a diagnostic
ceiling, not obstacle-top clearance or physically achieved height.

## CPU verification

RED tests were created before the module; fixed-speed attempt failed slew.
Eight lift contracts now pass. Full focused regression:83 passed in4.98s, exit0:
`amp/bin/python -m pytest -q tests/test_m1_single_lift.py
tests/test_m1_load_transfer.py tests/test_m1_support_observer.py
tests/test_m1_prepare_gate.py tests/test_support_geometry.py
tests/test_crossing_event.py tests/test_probe_evidence_contract.py
tests/test_m1_foot_frame.py tests/test_m1_cache_foot_frame.py
tests/test_m1_runner_wheel_parity.py tests/test_m1_unreachable_teacher.py --tb=short`.
Probe syntax check passed. This does not prove dynamics or crossing.

## Physical runs

GPU7/amp; flat8, seed2, selected legs[0,1,2,3,0,1,2,3]. Standing32 steps,
PREPARE100 steps, dt.02s, speed.04/bound.08, then `--lift_steps 32` or200.
Common entry: `scripts/probe_m1_contact_prepare.py --device cuda:0 --headless
--num_steps 100 --transfer_speed .04 --max_root_shift .08`.

1. `/tmp/m1_contact_lift_8x32_20261007.log`: native0, all32 lift samples,
   stopped=null. Final target25.6..29.6mm but measured rise -2.78..0.86mm.
   Selected wheels still loaded; final margins5.65..17.80mm. NOT lift success.
2. `/tmp/m1_contact_lift_8x200_20261007.log`: native0, guard stops atstep36,
   env3 nonselected leg0 force8.794N<10N (reason2). Remaining rows valid at that
   instant. Target29.6..37.6mm, actual -2.48..1.34mm. Rear selected wheels begin
   unloading but have not achieved significant clearance. Margins2.46..16.63mm.
   Max final tilt .03846rad; no large-angle instability required to reject.

Tracking trace rows0..3: root height changes during lift -5.50,-5.14,-7.85,-8.82mm;
some loaded knee tracking errors ~.05.. .0812rad. Fixed prepared references do
not keep the physical root/COM fixed under unloading. These data establish the
failure stage, not a complete causal proof that a gain change alone would fix it.

## Resource lifecycle

Exact own placeholder538748 stopped/restored587494 for32-step run; then587494
stopped/restored598258 for200-step run. Both native0 and restored process verified.
Other user ldc PID3227360 remains alive. No GPU reset/display/driver changes,
no training or GitHub push. Raw logs also copied to local audit artifacts.

## Follow-up and acceptance gaps

New child T306.contact-transfer.lift-support-tracking: distinguish support-force
redistribution, root attitude/COM drift and actuator tracking/effort limits before
changing control. Add bounded feedback/support compensation using frozen phase
references rather than integrating measured sag; test safe rejection/recovery.
Do not relax support limits or label a commanded18cm as achieved clearance.

Still open: recovery, obstacle-derived lift/traverse/landing, substep collision
oracle, three-seed per-leg/video/6-obstacle and bypass gates, PPO/policy-only.
Diagnostic remains optional, existing training behavior unchanged.
