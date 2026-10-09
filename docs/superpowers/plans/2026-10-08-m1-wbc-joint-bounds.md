# M1 authored joint-state bounds vs diagnostic acceleration box

Baseline8751554; parent [WBC design](../specs/2026-10-08-m1-dynamic-wbc-design.md).
The prior joint acceleration bound1rad/s² was explicitly a diagnostic box,
not an authored M1 limit. Do not increment it until a solve passes.

1. TDD derive acceleration interval from measured q/v, authored position and
   velocity limits using v_next=v+dt*a, q_next=q+dt*v_next. Intersect native
   and configured velocity limits; invalid state rejects, never clamps.
2. Preserve original diagnostic solve as negative control. In an additional
   shadow, replace ONLY joint diagnostic acceleration slots by derived bounds.
   Root diagnostic boxes, torque/friction/support/task constraints unchanged.
   Reference speed/acceleration/slew limits remain unchanged; this helper is
   actual joint-state feasibility, not a reference generator.
3. Record predicted joint position/velocity checks and exact native limits.
   Finite-step state check is not stopping-distance viability or torque-slew
   certification. No actuator use until sole-owner handoff/slew and physical
   step validity are tested. No training.
