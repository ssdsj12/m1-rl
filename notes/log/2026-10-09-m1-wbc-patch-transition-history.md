# WBC patch transition: approaching geometry is filtered before impact

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), child
execution-physical/contact-transition-consistency. Baseline/candidate c90bb1d;
stage read-only instrumentation of existing opt-in base-priority native probe.

## Native checks and immutable inputs

GPU0,1env,seed7,dt.001,settle2000/stable100/hold500/base_priority. The wrapper
only reads points, forces, gaps, native Jacobians and velocities; returns original
solver outputs unchanged. Original hard bounds and stopping gates retained.

| Capture | Log | SHA256 | Terminal result |
| --- | --- | --- | --- |
| patch history from740 | `/tmp/m1_wbc_patch_history_20261009_trQAj2.log` | `6dca09ad712cc5e51af482e40257a198d10a808126f9e370fa58c6a65b6d0dc6` | feedback465/native760 contact inconsistency |
| raw near contacts/J/solver inputs from700 | `/tmp/m1_wbc_near_contact_20261009_rLpJn4.log` | `56122e93c593a74b6701f91245a7884610d60267610d01ec7078d2d7dc0e8f16` | feedback472/native767 contact inconsistency |

Both ended, no live probe or training. GPU7 placeholder1768831 untouched.
These baseline captures preceded the released-material bias correction below.

## Measured transition

Affected wheel is `FAR_FOOT_LINK`, owner1. Native760 shows old point at
x.333758m with normal velocity+.008038m/s and84.26N; new point atx.278714m
with normal velocity-.005812m/s and~67.06N combined duplicate reports.
Both have nonnegative gaps (~.194um and9.798um). All-attached targets demand
opposite normal corrections -8.0397/+5.8103m/s2. This is an impact/patch
handoff, not two stationary support points.

Before this, new point already existed with zero force and gaps64.79/46.65/28.14um
at757/758/759. In the second capture, gaps59.23/41.78/24.12um at764/765/766,
then6.646um and nonzero force at767. Source `contacts()` discards strength<=.001N,
so this approaching geometry is absent from active WBC before impact.
Do not infer pre-impact eligibility from load alone.

PhysX documents contact generation before penetration and distinguishes
contact offsets from rest offsets: [official collision documentation](https://nvidia-omniverse.github.io/PhysX/physx/5.1.2/docs/AdvancedCollisionDetection.html).
The specific missing-point/velocity conclusion above is from measured data,
not an assumption derived solely from documentation.

## Proposed immediate release rejected offline

`/tmp/m1_audit_wbc_release_candidate_20261009.py LOG SNAPSHOT` preserves all5
force slots/Jacobians/moment arms, zeroes ONLY candidate released-point force,
retains material-point nonpenetration, friction/group minima and original slew.
Releasing either old or new point has feasible contact+acceleration equations,
but full original WBC is infeasible. Native-capacity-only counterfactual solves,
requiring a chosen delta~7.63Nm(old release) or~7.07Nm(new release); these are
NOT minimum-change certificates and were NEVER applied. No rate increase.
Therefore "drop old point now" is not an accepted fix; need anticipate the
approaching point and/or verified impact-aware transition before saturation.

## Next action

Retain raw zero-force near-contact geometry separately from load-bearing modes,
then evaluate pre-impact deceleration/transition feasibility under original
limits. The second log preserves per-frame full wheel COM Jacobians and exact
solver inputs; full analytic COM/angular kinematic bias should be captured for
any proposed new-point predictor rather than silently assumed zero.
Do not replace the current model with arbitrary point deletion or claim a
fixed smooth-circle model applies to discrete patch transitions.
Single-leg actual lift/10cm crossing/3--5cm bottom clearance/far-side landing,
recovery and policy-only avoidance remain unverified; long training remains off.
