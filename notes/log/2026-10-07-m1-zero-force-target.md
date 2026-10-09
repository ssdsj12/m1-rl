# Zero-force unload target comparison

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), unloading-convergence.
Baseline Ref: f71fc1c. Candidate Ref: commit containing this log.
Key files: m1_unload_reference.py, its tests, probe_m1_contact_prepare.py.

## Change and verification

Optional target_force in [0,5] separates tracking target from measured <=5N
acceptance. Default5 preserved; probe --unload_target_force 0 opts in. Rate .01m/s,
height .02m, effort-settle gating and other support/pose constraints unchanged.
RED: four expected unexpected-keyword failures; GREEN: 121 focused tests passed
in4.93s (same16-file suite as prior log plus four target tests).

## Physical comparison

Same GPU7 flat8 seed2,100PREPARE/100UNLOAD/200LIFT budget, transfer .04m/s/.08m,
--prepare_load_floor --phase_effort --unload_feedback --unload_com,
--unload_steps 100 --unload_target_force 0 --lift_steps 200.
Raw /tmp/m1_unload_zero_target_20261007.log; native exit0.
Result unload_timeout,100 unload samples,0 lift samples. Final selected forces
9.36,10.01,11.41,13.61,19.09,9.87,12.92,13.65N. Last reference3.70..6.44mm;
effort gap<=.049Nm; all ready false. Prior target5 gave11.92..19.29N.
Target distinction improves some rows but does NOT resolve unloading or prove
crossing. Do not promote this experiment into training.
Own1161123 placeholder stopped exactly; restored1224540 verified alive.
No other process/display/driver changes. No long training or push.

## Next / architecture checkpoint

Unloading-convergence remains open. Before more parameter trials, inspect coupled
COM/selected-height response: commanded vs actual wheel height, joint tracking,
force slope, and time spent blocked by load reserve. Zero target alone is not
the root solution. Preserve measured gates; no indefinite wait, no PD cancellation
based on normal-only contact proxy. Full physical crossing remains unverified.
