# Selected-world-frame unloading experiment

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), unloading-realization.
Baseline Ref:0e12f28. Candidate Ref: commit containing this log.
Key files:m1_selected_world.py,test_m1_selected_world.py,probe_m1_contact_prepare.py.

## Ownership and change

Opt-in --unload_world_pose keeps stance9 joints owned by existing nominal
COM/anchor controller; selected3 use IK interpolating command pose toward fresh
measured pose. No additional integrated root correction, gain, or threshold change.
Backtracking factors1,.5,.25,.125,.0625 preserve .5rad/s joint slew and limits.
Reject nonfinite data, >25mm root mismatch, >.08rad attitude mismatch. Partial
scale is not exact world tracking. Keep separate nominal previous joint for
support planner; final composed joint still receives all-joint slew/limit checks.
This addresses the world-position consequence of stance sag, not a claim that
stance tracking itself is fixed. Default controller remains unchanged.

## Tests

RED3 missing-module failures; GREEN3 all-four-leg FK/stance preservation,
invalid/excessive pose rejection, joint slew. Full17-file focused suite125passed
5.12s. No full crossing acceptance inferred from these tests.

## Physics

Same8flat seed2 GPU7,100PREPARE/100UNLOAD/200LIFT budget. Prior zero-target COM
probe plus --unload_world_pose. Raw /tmp/m1_unload_world_pose_20261007.log;native0.
Result unload_timeout,100UNLOAD,0LIFT. Final selectedforces by row:
2.04,.89,5.59,4.06,2.75,0,5.80,4.10N. Six rows satisfy measured gate with final
streak20,25,0,9,11,37,0,7; rows2/6 remain above5N. All final worldscales .5.
Compared with prior9..19N this improves actual unloading, but not8/8 or crossing.
No training. Exactown1254648 placeholder stopped;1310281 restored verifiedalive.
No unrelated process/display/driver mutation or push.

## Next

Child selected-frame-slew: identify why final IK correction remains .5 and why
rows2/6 lag before changing any bounds. Check candidate per-joint slew vs limits,
then physical8/8 unloading and consistent world-frame LIFT handoff. Existing
LIFT does not yet own this correction; no assumption that its transition is safe.
Keep5N/30N/pose/deadline guards. Recovery, obstacles, landing, bypass, policy-only
video/metrics remain open; no long training until physical acceptance.
