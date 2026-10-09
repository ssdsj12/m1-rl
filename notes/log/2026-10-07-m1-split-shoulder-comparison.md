# Controlled split-shoulder collision comparison

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), rolling-support-control.
Baseline Ref:c371ac7. Candidate Ref:containing commit.
Key files:m1_wheel_collision_probe.py, probe_m1_contact_prepare.py,
test_m1_wheel_collision_probe.py.

## Diagnostic implementation

Opt-in shoulder_split profile replaces one20-segment three-ring hull with two
32-segment frusta sharing the center ring. Same axial radii/width, no source USD
write. Additional collider uses an internal reference to retain authored physics
and material bindings. Input per hull64vertices/34faces/max32vertices per face.
Runtime FBL cooked hulls both62vertices/33polygons; cooker modifies input shape.
Inspected first-half central ring has31vertices,maxangular gap16.875degrees,
so not a perfect32-gon. Original conservative wheel envelope remains acceptance
boundary; not production promotion.

Official reference: [PhysX GPU rigid bodies](https://nvidia-omniverse.github.io/PhysX/physx/5.4.0/docs/GPURigidBodies.html)
documents64vertex/polygon and32vertex-per-face GPU contact limits.

## Invalid initial comparison and correction

/tmp/m1_split_shoulder_20261007.log exits0, physical rejection104. This run is NOT
a causal shape comparison: shape count17->21 changes material random-number
consumption, subsequently changing base mass/inertia. Never report preservation
based only on unchanged authored asset values.
Added diagnostic_fixed_physics: disable additive mass randomization, fixed
static/dynamic friction.8, restitution0, deterministic joint reset. Production
training cfg and default diagnostic behavior remain unchanged.
Tests RED missing wheel_parts then missing fix_diagnostic_physics, final GREEN
46passed11.84s including lift/settle/rolling/contact wiring. diff-check clean.

## Matched physical comparison

Same full8env seed2 flat none-stage low-speed cycle as
[previous log](2026-10-07-m1-low-speed-support.md); add diagnostic_fixed_physics
to BOTH profiles. GPU7 only. Raw:
- /tmp/m1_fixed_shoulder_20261007.log: exit0, rolling_support_rejected105,
  all8progress negative(-.605..-.883mm), no landing.
- /tmp/m1_fixed_shoulder_split_20261007.log: exit0, same rejection107,
  row3 FBL29.725N<30N; all8progress negative(-.058..-.877mm), no landing.
Runtime entire masses and inertias arrays match exactly. Both material arrays
contain only[.8000000119,.8000000119,0]; shape counts necessarily differ.

## Conclusion / follow-up

Finer split hull alone does not restore traversal and is not a production fix.
Do not continue blind geometry/speed sweeps. Next implement bounded moving-load
compensation with explicit reference ownership and predictive admission, using
the controlled-physics baseline to isolate response. Preserve30Nfloor,8cm bound,
4saction and original-envelope crossing oracle. Actual obstacle/video/teacher
training acceptance still open; no training started.
Placeholder2363319->2392320(initial)->2420282(paired tests), final exact own
process verified. No display/driver/other GPU or original-checkout changes.
