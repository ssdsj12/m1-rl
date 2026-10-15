# Support knee reserve implementation plan

> Use superpowers:executing-plans inline; one final fresh review before native.

**Goal:** Prefer support knee reserve among equal-load safe support poses, then test actual10cm crossing.
**Architecture:** Pure deterministic lexicographic ranking called only from load-aware choose_support_pose; no new controller.
**Tech Stack:** Python/PyTorch, CPU pytest, isolated Isaac native.
**Spec:** docs/superpowers/specs/2026-10-15-m1-support-knee-reserve-design.md

## Global constraints
Keep126candidates,4/6/8cm envelope,nominalZ-.08floor,.1rad knee,.1mm execution residual,.05rad step,30N actual support and existing crossing/recovery. No production training,PD/wheel/heave changes. No live source overwrite. Preserve all evidence.

## Review focus
Exact primary load beats larger knee reserve; all4active exclusions; noneligible never wins; equal reserve uses cost/index; no-load legacy unchanged. Task1 tests each.

## Task1 — Ranking and integration
- [ ] Write tests/test_m1_teacher_support_knee_reserve.py: literal ranking cases for load/reserve/cost/index, invalid rows, four active legs and float32/64; missing _rank_load_candidates is RED.
- [ ] Implement _rank_load_candidates(cost,weakest,extension_margin,active_wheel,eligible) in m1_teacher_pose.py returning best long[B]; stable sorts cost then min(nonactive margin) then weakest.
- [ ] Integrate only tripod_total_load_n path. Test real saved frame90 selection retains load safety and larger knee margin; run related and full v31 selection+newtests.
- [ ] Update teacher fingerprint v32-support-knee-reserve, no diagnostic schema change; execute barepytest and record dependency failures by name.

## Task2 — Review and actual run
- [ ] Fresh final independent review exact v31 baseline vs delta; C/I one RED/GREEN pass; record minors.
- [ ] Check v31 archive local/serverSHA and terminal; deploy only changed reviewed runtime files and verify SHA.
- [ ] Unique same4env first-obstacle10cm slowrolling/loadfeedback native with video, max1000diagnosticsteps; no concurrent native/training.
- [ ] Read final records/result/video, archive exact source/evidence; goal complete only real requested crossing/recovery proven.

Self-review: Task1 supplies selection to Task2 native; no interface conflict. No new thresholds. Git commit omitted until identity available; do not modify global Git or delete ledgers.
