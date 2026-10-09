# Vertical-only selected frame comparison

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),vertical-only-frame.
Baseline Ref:ce1f1bb. Candidate Ref: commit containing this log.
Key files:m1_selected_world.py,test_m1_selected_world.py,probe_m1_contact_prepare.py.

## Change and tests

Opt-in vertical_only changes desired selected IK frame to nominalXY/attitude,
measuredZ. Full actual-pose and previousframe25mm/.08rad guards remain. Stance9
joints, contact thresholds, effort, slew and time budgets unchanged. Diagnostic
--unload_vertical_only requires --unload_world_pose. This mode is Z compensation,
NOT exact3D world-foot tracking. RED2missingkeyword, GREEN130focusedtests5.19s.
Tests verify frame ownership and continued XY/attitude safety rejection.

## Physical comparison

Same8flatseed2 GPU7,100PREPARE/100UNLOAD/200LIFT budget,zero target/COM/worldpose
flags plus --unload_vertical_only. Raw /tmp/m1_vertical_only_20261007.log,native0.
Full100UNLOAD without priorstep25frame-bound abort; finalscale1allrows.
Result unload_timeout,0LIFT. Finalselectedforces1.48,0,5.79,0,4.14,1.56,5.61,0N.
Finalreadinessstreak3,60,0,6,7,42,0,2:6instantready but only4sustained>=5frames.
Rows2/6 stillabove5N; rows0/7 do not yet meet temporal gate. Do not claim6/8
sustained or actual crossing. Compared with fullpose, avoids observed lateral
abort; supports hypothesis of correction ownership coupling, not universalproof.

## Next

Child finite-unload-progress: analyze late contact/height slopes and readiness
flicker, then finite-rate measured-contact approach within existing10mm/s,20mm
referencecap and2s deadline. Preserve5N/30N and5freshframe gate; no timeout or
success redefinition. Need8/8unload before consistent LIFT handoff and all full
crossing/landing/obstacle/bypass/policy gates. No longtraining.
Own1402415 placeholder stoppedexactly;1427632 restored verifiedalive. No other
process/display/driver mutation or push.
