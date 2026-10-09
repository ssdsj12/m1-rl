# Wheel holding / unload pose attribution

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), unload-realization child.
Baseline Ref:5d20d7a. Candidate Ref:unchanged runtime at5d20d7a; containing notes commit.
Key files:m1_selected_world.py,m1_unload_reference.py,probe_m1_contact_prepare.py.

## Investigation

Re-read previous vertical-only and full-world comparison logs before comparing.
Vertical-only preserves nominalXY/attitude while using measured rootZ: it is
not exact world-height tracking when body roll/pitch differs from nominal.
In phase-hold baseline,596 row-frames fail unload_ready:588 have selectedforce>5N;
7 of the remainder have anotherwheel<30N;1 requires otherpredicate evidence.
Late40frames: no effort-settled inhibition; load_ready inhibits14/16frames in
FAR rows0/4,1frame in eachFBL,0rear. Thus universal effort inhibition is ruledout.

AtUNLOAD99 reference height2.06..3.90mm while actualselectedwheel rise is
negative(-1.625..-.211mm) relative entry. Actual-minus-reference error
[-3.850,-4.234,-3.584,-4.111,-3.672,-4.236,-3.388,-4.097]mm.
First-order worldZ effect using measured wheel-root lever and relative
roll/pitch, dz=delta_roll*lever_y-delta_pitch*lever_x:
[-4.337,-4.477,-3.739,-4.072,-4.181,-4.489,-3.605,-4.092]mm.
Agreement within~0.5mm supports missing attitude compensation as major height
error, not exact rigid-body proof. Entry FK residual only0.20..0.23mm.

## Controlled full-pose comparison

Existing selected-world tests + wheel-hold + unload-gate:21passed1.84s.
Same8envseed2 SDF128/rest1mm/contact2mm phase-hold fullcycle command, remove
ONLY --unload_vertical_only. Allphysical/effort/joint/time/frame guards unchanged.
Raw:/tmp/m1_hold_full_pose_20261007.log; session94554 exit0.
Result unload_world_pose_rejected at15, noLIFT. Rows0/4 actual/reference dr
approximately[-15.75,-20.19,-1.65]mm => exceeds25mm bound. Nominal fulljoint
step~.01543rad> .01rad and frame safe=false; backtracking cannot authorize it.
Yaw error develops~-.023rad(FAR),+.024rad(FBL). This reproduces lateral/frame
coupling with fullXYZ correction despite wheelholding; do not promote fullpose.

## Next action

Need world-height correction with no selected-wheel horizontal correction while
contact persists, rather than either ignoring tilt or correcting completeXYZ.
Candidate: keep nominal selected body-frame x/y, solve body-frame z from actual
orientation/rootZ for desired worldZ; use same named M1 IK and alljoint slew/
limits/frame bounds. Verify exactworldZ with FK, nine stancejoints untouched,
no requested bodyXY change, finite rotation/reachability; physicaltest then gates.
This is the next hypothesis, not implemented or proven in this commit. Preserve
5N/30N/5frames and deadlines; no force filtering or success relabeling.
Per-env phase progression remains needed eventually; do not latch intermittent
batch readiness to hide contact recurrence. Real crossing/video/policy/bypass
acceptance remains incomplete.

Own3356222placeholder stopped,3429808restored verified. No runtimecode, asset,
driver/display/unrelated-process changes; no training. Notes aligned, localonly.
Improvement vs prior evidence: attribution now explains most height mismatch
and rejects fullXYZ compensation as a safe replacement under current control.
