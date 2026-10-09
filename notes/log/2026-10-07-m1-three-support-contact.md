# Lifted rolling contact and wheel-angle audit

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), rolling-support-control.
Baseline Ref: 4d267c9. Candidate Ref: containing commit.
Key files: probe_m1_contact_prepare.py, test_m1_roll_contact_evidence.py.

## Purpose / change

Distinguish loaded-wheel rolling from instantaneous velocity and determine whether
support-reference motion explains the low-speed failure. Added read-only measured
wheel joint angle to lift samples, and exact env3 FBL/FAR/RBL ground contact views.
Record normal and friction forces/points at rolling indices0,5,10,12,14. No action,
gain, geometry, budget or protection change. Static wiring RED2fail, GREEN14pass
in1.42s (contact evidence, speed CLI/profile); physical data checked separately.

## Procedure / actual evidence

Same command/config as [low-speed comparison](2026-10-07-m1-low-speed-support.md),
including .02cap, none-stage flat8seed2, shoulder diagnostic, GPU7. Raw output:
/tmp/m1_three_support_patch_20261007.log. Exit0; physical result again
rolling_support_rejected at104, no landing/crossing success. Local copy retained.

Env3 lifts RAR. From step90 to104, wheel joint angle changes (FBL,FAR,RBL,RAR):
0.0111469,0.00187409,0.00176950,0.000358373rad. At104 previous wheel targets
are0.2084245rad/s on support wheels; instantaneous RBL velocity is negative.
Thus sampled qdot must not be used as proof of sustained rolling.

Contact x positions at90 and104:
- FAR:0.33917632699,0.30915254354m, exactly unchanged.
- RBL:-0.31984090805,-0.34986466169m, exactly unchanged.
- FBL:both points move only7.9..8.5micrometers.
Heavy-wheel contact span30.024mm matches the coarse shoulder hull support face.
At104 normal+friction moment about each wheel center world-Y is approximately
FBL:-.1693,FAR:+.3134,RBL:+.2329Nm. These are single-substep contact samples,
not full joint/inertial dynamics balance or proven net rolling resistance.

Previously stored low-speed samples show support joint targets change at most
1.8e-7rad across all8 rows in the rolling window (row3 exactly0); no live load
redistribution is applied. This is a separate controller gap, not proof that it
alone causes no forward motion.

## Conclusion / next

Shoulder-model four-support rolling success does not transfer to this loaded
three-support low-speed condition. Contact-face discretization remains an active
traction hypothesis. Next compare a more faithful, finer contact representation
under identical original-envelope safety oracle and mass/inertia/materials,
before treating COM redistribution alone as the solution. No production tire
promotion, threshold relaxation, model-training or obstacle acceptance.
Placeholder2339056->2363319 restored and exact process verified. No other GPU,
display, driver or original-checkout changes.
