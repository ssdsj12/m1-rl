# M1 Lift-and-Roll Layout Implementation Plan

## Latest execution override: PPO self-learning

User explicitly requests long training first and autonomous folding/crossing.
Static folded-leg fixture acceptance is no longer a pre-training gate; its
inconclusive evidence stays. Geometry/roles/maps and96recovery placements have
been checked,233CPU regressions pass, and equal8+70 is selected for flat-first.
Start user-selectedmodel300,next301+9699,2048/save100, preserve optimizer/std/course.
No swing/control takeover. Dynamic mastery remains OPEN. Independent review
found noCritical/Important selector/launch issues.
See [live deployment evidence](../../../notes/log/2026-10-11-m1-lift-roll-self-learning.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe target/fill separation and a dense alternating single-wheel layout without changing PPO control or strict success.

**Architecture:** Authored roles survive both grounding paths. The crossing registry excludes explicit fill from encounter/mandatory targets, while its all-geometry landing registry retains every collider. A deterministic geometry candidate preserves two rolling strips and the spawn support area; deployment is conditional on geometry and native safety gates, not merely passing unit tests.

**Tech Stack:** Python dataclasses, PyTorch CPU, pytest, Isaac Lab/PhysX, existing PPO checkpoint runner.

**Spec:** `docs/superpowers/specs/2026-10-11-m1-alternating-lift-roll-design.md`, plus user approval of explicit target/fill roles.

## Global constraints and interfaces

Local root: `C:/Users/xk/Documents/project/m1-ppo-recovery`; dedicated `codex/m1-ppo-repair-upload` mirror, not the running Linux source. Remote production: `/root/quad/m1-rl/.worktrees/contact-recovery` on `a21472797434572800304964`. CPU candidate files must be separate from production, under `/tmp/m1-lift-roll-candidate-20261011`; no GPU probe alongside training.

`required_crossing: bool | None = None` is metadata. `None` retains legacy behavior, `False` marks fill, `True` marks explicit target. Invalid non-bool values fail. Keep semantic class, collider, perception and all-geometry landing records independent from this flag. Stage0/mixed4+ remain legacy. No changes to std, controller, reset posture, reward weights, strict clearance or boundary.

### Task 1: Preserve roles from authored geometry through runtime tables

Files: modify `Go2Pvcnn/extension/semantic_course.py`, `Go2Pvcnn/ame_baseline/m1_course_registry.py`; create `Go2Pvcnn/tests/test_m1_fill_roles.py`.

- [ ] Write RED tests: target at Y=.215 plus fill at Y=1 must yield one encounter target, two landing geometries, and required wheels `[True,False,True,False]`. Legacy metadata-free small objects remain targets. A fill placed under a wheel must still make the existing landing-distance predicate false. Both CPU and world-query grounding must preserve roles.

```python
target = SimpleNamespace(row=1, col=0, slot_index=0, semantic_class='small',
    shape_kind='cuboid', shape_params={'size': (.10,.18,.03)},
    world_center=(0.,.215,.015), required_crossing=True)
fill = SimpleNamespace(**{**vars(target), 'slot_index':1,
    'world_center':(0.,1.,.015), 'required_crossing':False})
c = CourseRegistry([target,fill],rows=4,cols=1,device='cpu').for_envs(
    torch.tensor([1]),torch.tensor([0]))
assert c['valid'].sum().item() == 1
assert c['landing_valid'].sum().item() == 2
assert progressive_required_wheels(c,torch.zeros(1)).tolist() == [[[True,False,True,False]]]
```

- [ ] Run `PYTHONPATH=Go2Pvcnn python -m pytest -q Go2Pvcnn/tests/test_m1_fill_roles.py`. Expected: assertion/constructor failures caused by absent role handling; not missing dependencies.
- [ ] Add the defaulted role field to both dataclasses; pass `required_crossing=anchor.required_crossing` in both GroundedCourseObstacle constructors. Validate and filter only the encounter branch:

```python
role = getattr(obj, 'required_crossing', None)
if role is not None and type(role) is not bool:
    raise ValueError('required_crossing must be bool or None')
if not _all_geometry and (obj.semantic_class != 'small' or role is False):
    continue
```

- [ ] Run new tests plus `test_m1_course_registry.py`, `test_m1_persistent_route_penalty.py`, `test_m1_dynamic_crossing.py`, `test_semantic_course_curriculum_layout.py`. Expected: all pass, off-track fill never required, but still obstructs landing.
- [ ] Commit only role implementation/tests and evidence.

### Task 2: Build a candidate and prove rolling and landing space before production selection

Files: create `Go2Pvcnn/ame_baseline/m1_lift_roll_layout.py`, `Go2Pvcnn/tests/test_m1_lift_roll_layout.py`. No selection in the training configuration until the geometry gates pass.

Candidate schema: frozen `Block(x, y, length, width, height, required_crossing)`; `candidate_blocks(row)` returns target blocks followed by fill. Preserve target X/count/height from `progressive_positions`/`progressive_row`; row0 returns empty, rows outside1..3 raise. Fill space over X/Y[-7.95,7.95], clipped around spawn rectangle X[-2.55,-1.45],Y[-.8,.8], and two rolling strips Y=±.215 with initial half-width .13. Partition fill into longitudinal cells of .5m separated by .02m, and lateral complement intervals; disjoint tops, no transverse connecting bar through a rolling strip. Initial targets remain .10×.18m. These numeric choices are candidates, not safety certificates.

- [ ] RED: function/Block presence, deterministic rows, target order and counts, real heights, no fill overlap with reserved support strips or spawn area, no touching fill tops, all inside original tile, no geometry output for stage0.
- [ ] Implement pure geometry construction using interval subtraction. For interval `[a,b]` and hole `[c,d]`, return nonempty pieces `[a,min(b,c)]` and `[max(a,d),b]`; do not silently accept inverted/zero-size blocks. Reject nonfinite geometry.
- [ ] GREEN: run `PYTHONPATH=Go2Pvcnn python -m pytest -q Go2Pvcnn/tests/test_m1_lift_roll_layout.py`. Expected: pure geometric invariants pass.
- [ ] Check four-wheel XY circles at front and rear recovery positions for each target and throughout five frames/.045m forward travel, against every block. Use wheel X offsets±.3295, Y±.215, radius.119208 and far margin.04; target center X plus half-length+radius+far minus selected wheel offset gives first recovery root. Required minimum free-distance margin positive and root below7.25.
- [ ] Reject a candidate if any valid-support window is empty. Do not change runtime landing_free, required_far_margin or boundaries to make it pass. Record pose/time of first failure.
- [ ] Anti-bypass check uses the complete obstacle geometry, not target-only tables. Search each ground wheel's free-space connectivity with conservative minimum lateral tire half-width .02325, 2mm lateral resolution around target/strip edges and obstacle corners, including possible strip changes through cell gaps. A found path is a witness to reject or investigate, not automatic proof the whole vehicle can follow it; a full-body bypass witness is a rejection. Report discrete limits; never call sampled no-path an all-posture proof.
- [ ] Check actual mesh/FK posture envelopes for the reserved corridors before GPU deployment. If independent support/anti-bypass constraints conflict, retain candidate/negative evidence and stop deployment under the approved spec; do not guess a controller workaround.
- [ ] Commit only the tested candidate and geometry evidence; production selector stays unchanged until native readiness is established.

### Task 3: Conditional authoring integration, native check, continuation and publication

Files: `Go2Pvcnn/extension/semantic_course.py`, `Go2Pvcnn/scripts/probe_m1_flat_first.py`, affected terrain tests, root `README.md`, paired ai/human17 and notes. This task is gated on Task2; an unsuccessful geometry gate is an incomplete implementation, not permission to publish a new production layout.

- [ ] RED authoring test: candidate targets/fill have exact shapes and roles in grounded records; semantic class remains small for both; row0 and mixed rows equal baseline. Extend existing anchors after authored target anchors only for the new approved stage1--3 candidate. Use unique slot_index, world_xy=origin+local_xy, bottom_to_center_offset and existing spawn path; no new sensor channel or role in policy observation.
- [ ] Preserve role through both grounding constructors (Task1); compare all native authored centers, dimensions/heights, semantic hits, target table and landing table against the candidate manifest. Do not replace per-shape dimensions with target_diameter.
- [ ] Run CPU regression: `test_m1_fill_roles.py test_m1_lift_roll_layout.py test_m1_flat_first_terrain.py test_m1_required_crossing.py test_m1_strict_crossing.py test_m1_dynamic_crossing.py test_m1_persistent_crossing_reward.py test_m1_persistent_route_penalty.py test_m1_obstacle_rewards.py test_m1_learning_curriculum.py test_m1_recovery_runtime.py test_m1_dense_forward.py tests/ame_baseline/test_ame_runner_checkpoint.py test_semantic_course_curriculum_layout.py` under Go2Pvcnn tests. Expected: all pass; report exact selection and result, not full-repository green.
- [ ] Freshly identify live training/cwd/cmd and newest complete saved PT; CPU validate finite weights/optimizer/std, iter/next_iter and course. Back up exact replaced source files; SIGINT only the verified current training. Wait for process exit/GPU release before any native probe.
- [ ] Execute bounded4env native geometry/map/reset/actual collision and support-placement checks on GPU0. No synthetic trajectory is fed to PPO or counted as learned crossing. Check all target front/rear recovery poses and support-wheel paths, including body/thigh/calf intersections with fill. Fail closed on collision, no landing room, OOM or wrong counts. Do not resume a failing candidate.
- [ ] Exit probes and verify GPU released. Launch existing guarded one-shot PPO workflow from validated current PT next_iter to10000,2048env/save100/keep_std/optimizer/course; verify actual iteration, loss, logdir and unique process. Do not reuse historical1000 automatically or run old watchers.
- [ ] Record real video/strict event evidence separately from geometric/native wiring. Update README, notes/index, T306, dashboard, log index and paired contract docs. Publish only coherent tested changes via normal non-force push to GitHub `m1-10-11`, independently verify remote SHA. Exclude checkpoints and untracked old watchers. Update monitoring to exact deployed identity; no mastery claim without real policy evidence.

## Review focus / stop rules

Review role flag validation before filtering; both grounding paths; stable unique IDs and unchanged mixed rows; semantic-small collider preservation; target-only versus all-geometry consumers; over-conservative landing circles versus real tire/leg geometry; narrow-band bypass loopholes; fill gaps becoming driveable tops; actual2048env memory cost; no concurrent native diagnostics or hot deployment. A new physical incompatibility stops deployment, not user approval of the already confirmed action semantics.

## Planning review

Task1 establishes role contracts consumed by Task3. Task2 provides geometry/negative-witness evidence consumed by Task3; it is intentionally a falsifiable candidate, not an assumed proof. Task3 cannot start if Task2 fails. Exact native probe extensions and production authoring changes must be red/green developed from the accepted candidate manifest; if no candidate survives, record the failed acceptance criterion instead of writing speculative deployment code.
## 实施中用户修订（优先于上文历史数量）

恢复点后续由用户明确改为当前谱系18-49-19/model300。CPU已校验完整，next301+9699至10000，保留optimizer/std/course/2048env/save100。1400保留备份，覆盖旧latest-only恢复选择；原生布局验收要求不变，尚未启动。

三个障碍高度阶段统一8个目标、相同X=-1.2+1.1*i/Y±.215及相同70填充，只变3/6/10cm高度。Task3先加等数量/等XY/等足迹反例，修改progressive_row/positions并同步authoring fixture/native清单；保留stage0/mixed4。旧4/6/8图与原生准备不部署。完整回归、有界全机/单轮空间及原生筛选须对新清单重核，1400边界暂停保护不变。
