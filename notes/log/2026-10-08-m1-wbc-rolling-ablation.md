# 2026-10-08 M1 WBC rolling-contact ablation

This is a diagnostic checkpoint, not a crossing or controller pass. The user's
priority is strict obstacle crossing first; rapid balance recovery is evaluated
only after crossing. No training was started.

## Same-state evidence

- Focused WBC suite before the physical run: 157 passed.
- GPU7 flat-support probe still failed its safety gate at tick 48. Forward speed
  reached 0.08091 m/s; wheel loads remained 94.1--119.9 N and roll/pitch remained
  near zero. The predicted forward base acceleration was +1.16 m/s^2 while the
  target was -0.158 m/s^2. This is not crossing evidence.
- Same-state counterfactual with the welded 3-D contact-point equalities: even
  unrestricted native torque capacity predicted base linear qdd
  `[+1.417, +2.000, -1.483]` m/s^2 against target
  `[-0.044, -0.0005, +0.060]` m/s^2.
- Normal-only ablation at the same state and native effort capacity predicted
  base linear qdd `[-0.044, -0.0005, -0.975]` m/s^2. It fixes forward qdd but
  sacrifices vertical acceleration; therefore it is diagnostic only and is
  explicitly not accepted as a rolling-wheel controller.
- At the applied 20 Nm/s slew, the welded model predicted +1.394 m/s^2 forward
  acceleration; even the 200 Nm/s counterfactual predicted +1.292 m/s^2. The
  applied probe failed at tick 48. Raising slew alone is not justified.
- A one-run normal-only physical ablation also failed the speed gate at tick 50
  (0.08018 m/s), despite safe observed tilt and support loads. The probe was
  reverted to execute the original welded baseline; normal-only remains a
  same-state counterfactual only.

## Interpretation and next gate

The full 3-D contact model is over-constraining a rolling contact, while a
normal-only model omits no-slip rolling kinematics and is physically incomplete.
Implement the contact-patch migration derivative for wheel tangent constraints,
verify it against an analytic pure-roll case and finite differences, then use a
fresh single-env run with independent load/tilt/speed gates. Add a single-wheel
obstacle trajectory only after the rolling model can support a controlled lift;
do not restart PPO before strict physical crossing succeeds.

GPU7 placeholder was restored via the existing lifecycle wrapper and verified
on the physical GPU7 UUID; other GPUs/processes were left untouched.
