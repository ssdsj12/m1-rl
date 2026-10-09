# Rolling handoff isolation: initial braking is not the sole support failure

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), LIFT/ROLL support child.
Baseline Ref:03854c8. Candidate Ref: same code, runtime comparison only.
Key files:probe_m1_contact_prepare.py,m1_rolling_speed.py.

## Purpose and method

Inspect baseline wheel commands and existing LIFT transients before changing
control. Row1 support commands atLIFT89 were[.025761,.016934,.021942]m/s.
ROLL's independent zero-start triangular profile reduced these for3steps before
accelerating again. Hypothesis: this braking contributes to ROLL rejection.
Single-variable comparison removes only --roll_ramp; target remains.1m/s,
phase_hold_speed still owns continuous .2m/s2 slew from prior wheel commands.
No code, effort gains, acceptance thresholds, collision or deadlines changed.

## Tests and resource evidence

18 rolling-speed/COM tests passed1.45s.
Same GPU7 8envseed2 sourceSDF128/1mmrest/2mmcontact, UNLOADramp,phasewheelhold,
100PREPARE/100UNLOAD/90LIFT/20ROLL/90LAND/100SETTLE budgets.
Raw /tmp/m1_roll_handoff_20261007.log; session32402 terminalexit0.
Own4054047placeholder stopped;4155417 restored and verified.
No training/display/driver/otherGPU changes.

## Result

UNLOAD samples and first90LIFT samples exactly equal to baseline, confirming
the comparison first differs at rolling. Commands now monotonically accelerate:
row1 firstsupport .029761→.065761m/s over10executedROLLsteps.
Baseline rejects global95/ROLLoffset5 row1RBL29.694N.
Comparison rejects global100/ROLLoffset10 row5RBL27.718N; allotheradvance true.
Final progress allpositive .000790.. .001482m, versus baseline negative
.000015.. .000255m. This is only0.8..1.5mm, NOT obstacle traversal.
No LAND or SETTLE, no full crossing success, no candidate promotion.

## Independent preexisting LIFT transients

Below30N observation counts byrow [0,4,3,1,0,3,1,2] over90LIFTsamples.
Worst row7 at72:17.3699N, then76:17.7590N, beforeROLL began.
Row1 dips at35,70,81; last81=28.85394N. These are not caused byROLLhandoff.
LIFT currently pauses height progress on advance=false, whileROLL rejects.
Do not relabel the lift as uniformly>=30N or smooth away unexaminedtransients.

## Conclusion / next

Initial braking is undesirable for forward progress but removing it does not
solve loaded three-support control. Next inspect/validate proactive support
redistribution throughLIFT andROLL, including existing moving-load proposal
and boundedCOMtrajectory with currentSDF (previous negative tests used older
contact variants). Verify remaining rootdisplacement, actual loads, momentum
and phase ownership before any enablement. Do not increase gains or reduce30N
just to pass. Full5cmclearance/4cmlanding/sixobstacles/bypass/video/policy-only
goals unchanged. Evidence/notes commit only; nothing uploaded.
