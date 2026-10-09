# M1 retimed flat lift and landing

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),
trajectory-budget-feasibility. Baseline Ref:9b7552b. Candidate Ref:commit containing
this log. Key files:m1_single_lift.py, probe_m1_contact_prepare.py and its lift tests.

## Cause and change

Dense nominal IK path integration (2001 height samples, .5 rad/s joint cap)
gives vertical roundtrip lower bounds 3.274/3.454/3.806 s at15/16/18cm.
Including old .08 m/s cap gives3.790/4.040/4.540s. Old discrete scale choices
lose further progress. Add explicit vertical_speed .12 opt-in with1/32-scale
trials; preserve default .08 and old scale choices, all reach/slew/pose/contact
guards, and below-ground1cm/s/5mm search bounds. No raised joint limit.
Probe exposes logged --vertical_speed and --lift_height; defaults preserved.

## Tests

RED:6 new tests fail on missing vertical_speed. GREEN:145 focused tests passed;
after parametrizing ground-search bounds for both speeds,23 lift tests pass.
Nominal16cm up/down test enforces <=180steps and every joint delta<=.010001rad.
These synthetic tests are not a physical crossing certificate.

## Physical smoke

GPU7 only,8flat environments,seed2,all4legs twice. Same prior prepared effort /
unload / vertical-frame control.90LIFT+110LAND+100SETTLE budgets; explicit
--vertical_speed .12 --lift_height .16 --land_search_depth .005.
Raw:/tmp/m1_retimed_cycle_20261007.log. Native exit0,stoppednull,
landing_complete true,finalstep234,all landing streaks5. SETTLE .68s.
Peak measured wheel-center rise by row in cm:
15.329,15.752,15.464,15.628,15.314,15.772,15.437,15.632.
Samples above15cm:8,11,10,12,8,11,10,12 (only .16.. .24s).
Final selected normal forces63.21,59.70,58.18,67.34,63.81,53.74,56.39,66.49N.
No obstacle exists in this probe; these rises are NOT obstacle-top clearance.

## Remaining

Now physical15cm-rise plusstablelanding is demonstrated, but the short high
window does not prove horizontal traverse. Next obstacle-aware TRAVERSE hold
and rolling reference ownership must be integrated with the4s action budget,
real near/far obstacle boundaries, wheel envelope and contact/collision oracle.
Do not start longtraining or call this a crossing policy.3seeds/video/recovery/
large-obstacle avoidance still pending. Own placeholder restored PID1745580;
no display/driver/unrelated job changed.
