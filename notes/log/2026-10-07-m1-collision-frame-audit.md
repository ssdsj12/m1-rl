# Read-only wheel collision-frame audit

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), effective-rolling-progress.
Baseline / Candidate Ref: 307ac8f; no controller or simulator changes.
Procedure: bundled pxr CPU reader, TraverseInstanceProxies, evaluate collider
world matrix times rigid-body inverse matrix; inspect authored joint attributes.
Script: `/tmp/m1_inspect_collision_20261007.py` (local inspect_m1_collision.py).

## Result

FBL collider-to-body transform is identity. Body-local bounds:
X[-0.09590133,+0.09590133], Y[-0.01594941,+0.03054941],
Z[-0.09595813,+0.09595813]. Thin cylinder axis agrees with joint Y axis.
Joint local rotations both identity, child anchor0; parent anchor(0,.0592,-.28).
No extra collision-frame rotation/translation found in this inspected wheel.
Collider approximation convexHull, collisionEnabled true.
Source angular drive stiffness52.8753,damping.02115 is NOT runtime configuration:
previous runtime telemetry measured stiffness0,damping5. Source authored limits
are +/-359.989 degrees but runtime PhysX limits were effectively unbounded.
Do not diagnose a live position spring or finite-angle lock from source alone.

## Conclusion

This inspected collision-frame mismatch hypothesis is unsupported. Actual cooked
hull/contact manifold and solver/substep response remain unverified; next inspect
those to explain stationary cumulative angle with positive sampled velocity.
No GPU allocation, training, driver/display/config changes. Existing placeholder
2076869 was observed and left running. No crossing success claim.
