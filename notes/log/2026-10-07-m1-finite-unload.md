# Finite contact approach passes unloading, exposes LIFT handoff

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),finite-unload-progress.
Baseline Ref:0d954cd. Candidate Ref: commit containing this log.
Key files:m1_unload_reference.py,test_m1_unload_reference.py,probe_m1_contact_prepare.py.

## Evidence and change

Baseline last30steps rows2/6 had no effort/load holds, force8.23/9.25->5.79/5.61N,
reference advance only.780/.848mm. Proportional speed falls near1mm/s as force
falls. Add opt-in minimum contact approach .003m/s while force>target(0N here),
otherwisezero. Default0 preserves old behavior. Existing.01m/s cap,.02m height,
effort-settle/load guards and2s budget unchanged. This is measuredcontact approach,
not a success shortcut. RED2missingkeyword;GREEN132focusedtests5.18s, including
zero-contactstop, effort hold and heightcap coverage.

## Physical result

Same8flatseed2 GPU7/100PREPARE/100UNLOAD/200LIFT budget, priorvertical flags plus
--unload_min_speed .003. Raw /tmp/m1_finite_unload_20261007.log,native0.
UNLOAD94samples,finalforce[0,0,1.9583,0,0,0,2.5397,0]N,readystreak
[12,54,18,10,5,49,8,7]. All8 satisfy measuredforce/support/pose/effort criteria
for>=5freshframes within budget. This validates unloading only, not full lift.
Then stopped=lift_guard_rejected. One LIFTsample is pre_action rejection atstep0,
validfalse/reason6 all8 (slew), zero executedLIFTactions. Support margins.02985..
.03342m; non-supportforces0. OldLIFT IK reverts selected frame and causes handoff
discontinuity. Do not call the single logged sample a successful liftstep.

## Next

Child continuous-unload-lift-handoff: preserve accepted selectedframe/nominal
support references across transition; verify first action and subsequent live
frame update under samejoint limits/slew. Add regression for no reference reset.
No global slew relaxation. Actuallift,obstacles,landing,recovery,bypass andpolicy
validation remain open. No longtraining or push.
Own1427632 placeholder stoppedexactly;1451314 restored verifiedalive. No other
process/display/driver changes.
