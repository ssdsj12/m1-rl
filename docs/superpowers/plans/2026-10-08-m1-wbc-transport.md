# M1 moving contact acceleration transport

Parent [approved design](../specs/2026-10-08-m1-dynamic-wbc-design.md).
TDD inline in existing isolated worktree. No actuator/terrain change.

1. RED tests: pure circular rolling, fixed polygon vertex, independent velocity
   field central difference with nonzero slip/angular bias, Galilean invariance,
   malformed/missing migration, integration with existing constrained QP.
2. Implement required explicit geometry_velocity input. Material bias is
   bCOM + alphaBias cross r + omega cross (omega cross r).
   Total derivative at migrating evaluation point adds
   omega cross (geometry_velocity - material_velocity).
   Return components separately; never infer geometry_velocity by differencing
   transient PhysX patch IDs. Missing migration must not default to zero.
3. Run WBC CPU regressions; fixed finite difference tolerance1e-8 at1e-5s,
   analytic cases1e-12, QP independent residual existing1e-5.
4. Preserve distinction between formula and native shape model. Real M1 cooked
   hull support changes between faces/vertices; do not assume a smooth circle
   merely because pure-circle unit test passes. Native migration model then
   static stance/rolling remains next gate.
5. Native read-only static QP: current pose/M/g/J/points/mu/actual torque limits,
   counterfactual zero velocity and qdd; grouped wheel support>=30N. Not a moving
   dynamics test. Record infeasibility without changing limits or claiming support.
   Reuse bounded GPU7 snapshot, exact placeholder stop/restore, no actuator writes.
