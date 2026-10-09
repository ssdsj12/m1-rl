# M1 diagnostic speed and total-effort continuity

Baseline359c5d3, parent [WBC design](../specs/2026-10-08-m1-dynamic-wbc-design.md).

1. TDD explicit named diagnostic actual-speed caps: legs.5rad/s (conservative
   experimental cap, NOT a manufacturer rating), wheels existing M1 wheelcap,
   intersect native. Preserve reference generator limits independently.
2. Total effort bounds intersect physical limits with previous explicit total
   command plus/minus20Nm/s*dt. Require previous tick/same episode/explicit
   ownership; no implicit estimate, stale data, missing history or zero default.
   This extends existing conservative20Nm/s feedforward slew to total command
   in diagnostic WBC, not an alteration of training actuator configuration.
3. Native read-only force-source inventory: direct actuation, projected active
   joint force, approximate cached torque, drive gains. Do not assume any getter
   equals total drive command without verification. Keep no-actuation boundary.
4. Retest state-bound shadow with explicit speed cap. Preserve raw-native limit
   evidence and original negative control. Record missing initialization/handoff
   prerequisites rather than fabricate previous command.
