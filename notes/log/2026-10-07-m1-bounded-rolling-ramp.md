# Bounded rolling acceleration diagnostic

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),rolling-support-control.
Baseline Ref:16c4f06. Candidate Ref:commit containing this log.
Key files:m1_rolling_speed.py,test_m1_rolling_speed.py,probe_m1_contact_prepare.py.

## Change / tests

Explicit --roll_ramp enables first/lastspeedzero and .2m/s^2 speed changes.
20frames/.4s give peak .036m/s and commanded integrateddistance .0072m,
not a planner for crossing an obstacle. Defaultstepcontrol unchanged for A/B.
RED8 missing-module;GREEN54focusedtests. Existing30N support,4saction and
2ssettle constraints unchanged. No changed leg control or wheel gains.

## Physical result

Same8flatseed2,90LIFT/20ROLL/90LAND,100SETTLEbudget,.12vertical/.16height.
Raw:/tmp/m1_rolling_ramp_20261007.log,native0. All20ROLLactions execute with
minimumsupport35.1103N,comparedto29.07N and9actionswithstepdrive.
This isolates a useful effect on supportload, NOT effective forward traversal:
lastloggednetprogress -0.394..+0.470mm,farbelowcommanded7.2mm andobstaclewidth.
Need wheel-speed tracking/traction andreference-ownership analysis before scaling
speed orcalling rolling successful. Don'treplacecrossinggoalwithmillimetre motion.

LAND reachesstep199;firstSETTLEadmissionrejects contact. Selected row1/5 normal
forces are8.016/9.694N atfinalobservation (previous11.77..15.27N),stopped=
settle_contact_lost_or_missing;landing_completefalse. Othercontactsremainloaded.
Next inspect whethercontactjitter shouldresetstablecounter ratherthan immediate
abort, preservingactualcontact,timeout,heldheight andfinal5frames>10N criteria.
Do not extendairborneactionorclaimtouchdownstability.

## Resource / next

Ownplaceholder1863813 stoppedexactly;1893212 restoredandverified. No unrelated
process/display/driver change orlongtraining. Nextactivechildren:effective-rolling
progress andlanding-contact-stability. Realobstacle/clearance/video/avoidance
acceptance andPPOintegration remainunachieved.
