# Guarded standing feedforward experiment

Parent:[T306 whole-body-load-model](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:9823681; Candidate Ref:commit containing this log.
Key files:m1_effort_guard.py,test_m1_effort_guard.py,probe_m1_contact_prepare.py.

## Difference from previous version

Pure guard adds named12-leg mask,20Nm/s feedforward slew, finite and requested
torque checks, combined estimated PD+feedforward limit check, and immediate zero
output for disabled/reset/invalid rows. It rejects, not clips, excessive effort.
Zero output is abort semantics, not recovery proof. Five RED tests failed on
missing module; focused14-file suite107 passed in5.35s after implementation.

Opt-in --standing_effort_steps100 (flag/value separated) is limited0..100 and
cannot combine with lift. Four-contact allocation refreshed each step; all wheel
forces>10N, tilt<=.15rad/rate<=.20 and no nonwheel contact>10N required. Joint mask
resolved by names in actual articulation order. Fresh PD estimate uses installed
stiffness/damping and current position/velocity target/errors. Effort target is
explicitly cleared and written on normal exit and finally on errors; reset causes
abort/clear without a subsequent simulation step. Not integrated into training.

## Actual GPU7 smoke

Flat8 seed2,32 warmup then100 standing steps, --num_steps1 --headless --device
cuda:0 --standing_effort_steps100 (all CLI values separated by spaces).
Raw:/tmp/m1_standing_effort_20261007.log; native0.100samples, stopped=null,
cleared=true. All support contacts across trace>=78.9976N, maxaxis tilt.009302rad.
Row0 rootZ rises.5495469 -> .5505780m. No lift was attempted. This validates
bounded standing execution only, not improved lifting or crossing.

## Metric issue / next

The diagnostic tracking_error currently aggregates all16 joints, including
velocity-controlled wheel positions. Its~.30rad value cannot establish leg
tracking quality. Next child:leg-only-standing-comparison, add twelve-leg error
telemetry and compare matching no-feedforward baseline before claiming error
reduction. Then PREPARE-to-lift feedforward integration and measured lift gates.
Do not confuse implicit PD estimate with measured torque; substep hard total
effort monitoring and full recovery remain unverified.
Own906048 placeholder restored933857 alive; ldc3227360 alive, untouched.
No display/driver changes, long training, or upload.
