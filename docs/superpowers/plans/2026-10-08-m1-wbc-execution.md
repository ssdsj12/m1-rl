# M1 actual WBC execution chain in suspended oracle

Baseline60906c0, parent [WBC design](../specs/2026-10-08-m1-dynamic-wbc-design.md).
No hot-switch, gravity change, source USD edit or zero-history fabrication.

1. Add opt-in QP mode to existing fresh zero-PD suspended-M1 oracle.
   Initial explicitly written zero is read back with native K/D0 before history
   initialization. Same episode/prior tick checked by effort_step_bounds.
2. QP free-body full dynamics, no contacts, authored state+diagnostic speed limits,
   physical effort limits and20Nm/s total effort rate. Soft joint acceleration
   targets0,+.1,-.1rad/s². Free-flight root bounds±20m/s² and±10rad/s² are local
   test bounds, not ground support/reference limits; no claim of ground control.
3. Execute exact QP effort through existing sole-owner write/readback path.
   Eight rows x3ticks, no resets during sequence, test requested/applied equality,
   rate and free-dynamics residual. Preserve existing baseline mode and .02
   residual threshold. No contact/stance/crossing acceptance from this test.
4. After execution-chain verification, physical grounded initialization remains
   a separate gate with existing support/reference limits and no stale history.
