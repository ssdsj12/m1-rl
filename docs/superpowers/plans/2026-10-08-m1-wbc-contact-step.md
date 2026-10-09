# M1 live velocity-level contact prediction

Parent [WBC design](../specs/2026-10-08-m1-dynamic-wbc-design.md), baseline0bce18a.
This child replaces zero-velocity assumptions in a read-only shadow calculation;
it does not certify impact handling or authorize actuator execution.

1. Test first explicit semiimplicit one-step model: v_next=v+dt*(J*qdd+b).
   Attached tangent target0; normal targetmax(0,-gap/dt). Released normal
   lower bound-gap/dt, force0. Thus predicted gap+dt*normal_next>=0.
   Preserve measured gap, velocity and kinematic bias; no state reset/clipping.
2. Actual native full h=gravity+C; actual material-point bias from named rigid
   tree; include all native contact entries. Fixed-material point local model,
   not a smooth-wheel migration or full collision/impact solver.
3. Use existing diagnostic acceleration/effort/friction/group bounds unchanged,
   enumerate geometric candidates, report all feasibility failures and predicted
   velocity/gap. No online mode selection from this alone.
4. Run full tests and bounded native shadow. Physical finite-step error and
   actuator handoff remain subsequent gates; no training yet.
