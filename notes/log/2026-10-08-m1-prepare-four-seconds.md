# User-confirmed PREPARE budget: four seconds

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:8b8b0a9. Candidate Ref:this commit.
User confirmation received2026-10-08 for PREPARE2s→4s only.

## Change

Approved design updated PREPARE maximum4s. Probe permits1..200controlsteps
at existing20ms control period (default32 remainsunchanged; runs must explicitly
request200). This does not make the old controller anticipate liftedCOM.
LIFT/TRAVERSE/LAND shared4s, SETTLE2s and recovery2s unchanged. Contact,
force, pose, collision, displacement and clearance contracts unchanged.

## Verification

Actual probe AST budget test observed RED:200rejected, thenGREEN afterchange.
Boundary tests assert200accepted/201rejected/0rejected and liftstill200max.
33tests pass:preparebudget,preparegate,liftforecast,anticipatorysupport,
probeCOMevidence. No new GPU/physical run for a CLI-bound-only change.
Goal reactivated after userconfirmation. Sourceworktree original preserved.

## Next

Wire causal frozenentry forecast into opt-in bounded PREPARE reference,
requiring referencearrival plus existing measuredcontact readiness. Keep
selectedreference continuous through UNLOAD; do not let legacy lateCOM
feedback silently undo anticipatory plan. Validate defaultoff/regressions,
then explicit200step GPU7physicalcompare; restore ownplaceholder onexit.
No pending budgetapproval; do not askagain. Crossing/bypass/learnedpolicy
still unverified. No longtraining started and no upload claimed.
