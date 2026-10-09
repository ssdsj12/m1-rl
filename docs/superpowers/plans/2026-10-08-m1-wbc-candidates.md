# M1 native at-rest rolling mode feasibility

Approved [WBC design](../specs/2026-10-08-m1-dynamic-wbc-design.md), inline TDD.

1. Enumerate nonempty subsets of distinct measured contact locations per wheel,
   preserving every force slot at coincident locations. Cartesian product capped
   at32; reject excessive budget/missing support rather than truncate silently.
2. CPU tests for duplicate slots, exhaustive choices, bounds and invalidgeometry.
3. Add read-only native --wbc_snapshot counterfactual: v=0 at actual pose/contact,
   M/g/native effortlimits/livefriction. For each candidate, attached material
   pointa=0; released normalacc>=0 and force0. Groupmin35N unchanged.
   This is explicitly at rest, not valid for arbitrary slipping/impact states.
4. QP tiers: rootlateral/angular stability; forward.05m/s² plus wheelworldY
   angularaccel .05/M1radius; minimum leg acceleration. Diagnostic accel bounds
   translation±.05, rootangular±.2, joints±1rad/s², not productionlimits.
5. Bounded GPU7 capture: compare allattached and release candidates, report
   achieved task errors and constraint residuals, do not apply any torque.
   Restore placeholder. Negative results retained; no training/crossing claim.
