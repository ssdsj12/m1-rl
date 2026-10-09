# M1 kinematic acceleration bias implementation

Parent: [approved design](../specs/2026-10-08-m1-dynamic-wbc-design.md).
Execute inline in the existing isolated worktree using test-driven development.

1. RED: independent central-difference COM oracle for a two-joint 3D tree,
   rotating floating root with offset COM, named permutations, zero velocity,
   malformed frames/tree and inconsistent measured angular velocities.
2. Implement a read-only NumPy recursion for acceleration with generalized
   acceleration zero (root COM world linear and root world angular coordinates).
   Return actor-origin, COM and angular bias in requested body-name order.
3. GREEN: all WBC CPU regressions; opt-in existing bounded suspended probe
   compares measured native body acceleration to J*qdd+bias for8rows x3ticks.
   Fix native tolerance <=.02 m/s^2 (linear), <=.02 rad/s^2 (angular) before run.
   No changes to the existing tiny diagnostic torque commands. GPU7 only,
   exact own placeholder stop/restore with EXIT trap; no support/lift experiment.
4. Record evidence and remaining native verification. A fixed material point's
   acceleration is NOT a zero-acceleration rolling constraint. Contact migration,
   effective friction and physical stance remain separate mandatory gates.

Fixed CPU tolerance: central-difference COM error <=2e-6 m/s^2 at h=1e-4 s;
analytic zero/root centripetal cases <=1e-12. Angular velocity consistency
<=1e-5 rad/s. This is not a physical crossing acceptance test.
