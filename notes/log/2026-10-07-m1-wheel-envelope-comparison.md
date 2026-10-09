# Wheel collision envelope restores diagnostic rolling

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md),effective-rolling-progress.
Baseline Ref:4c20e29. Candidate Ref:containing commit.
Key files:m1_wheel_collision_probe.py,probe_m1_contact_prepare.py,test_m1_wheel_collision_probe.py.

## Scope

Opt-in `--diagnostic_wheel_prism`, standing-roll only. Original source USD and
production spawn remain unchanged. Replace collision mesh points/topology in
the in-memory diagnostic stage, retaining material bindings/body physics.
Use uniform32-sided Y-axis cylinder envelope, radius.095963m and Ybounds
[-.01594940573,.03054940514].64inputvertices/34faces. This conserves maximum
radius and total width, NOT the detailed tire shoulder/tread cross-section.
Do not call it a validated production tire or silently adopt it for training.
Mass/inertia/friction/gains are not intentionally changed; follow-up should
read back physical invariants before production use.

## Verification

TDD RED:missing module,1failure. GREEN:23focusedtests pass1.57s.
GPU7 cleanflat8, feedforward0,damping5,velocityiterations0; same180-step control
with only `--diagnostic_wheel_prism` added and M1_OBSTACLE_STAGE=none.
Raw:/tmp/m1_prism_roll_20261007.log. Exit0;180samples,stopped=null.
Cooked comparison hull62vertices/33polygons (baseline34vertices/62polygons).
Actual world-X progress sample160 minus60,mm:
[93.5643,86.8117,94.6552,93.5510,91.5132,89.7166,94.7210,93.4086].
Baseline identical drive on source hull:-0.336..-0.349mm.
Final absolute roll<.00187rad,pitch<.00288rad; no standing guard rejection.
This provides causal evidence collision representation contributes strongly
to stalled rolling, not only a command/teacher/gain issue.

## Acceptance boundary and next

Still NOT obstacle traversal, policy learning, or validated real tire contact.
Audit actual tire cross-section and preserved mass/inertia/friction; develop
representative smoother collision model with geometry-error bounds. Then redo
flat rolling/lift/landing and actual obstacle single-leg sequence/video before
training. Preserve wheel radius and final clearance/stability/collision gates.
Exact own placeholder2174114 stopped,2193711 restored and verified. No other
GPU/user jobs or display/driver configuration touched.
