# Contact persistence versus stable landing

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),landing-contact-stability.
Baseline Ref:3fe33e1. Candidate Ref:commit containing this log.
Key files:m1_settle.py,probe_m1_contact_prepare.py,test_m1_settle.py.

## Cause / contract correction

Approvedspec sayscontactjitter resetsstabilitycounter. OldSETTLEadmission
requiredallforces>10Neveryframe andaborted with8..10N evenwhencontactpersisted.
Separate optional contact-persistence evidence fromunchangedstableacceptance:
selectedwheel musthaveexceeded10N duringLANDwithin4s,remain>1N; otherthree
mustremain>=30N. No airborne continuation.2smaximum andpose/collisionguards
unchanged. Finalsuccessstillall4>10Nfor5freshframes pluspose/margin/effortchecks.
SETTLE nowfreezesheightreference,zerowheels;no extra groundsearchpast4s.
Four-contactallocation persistswhilemeasuredcontactexists aftertouchdown,
instead ofswitchingbacktothreecontacts whenforce momentarilydropsbelow10N.

## Tests / physical evidence

RED2newtests failmissingselected/touchdown_seenarguments;GREEN65focusedtests,
then172fullfocusedsuitepasses13.54s. Testexplicitlyconfirmsthat8Nmaycontinue
settlingbutcannotincrementthe5framePrepareGate successcounter.0/1N,missing
touchdown,weakothersupportandtimeoutreject.

Raw:/tmp/m1_settle_persistence_20261007.log. Same8flatseed2GPU7,90LIFT/
20rampedROLL/90LAND/100SETTLEbudget,.12vertical/.16height. Native0,stoppednull,
landing_completetrue,lastsample244,allstreak5;44SETTLEactions=.88s.
Finalselectedforces63.47,54.01,59.00,66.66,62.77,51.50,56.33,65.92N.
HeightreferenceatfirstandlastSETTLEmatchesexactly:
[0,-.0006,.0007562,0,0,-.0004,.0008531,0]m. No extradescent.

## Still open

Thisisflatheldlegcycle,notobstaclecrossing. Fullrollingsegmentaudit confirms
atstep110 displacementstillonly-.977..+.508mm,notjustalaterretreatmaskinggood
forwardmotion. Effective-rolling-progress remainsblocking: inspect wheel
torque/friction/velocitytrackingandreferences,notblindlyraisecommands/gains.
Realgeometry/clearance/forwardtraverse/three-seed/video/avoidance/PPO pending.
No longtraining. Ownplaceholder1893212 stoppedexactly;1934277restoredverified.
