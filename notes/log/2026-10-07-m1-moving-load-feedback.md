# Moving load reserve wiring and physical rejection

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), rolling-support-control.
Baseline Ref:2e3ba89. Candidate Ref:containing commit.
Key files:m1_load_transfer.py,m1_moving_load.py,probe_m1_contact_prepare.py.

## Contract fix / diagnostic integration

Measured wheel_force branch ignored support_floor and hardcoded30N. RED2 tests
show requested35N does not act at33N and wrongly accepts total102N<105N.
Use requested floor for deficit/supply/readiness and total-load sufficiency;
default30N unchanged. GREEN31tests.

Add opt-in roll_load_feedback: propose35N reserve through bounded COM translation
in transported frame; preserve configured root speed/bound, final actual joint
slew/world-foot correction and30N measured hard guard. Only commit COM offset
after env.step; hold offset during LAND/SETTLE for reference continuity.
COM motion must not count as rolling transport: use measured three-support-wheel
centroid, excluding lifted wheel, instead of root position in this opt-in mode.
No training/controller default enablement. A static load model is only a proposal.
TDD missing helper/wiring/center RED; final73passed12.93s includes transfer,
moving frame, lift, settle and rolling speed. diff check clean.

## Physical results

Same fixed-physics shoulder8seed2 flat none-stage cycle and .02rolling cap as
[controlled baseline](2026-10-07-m1-split-shoulder-comparison.md); only feedback
enabled. Raw:/tmp/m1_moving_load_20261007.log initial root-transport version:
exit0, rejection97 versus baseline105. Not accepted due mixed COM/transport.
After support-centroid correction:/tmp/m1_moving_support_frame_20261007.log,
exit0, still rolling_support_rejected97, landing_complete=false.
All load proposals valid, so no bound/IK excuse. Row3 weak FBL load:
step94=35.025N,95=34.687N,96=32.974N,97=28.768N.
Root x command95=.0134954,96=.0141537,97=.0148160m; actual root x
.0129050,+.0128486,+.0128184m. Proposed correction97 x/y=1.520/1.128mm,
not all executed because rejected pre-action. Physical unload accelerates after
command shift begins. This is evidence against using instantaneous quasi-static
load redistribution directly during rolling, not proof of full dynamics cause.

## Next / constraints

Keep feedback default-off, no long training. Need dynamically bounded COM
acceleration and support-wrench coordination/predictive admission, not larger
gain, lower30Nfloor or a declaration that static proposal validity is stability.
Actual obstacle crossing, original wheel fidelity, video and policy-only
acceptance remain open. Preserve8cm displacement and4s action budget.
Placeholder2420282->2456625->2471170 verified. First probe had already exited
when stop check ran; no PID killed then. No unrelated GPU/display/driver changes.
