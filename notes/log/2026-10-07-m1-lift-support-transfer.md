# Support-aware LIFT hold: bound rejection before support loss

Stage: diagnostic LIFT; parent
[T306.support-load-distribution](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:`3a97ac2`; Candidate Ref:commit containing this log.
Key files:`m1_single_lift.py`, `test_m1_single_lift.py`, `probe_m1_contact_prepare.py`.

## Change / verification

Per-row advance_mask freezes selected-wheel target height without overriding
existing guards. RED reproduced missing hold; GREEN and full focused suite:
87 passed in5.56s, exit0. Same eleven-file command as previous log.
Probe syntax check passed. Added opt-in --lift_support_transfer, mutually
exclusive with pose-feedback experiment. Defaults unchanged.

Diagnostic permits further rise only with measured margin>=20mm and all three
nonselected forces>=30N (preventive hold threshold, not replacement for10N
failure guard). Otherwise it holds the current wheel target and calls existing
bounded transfer_target with measured support geometry and elevated selected
anchor. Original phase-entry root/Z/RPY and8cm total command bound retained.
It does not yet implement recovery or full crossing coordination.

## Physical result

GPU7 flat8 seed2,32standing/100PREPARE/200maximumlift,dt.02, speed.04,bound.08.
Command adds --lift_steps 200 --lift_support_transfer to existing probe.
Log:/tmp/m1_contact_lift_support_transfer_20261007.log, native exit0.
stopped=lift_guard_rejected atliftstep8, rows0/4 reason103 (transfer reason3:
required target beyond bound). Their margins19.74/19.58mm trigger hold.
All measured wheel forces remain positive, minimum59.80N in this final sample.
Targetrise5.6..7.2mm, actualrise -3.75..-.67mm; no meaningful lift.
Thus proactive hold avoids the previously observed later loss in this short
trace but does NOT pass lifting, stability-duration or crossing acceptance.

## Specific follow-up, not an increased bound

Existing transfer seeks soft30mm whenever measured margin<20mm. Its full soft
target can exceed8cm before taking a small bounded step. Need explicitly solve
whether a target satisfying hard20mm remains feasible inside the same8cm bound;
preserve the negative result and verify a constrained hard-margin alternative
before declaring geometric infeasibility or increasing available displacement.
New child under support-load-distribution:hard-margin-bound-feasibility.
Potential force-distribution/attitude issues are not resolved by this finding.

## Resources / remaining scope

Exact own placeholder634517 stopped/restored660878, verified alive. Other user
ldc3227360 remains alive. No reset/display changes, long training or push.
Full recovery, clearance/traverse/landing/events/collision/video/bypass and PPO
remain open. This is an optional diagnostic candidate, not a trained model.
