# Continuous wheel holding reaches UNLOAD; contact persistence blocks LIFT

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), wheel handoff child.
Baseline Ref:5cb08a8. Candidate Ref:containing commit.
Key files:m1_rolling_speed.py,probe_m1_contact_prepare.py,test_m1_wheel_hold.py.

## Change and verification

Opt-in phase_wheel_hold uses one previous-command state across PREPARE,
UNLOAD,LIFT,ROLL,LAND,SETTLE. The selected wheel brakes toward0 during
UNLOAD/LIFT/ROLL/LAND; other wheels retain bounded fixed-anchor feedback.
ROLL releases position feedback into forward feedforward; LAND resumes holding
against the existing transported anchor, not original pre-roll world position.
SETTLE can re-engage all4. One0.2m/s2 limiter across boundaries, unchanged
wheel effort limits, stiffness0/feedforward0 requirement. Other wheel diagnostic
torque/gain/lifted-only variants rejected. Default remains off.

Two RED missing-function tests then20GREEN1.47s, plus syntax check. Tests cover
selected braking, support retention, roll release/land braking and invalidphase.
Physical test is the prior8envseed2 SDF128/rest1mm/contact2mm fullcycle command
with phase_wheel_hold instead of prepare_wheel_hold_only; no other physics change.
Raw:/tmp/m1_phase_hold_20261007.log; session65427 terminalexit0.

## Evidence

100PREPARE and100UNLOAD executed, noLIFT/ROLL/LAND. Stopped=unload_timeout.
Prior UNLOAD0 world-frame rejection no longer occurs. Maximum command increment
over200frames .004000000656m/s, consistent with0.2m/s2 at20ms precision.
Final UNLOAD world candidate reports safe/reachable/limits/slew true all8.
Selected-wheel height reference atstep99 only2.056..3.900mm.
Selected-wheel force repeatedly rises above5N despite low reference height:
e.g env0 late rejectedframes5.12..9.29N;env4 5.35..7.27N.
Final fresh force perselectedwheel=[5.1081,0,0,0,4.6153,.8430,0,4.5901]N;
freshstreak=[0,3,3,5,3,4,4,23], finalready=[false,true,true,true,true,true,true,true].
Maximum pre-finalstreak perenv=[10,5,5,7,4,6,5,22]; simultaneous batch gate fails.
Final minimum other-wheel force32.583N, effort error<=.019883Nm.
Some earlier failures withselectedforce<5N require checking other predicate
components; do not attribute every reset toselectedforce without decomposition.

## Interpretation and next

The wheel-holding fix now has physical evidence throughUNLOAD, not onlyPREPARE.
Later phase implementation is unit-tested but NOT physically reached/verified.
Selected-force persistence and coupled batch gating are next investigation,
not CUDA failure or permission to raise5N/shorten5frames. Inspect actual
wheel-ground separation, unload-height inhibition by load_ready/effort_settled,
and every predicate component. A few-mm reference may remain incontact margin;
that is a hypothesis, not proven cause. Do not count intermittent readiness as
completed lift or relatch reference to drift. Full obstacle/video/policy/avoidance
acceptance remains open; no long training.

Own placeholder3276873 stopped,3356222 restored/verified. No display/driver,
unrelated tasks, originalasset or dirtycheckout changes. Notes synchronized.
Local commit only, not uploaded. Improvement vs5cb08a8: continuous phase
command ownership physically passes entry intoUNLOAD, new failure isolated.
