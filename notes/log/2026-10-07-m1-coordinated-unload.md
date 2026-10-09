# Coordinated COM and unloading reference

Parent:[T306 coordinated-unload-com](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:40ab2fe; Candidate Ref:commit containing this log.
Key files:m1_load_transfer.py,test_m1_load_transfer.py,probe_m1_contact_prepare.py.

## Change versus baseline

Optional support_floor30..40N controls barycentric PREPARE margin; default30
unchanged. New --unload_com selects35N target reserve (allocation acceptance still
30N). Root transfer runs concurrently with unload, retains original phase-entry
height/attitude/8cm bound/.04m/s and fixed nonselected anchors. Selected reference
only advances after load reserve is satisfied; combined IK/joint slew checked.
One REDunexpectedkeyword regression then GREEN; focused16files117pass5.10s.

## Physical evidence

Same flat8seed2 GPU7,100PREPARE+100UNLOAD, --prepare_load_floor --phase_effort
--unload_steps100 --unload_feedback --unload_com --lift_steps200 (CLI spaced),
speed.04,bound.08. Raw:/tmp/m1_unload_com_20261007.log,native0.
PREPAREready8/8. All100UNLOADsteps execute, no allocation/contact/pose abort;
stopped=unload_timeout,0LIFT. Final selectedcontact11.92..19.29N vsprior18..31N
atstep68abort. Reference2.94..5.77mm, geometricmargin29.51..33.03mm. This removes
the observed early allocation failure but does not meet<=5N unloading or crossing.

## Next

New child unloading-convergence: distinguish target/acceptance in force feedback.
Current velocity proportional to(force-5N) approaches same5N gate asymptotically,
and slows before unloading. Evaluate zero-force target with unchanged5N measured
acceptance and.01m/s cap/2cm bound; do not lower support or clearance criteria.
Use force/time traces to set finite unload progress, not indefinite waiting.
Then actual lift/crossing/landing/recovery/bypass/policy gates. No long training.
Own1125373 placeholder restored1161123, verified alive; no unrelated processes
operated on. No display/driver/reset changes or upload.
