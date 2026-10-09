# Height-only selected frame: exact FK contract, transfer-bound rejection

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), unload-realization.
Baseline Ref:2ae21f5. Candidate Ref:containing commit.
Key files:m1_selected_world.py,m1_single_lift.py,probe_m1_contact_prepare.py,
test_m1_selected_world.py.

## Change

Default-off height_only mode preserves nominal selected body-frameXY, solves
bodyZ from measured rootZ/attitude and requested worldZ using ZYX rotation row2.
Only selected3joints change; stance9 staynominal. Frame backtracking, full25mm/
.08rad guards, IK/joint/slew checks retained. Nearhorizontal bodyZ rejected.
Existing vertical_only mode unchanged; mutuallyexclusive. Diagnostic flag
unload_height_only propagates through UNLOAD and LIFT world_feedback, preventing
a silent return to older correction during phasehandoff. Defaults unchanged.

## Verification

TwoRED unexpectedkeyword failures, then46tests11.87s: selectedworld,singlelift,
wheelhold,unloadgate. Exact FKworldZ andbodyXY verified for allfourlegs withtilt,
nine stancejoints unchanged; excessive frame and joint-slew protections tested.
Syntax check passes. These prove kinematic contract, not contact stability.

GPU7,8envseed2,sourceSDF128,1mmrest/2mmcontact,100PREPARE/100UNLOAD,
phasewheelhold and prior completecycle parameters. Replace vertical_only with
height_only; allphysics/reserve/time/effortlimits unchanged.
Raw:/tmp/m1_hold_height_only_20261007.log; session45000 terminalexit0.
Result unload_com_rejected at12,12UNLOADsamples, noLIFT.
Rows0/4(FAR) reason3, desiredrootshift80.611/80.617mm>80mm; previousaccepted
shift79.046/79.080mm. No limitincrease. Atstep11 heightreference0 allrows,
selectedforce34..52N, actualselectedwheel rise -1.55..-.25mm relativeentry.
This earlyfailure cannot prove desiredheighttracking improved physically.

## Interpretation / follow-up

Kinematic omission now has an explicit isolated candidate, but correcting selected
height while itscontact stillbearsload changes the coupled transfer transient.
Need inspect load-transfer desiredroot and observedCOM/supportgeometry across
first12frames, phase-effort ramp and height-correction timing. Do not attribute
failure solely to a0.6mm numerical overrun or increase80mm bound. Compare early
trajectory against vertical-only baseline; decide whether correction activation
must be coordinated with actual unloading/support readiness, with bounded
continuous handoff rather than a new gain sweep. Not production-promoted.
Fullcrossing,landing,obstacle,bypass,video,policy gates remain incomplete.

Placeholder3429808 stopped,3502498restored verified. No otherGPU/userjobs,
driver/display/sourceasset changes ortraining. Notes aligned. Localcommit only,
not uploaded. Improvement vs prior: tested exact-height control option and
physical evidence localizing next failure to early load-transfer feasibility.
