# M1 mixed terrain density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; preserve the existing remote worktree and unrelated dirty files.

**Goal:** Reference default mixed terrain with flat small counts x1.5, M1 unchanged, and truthful actual-obstacle teacher/strict tracking.
**Architecture:** CPU course profile and deterministic clearance-preserving placement produce grounded obstacle metadata. Registry selects actual per-environment terrain obstacles. Direction-aware events consume that registry; enable the new training profile only after consumers are wired.
**Tech Stack:** Python, PyTorch, Isaac Lab/PhysX, pytest, existing semantic course importer.
**Spec:** ../specs/2026-10-09-m1-mixed-dense-terrain-design.md (user approved).

## Global constraints

No long train before physical crossing; no display edits or GPU7 placeholder changes. Preserve existing M1 asset/controller and16actions. No complete-checkout commits. Authoritative worktree `/home/hexinkun/m1_rl/.worktrees/m1-contact-crossing`; all local source edits via apply_patch then scp.
Baseline29tests passed: ten_cm_course, semantic_course_curriculum_layout, strict_crossing. HEAD0dd7508; prior changes stay uncommitted and intact.

### Task 1: CPU course profile and safe structured layout

Files: new `Go2Pvcnn/ame_baseline/m1_mixed_course.py`, new `Go2Pvcnn/tests/test_m1_mixed_course.py`; later layout adapter in `extension/semantic_course.py`.

- [ ] RED: `from ame_baseline.m1_mixed_course import flat_counts, structured_positions`; expect missing module. Assert flat_counts returns `(15,45,60,75,90,105,120,135,150,165)` with large counts unchanged and rejects invalid row.
- [ ] RED: request165small+3large for seeds0..19; assert exact counts, footprint-aware0.45m edge separation, protected.85m reset box and.5m border. Impossible2x2tile raises rather than drops slots.
- [ ] Implement `structured_positions(small_count, large_count, seed, tile_size=(8.,8.), small_diameter=.05, large_diameter=.45, gap=.45, safety=.85, margin=.5)` returning dict of tuple XY values. Use conservative circumscribed radii (boxes included), staggered candidates, deterministic seed ordering and edge large anchors; reject unsatisfiable requests explicitly.
- [ ] GREEN: `OMP_NUM_THREADS=1 .../amp/bin/python -m pytest -q tests/test_m1_mixed_course.py`. Do not activate config yet.

### Task 2: Runtime registry and event geometry

Files: `extension/semantic_course.py`; new `ame_baseline/m1_course_registry.py`; `ame_baseline/m1_strict_crossing.py` or focused event adapter; tests `test_m1_course_registry.py`, `test_m1_dynamic_crossing.py`.

- [ ] RED: build records from GroundedCourseObstacle, select env rows/cols including emptytiles and terrain changes; assert true world tops, XY/extents and validity masks. Test registry IDs are stable and unique and padding never triggers.
- [ ] Implement grounded record retention and batched registry, with `for_envs(levels, types)` returning centers_top, extents, valid and IDs. Map actual mesh shape dimensions, not configured-height estimates.
- [ ] RED: rotate/translate a synthetic complete crossing; observe same selected obstacle/wheel and one event. Scrape, touchdown before far edge, padding, duplicate/repeated frame and late lift must not count. Reset clears identity.
- [ ] Implement direction-relative encounter selection with identity latch, actual near/far edge and early-lift evidence, then original collision/landing/recovery gates. Keep fixed-course tests passing. Do not use all randomly scattered obstacles as an ordered required course.
- [ ] GREEN: targeted registry/dynamic/legacy strict tests.

### Task 3: Wire M1 profile and consumers

Files: `m1_ame_env_cfg.py`, `ame_env_wrapper.py`, `semantic_course.py`, training/probe entrypoints if they override terrain.

- [ ] RED: assert mixed profile uses reference seven families/proportions and scaled plane sequence, original nonplane/large sequence, M1 robot and16actions; verify explicit diagnostic six-course remains separately selectable.
- [ ] In layout cfg add opt-in structured strategy; use Task1 planner per tile and preserve it through layout_cfg_for_row. All other course users retain existing default behavior.
- [ ] Apply cloned reference SEMANTIC_TERRAIN_CFG for M1 mixed profile; wire semantic counts/safe shape dimensions; no stage or parent post-init may overwrite effective profile.
- [ ] Replace wrapper fixed-six teacher proximity and strict geometry with Task2 registry only in mixed profile; clear mapping on reset/terrain change. Fail closed with visible errors, not plausible zero-only success reporting.
- [ ] GREEN: focused layout, profile, M1 contract, strict and wrapper suites. Review actual action/observation dimensions unchanged.

### Task 4: Physical scene and integration checks

Files: new bounded scene probe/tests if existing probe hardcodes sixblocks; notes/todo.md, T306, log/index, ai/human17.

- [ ] Run no-training GPU0 bounded probe only after fresh process/VRAM check. Use same run handle until terminal. Construct representative low/high flat and nonflat cells; compare actual USD geometry, registry and scanner values; execute bounded neutral steps.
- [ ] Ensure simulated counts match requested counts and all terrainfamilies remain. Separate this result from actual crossing. If layout cannot honor landing gates fail clearly and debug.
- [ ] Request one final independent whole-change review (skill-required), fix important findings with RED/GREEN, run focused suite.
- [ ] Update notes and report exact evidence. Long training remains blocked until real singlewheel lift/roll/land and large-avoidance acceptance.

## Review Focus

Execution result 2026-10-09: Tasks1–3 implemented with RED/GREEN regression;
Task4 scene/integration and final review completed (148passed/1skipped, native
2376records/2280small10cm objects, semantic ray verification and2neutral steps).
Physical future-foot-placement/crossing gate remains OPEN; no long train.
Detailed completion evidence and rulings: `notes/log/2026-10-09-m1-mixed-dense-progress.md`
and `notes/log/2026-10-09-m1-mixed-terrain-verification.md`.

Runtime reset occurs inside env.step: do not use new terrain mapping to judge a previous-episode event. Pose direction must be latched per attempt; cache must not survive geometry changes incorrectly. No per-step USD traversal. Empty/nonflat obstacle sets, failed placement and shape support checks must be explicit. Check requested165 is genuinely generated, not capped at6 or by failed random attempts.
