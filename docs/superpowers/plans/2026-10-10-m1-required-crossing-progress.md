# SDD ledger — plan: docs/superpowers/plans/2026-10-10-m1-required-crossing.md

Spec: approved user requests in this task; no separate spec file. User's latest
override is FRESH2048/10000/save100, not resume. Old8573 is stopped; PT retained.

Pre-flight interfaces: task1 physical tracker -> task2 reward consumes one-shot
prelift/recovery pulses. Task3 authored cuboid bounds -> tracker registry and
reward zone; stage0/row4+ geometry unchanged.

Ruling: use the existing isolated remote worktree and local edit mirror; preserve
all earlier uncommitted edits. Review this delta against before/ backups rather
than pretending bb57e7d contains only this task. Cost: no standalone commit yet.

Ruling: in progressive obstacle slabs strip ALL positive rate terms (including
old progress/climb and velocity tracking), retain negative costs, then add .3
one-shot measured single prelift and2 stable-recovery bonuses. This closes the
user's explicit sliding-reward loophole, including general locomotion shaping.
Cost: sparser exploration in obstacle slabs; monitor learned progress/stalling.

Ruling: widen only stage1–3 to .10x.18m cuboids, alternating y=+/-.215m;
longitudinal pitches1.8/1.8/.9m retained. Mixed row4+ shapes unchanged. Cost:
initial obstacle stages intentionally lose shape diversity for unambiguous exposure.

Task1 complete: measured wheel-track spacing .43m, nominal tire half-width about
.05m; opposite support clearance .29m for.18m-wide blocks. RewardManager
_step_reward is value/dt, verified in installed IsaacLab source.
Task2/3:7 new RED failures ->31 GREEN; combined affected regression130passed.
Added whole-overlap clearance failure (old one-frame latch could hide a later dip).
Review dispatched fresh context; native4env integration currently running.
Full pytest attempted:19collection errors from missing pxr/evaluation/rsl_rl
paths and stale imports; not claimed as green. Full output /tmp/m1-required-full-suite.log.
Task2/3 complete: final134affectedtests green. Native final probe passed and exited0.
Final review fixed telemetry minima/counters with RED->GREEN. Late recovery was
regraded important and fixed with RED->GREEN; paired support strictness fixed.
Deferred minor: explicit failure/reset prelift-pulse fixtures beyond existing reset tests.
Ruling: native geometry/reward probe replaces old-policy rollout/video for
deployment because user requires fresh training; learned/video acceptance stays OPEN.
Task4: freshPID10311,run2026-10-10_18-49-19/bb57e7d. Iteration0 complete,
model_0.pt exists; TensorBoard10555 switched, local16006API verified;
monitor re-enabled with fresh-run instructions. Actual crossing remains unverified.
