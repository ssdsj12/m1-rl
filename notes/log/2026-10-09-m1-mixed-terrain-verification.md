# M1 mixed terrain native verification — 2026-10-09

Scope: approved reference default mixed terrain, flat small density +50%, M1 unchanged.
Worktree: `/home/hexinkun/m1_rl/.worktrees/m1-contact-crossing`.
Reference SHA: `a5b5c5f32f80192452f5326cb25f173ddeaa21b5`.

## Final evidence

- Expanded regression suite:148passed,1skipped.9runtime modules compile.
- GPU0 probe final log: `/tmp/m1_mixed_runtime_20261009_kCZSgT.log`.
- Harness exit0 AND `M1_MIXED_COURSE_RESULT` present, no `M1_MIXED_COURSE_ERROR`.
-7terrain families retained,200tiles (10x20),2376actual spawned obstacle records.
- All2280small USD bounds checked: height0.10000000149m; maxregistry/top error4.694e-8m.
- Representative cells low/high flat and low/high rough have15/165/0/4small objects.
- Real semantic scanner172small-object hits; maxhit/top error2.2874e-6m.
-4envs x2neutral physics steps completed, finite observations; policy1589,critic1592,actions16.
- Strict crossings `[0,0,0,0]`, as expected. This is scene/integration evidence, not crossing skill.
- GPU7 placeholder1768831 remained unchanged. No train launched; probe ended.

## Corrective iterations

First probe: wrong import path, fixed and regression added. Second: production
curriculum changed pinned terrain rows during reset. Third uses a probe-only
curriculum freeze; production curriculum remains enabled. Isaac shutdown could
return0 after assertions, so harness checks explicit RESULT/ERROR markers.

Independent review4important findings fixed with failing regressions first:
failed-event lock; uphill rolling mistaken for lift; missing large/all-wheel
landing geometry; main strict success rate incorrectly using full-course episode
completion. Additional early-touchdown/rolling and abandoned-event regressions
also failed before repairs. Mixed strict rate now uses events/attempts, never
lift counts. Legacy fixed-course diagnostics remain selectable.

## Boundaries still open

Runtime landing checks are conservative actual-geometry checks, NOT a guarantee
of a dynamically feasible future landing plan. Dense placement preserves shape
separation and reset space, but does not prove every obstacle can be crossed by
one wheel while the other three support. Actual lift/roll/land, recovery and
large-obstacle avoidance still require physical video/measurement acceptance.
Do not start a long training run based on this scene probe. Vendor Climb numeric
posture remains unknown and was not guessed. No display configuration changed.

## Changed entry points

- `Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py`: `--course-profile mixed` (default), `fixed` diagnostic.
- `Go2Pvcnn/ame_baseline/m1_mixed_course.py`: reference terrain/course profile and exact-count layout.
- `Go2Pvcnn/ame_baseline/m1_course_registry.py`: actual grounded small targets plus all-obstacle landing geometry.
- `Go2Pvcnn/ame_baseline/m1_dynamic_crossing.py`: direction-relative per-wheel encounters.
- Existing semantic importer, wrapper, strict tracker and metrics integrated; no replacement of M1 asset/controller.

Integration files contain substantial preexisting uncommitted changes, so they
were not committed wholesale or pushed. All changes remain in the authorized
isolated worktree. This log and ledger distinguish prior changes from this scope.
