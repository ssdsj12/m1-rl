# M1 contact-driven crossing design evidence

Stage: AME teacher/support control and event metrics.
Related nodes: [T306.contact-transfer / T306.event-metrics](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref: 5f94f14 plus existing uncommitted changes; no clean-code baseline claim.
Candidate Ref: design-only commit containing this log and
[specification](../../docs/superpowers/specs/2026-10-07-m1-contact-crossing-design.md).
Last Feature/Verified Commit: unchanged; this commit does not verify controller behavior.

## Existing evidence inspected

- Batch and viewer root-foot coordinate transforms were corrected; targeted CPU
  tests passed, but physical crossing did not. Broader tests still have unrelated
  entrypoint/diagnostic expectations failing; no full-green claim.
- Seed2/128-step measured-hold diagnostic: knee hold drift 1.10 to1.83rad;
  minimum body z .265m,19 non-support contact steps,0 resets.
- Matched hold-off ablation: minimum z .498m,0 non-support contact steps,
  maximum tilt .788rad,2 resets. Failure, not a production recommendation.
- Hold-off64-step COM capture: mass-weighted COM available with no read errors;
  first post-step projection margin -.0204m, later -.2344m. Other wheel contact
  force can become zero. Projected wheel-center triangle is diagnostic only.
- Runtime logs retained under /tmp with stems m1_support_drift_seed2_20261007,
  m1_fixed_hold_seed2_20261007, m1_balance_com_seed2_20261007 (all .log).
- CPU replay of stationary large-obstacle timeout produces avoidance rate1.0;
  current wrapper supplies presence-and-no-collision, not actual bypass evidence.
- Existing accumulator DOES revoke earlier/later collisions and terminal falls;
  missing strict event geometry/leg association remains a separate problem.

## This update

User confirmed proposed design. Wrote scoped opt-in controller architecture,
state transition criteria, failure paths, honest event denominators, physical
gates and GPU7 placeholder lifecycle. Self-review checked no success inference
from stopping, no lateral-wheel assumption, no ground-truth policy leakage,
no reset-spanning displacement claim and no unrelated dirty changes committed.
Implementation and physical validation remain outstanding. No new GPU job or
training was started in this documentation update.

Key files to change after spec review: ame_env_wrapper.py, m1_mpc_teacher.py,
m1_crossing_metrics.py and scoped new coordinator/observer helpers under
Go2Pvcnn/ame_baseline, with tests and probe/runner integration.
