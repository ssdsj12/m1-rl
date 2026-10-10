# M1 Flat-first PPO Implementation Plan

> **For agentic workers:** Use subagent-driven-development for the independent runtime gate and inline integration for terrain wiring. Preserve existing isolated contact-recovery worktree.

**Goal:** Fresh2048 pure PPO first learns obstacle-free flat forward locomotion, then measured-progress gates unlock sparse3cm/6cm,10cm alternating obstacles and mixed terrain.

**Architecture:** Prebuild terrain rows with row0 empty, row1 two3cm obstacles,row2 four6cm,row3 eight10cm,row4+existing mixed dense layout. Start every robot at row0/flat column. A runtime episode accumulator measures real command error, forward progress and physical failures before reset. Curriculum switches spawn tiles only at episode reset, never moves colliders under active robots. No action/teacher/servo changes.

**Tech Stack:** Existing IsaacLab/PyTorch/semantic terrain registry/TensorBoard.

## Tasks

- [ ] Runtime gate: add test-first tensor-only episode accumulator, consecutive completed windows with>=90%no failure and<.08m/s speed error, reject short/fake resets/nonfinite data; expose stage and denominator metrics; sparse-obstacle gates also require real strict crossing evidence.
- [ ] Terrain: test-first progressive row count/height/alternating positions, empty row0 accepted; keep default mixed/fixed profiles untouched and add flat-first CLI profile.
- [ ] Integration: measure before auto-reset using wrapped existing velocity reward without changing its numerical value; replace terrain curriculum only in flat-first profile; record metrics and consistent registry at reset. Disable unrelated command/terrain advancement in this profile.
- [ ] Regression: CPU tests of zero-obstacle map, no invalid metric division, false progression on bad/short episodes, correct row/type assignments; native tiny validation of geometry/first reset;2048fresh runtime after isolation.
- [ ] Deployment: stop only currenttrain6169 (user approved fresh restart), preserve priorPTs, start10000fresh steps with2048env/no checkpoint; verifyPT/loss; TensorBoard and monitoring target newrun; update T306 notes.

## Acceptance

No obstacle colliders in initial tile; all2048spawnflat,row0; forward command.18--.45.
No promotion without completed measurable episodes. Three consecutive windows,
each>=2048completed episodes, including all early failures, not only survivors.
Obstacle-stage advancement additionally requires nonzero strict attempts and
>=50%strict successes in measured window. This does not certify final mastery.
No resumed prior model, no forcedlift,MPC,WBC; actual crossing remains unverified
until native video+strict criteria. If initial scene fails do not startlongtrain.
