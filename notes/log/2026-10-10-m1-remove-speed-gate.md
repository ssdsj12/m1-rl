# Remove speed-error promotion requirement

## Deployment verified 2026-10-10 16:38 CST

Watcher finished successfully: old7747 and watcher8491 are absent; actual
training PID8573 resumed model_500 at501 with2048envs and9499remaining updates.
New run2026-10-10_16-16-53/bb57e7d. Observed iteration591/10000 and finite loss.
Production source promotion predicate is pass_rate>=.9 and strict_ok only.
TensorBoard's verified old PID7905 was stopped and restarted on this new run.
Stage remains0; course_boundary metric.4824, no base/orientation/nonfinite
termination. Partial-window pass_rate0 is NOT a complete-window success rate.
Boundary cause remains unresolved; removing speed gate is not a boundary fix.

The pending deployment narrative below is historical and now superseded.

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md).
User explicitly requested only removing the velocity-error promotion metric.
Baseline bb57e7d; current codex/m1-contact-recovery uncommitted candidate.

The sole production predicate change removes velocity_error<.08 from
LearningCurriculumGate.reset. Telemetry and velocity-tracking reward remain.
The three completed windows, >=90% pass rate, >=70% commanded forward distance,
finite state, full episode and strict crossing/recovery criteria are unchanged.
Stationary test fixture now has zero displacement as well as zero speed.

TDD: high-speed-error forward progression regression failed on original code
(stage0 instead of1); after change, 20 curriculum/terrain/checkpoint tests pass.
New test exercises both flat and obstacle-stage advancement with error>.08.
No native simulator launched concurrently with training.

Deployment is PENDING, not a hot patch: verified one-shot watcher PID8491 waits
for model_500.pt from exact training PID7747, validates finite weights and
curriculum metadata, then stops only that process and resumes next_iter501
with optimizer/std from this same flat-first lineage, remaining9499 updates.
Launcher flock prevents duplicate jobs. Script fails closed on changed PID/cwd
identity, missing checkpoint, bad metadata or failed restart.
Deployment log /tmp/m1-speed-gate-deploy.log; resumed training log
/tmp/m1-ppo-flat-first-no-speed-gate-20261010.log. Confirm new actual PID/run
after switch, point TensorBoard at it, and verify continued iteration output.
Automation updated with new predicate and pending deployment identity.
The existing boundary-exit regression remains unresolved; not claimed fixed.
