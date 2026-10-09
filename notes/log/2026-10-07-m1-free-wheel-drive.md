# Lifted-wheel drive isolation

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), contact/traction child.
Baseline Ref:5aa7d97; Candidate Ref:containing commit.
Key files:m1_rolling_speed.py,probe_m1_contact_prepare.py,test_m1_free_wheel.py.

## Change / hypothesis

Default-off --roll_lifted_only commands only the selected already-lifted wheel
during existing bounded20step rolling window. Otherwheel targets0; normal mode
still commands only support wheels. Selection validated in planner-name order.
No contact/torque/pose guard relaxed. All other physics/control parameters stay
baseline5ms/gain5, rearreserve40/front35, fixed shoulder diagnostic8envseed2.
This is free-DOF versus loaded-contact isolation, not a proposed crossing mode.

## Tests and physical verification

RED9missinghelper; GREEN33focused. Full focused suite107passed13.36s (load
transfer/reserve,movingload,COM,singlelift,settle,freewheel,timestep,substeps,
rollgain,rolling speed/reference). git diff check clean.

Same90lift/.16m/.12m/s,20ramp/.1cap,90land/.005msearch,100settle, no obstacles,
GPU7/cuda0 and substepaudit; add only --roll_lifted_only.
Raw:/tmp/m1_free_wheel_20261007.log. Session51765 terminal exit0.
stopped=null,landing_complete=true,finalstep243. All8complete.
Selected force during rolling max0N. Actual wheel targets atstep100 confirm
only selected .375164rad/s, allsupport0.

Actual selected angle over full20actions (step90to110), rows0..7:
[.07720414,.07504757,.07503386,.07544048,.07719997,.07504746,.07503339,.07544113].
Reference integral7.2mm/.095963m ~= .07503rad. Free wheel drive thus produces
expected-magnitude rotation for every selected leg. Env3 native substeps agree
with its .07544048rad end-to-end angle. Unlike grounded wheel trial, no effective
forward translation is requested here; it is deliberately not crossing evidence.

## Decision

The same action/actuator chain can rotate allfourfree wheels. This weakens a
general drive failure explanation and prioritizes loaded contact/constraint
behavior. It does not uniquely prove convex faceting or absolve all loaded
dynamics/drive effects. Next isolate contact representation and loaded response
while preserving mass/materials and conservative original envelope; avoid
another speed/gain-only test or unsupported whole-body rewrite.
Source-geometry, actual obstacle5cmclearance/far-side landing/bypass/video and
policy acceptance remain open. No training started.

Only exact own placeholder2723800 stopped;2786123 verified restored afterwards.
No driver/display/other-GPU or dirty original checkout changes.
