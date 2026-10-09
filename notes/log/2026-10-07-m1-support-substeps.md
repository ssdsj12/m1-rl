# Named support-force audit and substep persistence

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), three-support-load child.
Baseline Ref:66a260e. Candidate Ref:containing commit.
Key file:probe_m1_contact_prepare.py; existing m1_substeps observer unchanged.

## Ordering correction (supersedes prior human labels)

Authoritative M1_PLANNER_JOINT_NAMES and M1_WHEEL_JOINT_NAMES order is
FBL,FAR,RBL,RAR, not FAR,FBL,RAR,RBL. Rows0/4 selectFBL,1/5FAR,2/6RBL,3/7RAR.
Earlier logs labeling row0 orrow4 FAR are wrong human labels; numeric row/force
values remain unchanged. Runtime resolves names into asset order; no runtime
leg-index mismatch was found in inspected paths. Do not copy humanlabels into
control. Articulation telemetry order is FAR,FBL,RAR,RBL grouped byjointtype.

AtUNLOAD52 front cases lowwheel is opposite rear: rows0/4RAR,rows1/5RBL.
Mapped byname, targetforce=[34.090,34.570,33.968,34.649]N,
measured=[28.590,26.031,26.981,27.600]N. Lowwheel kneePD estimates
[-.405,+.575,+.602,+.170]Nm, FF[-2.451,-2.572,-2.435,-2.583]Nm.
The initially suspected~-18Nm kneePD came from mixing planner/asset orders;
it is NOT evidence of large conflicting effort on the underloadedwheel.
Do not compensate/cancel torque based on that mistaken attribution.

## Instrumentation / test

Add default-off unload_substep_audit: existing read-only scene.update wrapper
captures native normal wheel forces and root linear velocities at5ms, labeled
with wheel_names andselected. No extraactions or changedcontrol.
Existingobserver tests2passed1.36s, syntaxpass. Same fullcycle settledheight
command plusonlyobserverflag onGPU7,8envseed2,sourceSDF128/1mmrest/2mmcontact.
Raw:/tmp/m1_support_substeps_20261007.log; session68440 terminalexit0.
Sameunload_com_rejected53,53actions. Finalforce andlastroot exactlyequal baseline.

## Physical evidence

Four5ms-substep means of underloaded rearwheel in rows0,1,4,5 respectively:
- action48:[40.868,37.460,40.692,38.428]N;
- action49:[36.245,39.025,35.399,36.092]N;
- action50:[33.111,28.206,32.035,31.680]N;
- action51:[28.405,26.084,26.630,24.967]N;
- action52:[26.554,22.654,23.591,24.253]N.
At52 every sampled force for allfour lowwheels<30N, not just finalsample.
Thus sustained dynamic load decline, not stalecache/singleendpointnoise.
Do not smooth it away or reduce acceptancefloor. NoLIFT/crossing acceptance.

## Next

Investigate base/COM acceleration, angularmomentum and contact/friction moments
through40..53 against static normal-onlyallocation. Static target34N isnot
achieved bydynamicplant; correcting selectedheight releases previous support.
Need coordinated unloading/support response under existingbounds, not another
heightincrease, PDcancellation frommisindexed logs, or thresholdchange.
Fullobstacle/landing/bypass/video/policy acceptance remainsopen.

Own3579350placeholder stopped,3692792restoredverified. No training,driver,
display,sourceasset,otherGPU/user changes. Notesaligned;localcommit only.
Improvement vs66a260e: corrected namedattribution and nonmutating substep evidence
separate real supportloss frommeasurement artifacts; no newcontrollerfixclaimed.
