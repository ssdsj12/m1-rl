# Flat lift/land/settle cycle passes measured gate

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),four-support-settle.
Baseline Ref:6629f36. Candidate Ref:commit containing this log.
Key files:m1_settle.py,test_m1_settle.py,probe_m1_contact_prepare.py.

## Change

Opt-in --settle_steps<=100 adds approvedseparate2s phase after original<=200step
LIFT+LAND. Fresh all4normalforces>10N required atentry andeverySETTLEframe; missing
or lost contact rejects, no extraairborne search. Existing descenthold already
freezes height whenselectedcontact exists. Five-frame PrepareGate plus prior
effortgap<=1Nm validatesstablelanding; admission itself isnot success. Phase/time
reported separately. RED2missingmodule;GREEN139focusedtests5.57s.

## Physical verification

Same8flatseed2 GPU7,90LIFT/110LAND/100SETTLEbudget, priorsearch/vertical/finite
unload flags plus --settle_steps100 (actualCLIspaced). Raw
/tmp/m1_settle_cycle_20261007.log,native0; stoppednull,landing_completetrue.
Finalsample236,phaseSETTLE,all8streak5.200LIFT/LANDactions+36SETTLEactions=.72s
settling after4s actionbudget; finalpreactiongate exitswithout furtheraction.
Finalselectedforces59.26,59.79,56.08,64.64,62.86,57.76,50.69,64.22N.
Finaleffortgapmax.001135Nm;roll/pitch componentabsmax.00953rad;other3COMmargin
.03093..03440m. Fourleg identities each testedtwice in8envs. Evidence iscontrol-
frame sampling, notsubstepcollision certificate. This verifies flatcycle only.

## Remaining scope / next

Flatcycle single seed cannotprove10cmobstacle+5cmclearance, forwardtraversal or
far-side touchdown. Next obstacle-cycle integration: actualselectedwheel-front
box geometry andlandingcorridor, explicitforwardprogress withco-moving support
references, measuredwheel-envelope clearance andcollision evidence. Review
trajectory timing to preserve required15cm+actualclearance within4s singleleg;
the90-step diagnosticpeak isnot that acceptance. Need3seeds/alllegs/video,
recovery/bypass andtruthfulmetrics beforeteacher/PPO integration/training.
Do not call this a trainedpolicy. No longtraining orpush.
GPU7preflight13.4GBfree; own1598746 stoppedexactly;1640307 placeholder restored
verifiedalive. No unrelatedprocess/display/driver changes.
