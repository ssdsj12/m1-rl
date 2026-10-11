# M1 Autonomous Lift Timing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. User has chosen the existing mirror. Steps use checkboxes.

**Goal:** Remove the vertical2cm prerequisite in progressive stages1–3 without weakening physical crossing evidence.

**Architecture:** Explicit per-row autonomous mode in the encounter adapter, independent airborne and overlap lifecycle, unchanged strict inner tracker and reward budget. Wrapper selects mode from post-step course identity, excluding done.

**Tech Stack:** Python, PyTorch CPU tests in isolated remote directory, Isaac native validation only with training stopped, Git.

**Spec:** [approved design](../specs/2026-10-11-m1-autonomous-lift-timing-design.md).

## Global Constraints

- User2026-10-11 now overrides resume choice: new run from18-49-19/model300, preserving its optimizer/std/course,301+9699/exclusive10000/2048/save100. Do not resume latest failed model.
- Preserve existing dirty notes and untracked watchers. No hotpatch, parallel native, control/std/contact threshold/terrain edits.
- Failed PT deletion user-confirmed: only13-17-21model400/500/600/700 plus15-16-31PTs before switching; protect selected300, allotherhistory andlogs. Delete onlyafternewrunverified.
- Workspace CPU baseline uses existing deployment; candidate is isolated `/tmp/m1-autonomous-timing-20261011` with its own `Go2Pvcnn/ame_baseline` and tests. `PYTHONPATH` candidate first, production extension and rsl_rl fallback; `CUDA_VISIBLE_DEVICES=''` for pytest.
- Relevant test command from candidate root: `PYTHONPATH=Go2Pvcnn:/root/quad/m1-rl/.worktrees/contact-recovery/Go2Pvcnn:/root/quad/m1-rl/.worktrees/contact-recovery/Go2Pvcnn/rsl_rl CUDA_VISIBLE_DEVICES='' /opt/conda/envs/env_issacsim/bin/python -m pytest -q Go2Pvcnn/tests/test_m1_autonomous_lift_timing.py Go2Pvcnn/tests/test_m1_dynamic_crossing.py Go2Pvcnn/tests/test_m1_required_crossing.py Go2Pvcnn/tests/test_m1_strict_crossing.py Go2Pvcnn/tests/test_m1_crossing_receipts.py Go2Pvcnn/tests/test_m1_persistent_crossing_reward.py`.

### Task 1: Encounter lifecycle / CPU counterexamples

**Files:** Create `Go2Pvcnn/tests/test_m1_autonomous_lift_timing.py`; modify `Go2Pvcnn/ame_baseline/m1_dynamic_crossing.py` only.

**Produces:** `update(..., autonomous_lift=None)` bool[B], defaultlegacy; per-row flight/overlap/mode state reset consistently. Existing output names retain units.

- [ ] Write real CPU frames (no mocked tracker): airborne-at-entry completes without early_lift, variable lift distances, pre-obstacle20mm lift/land/retry, sub2cm support loss, loaded overlap, post-overlap touchdown, low second clearance, collision/bypass/no-sample, mixed modes and reset.

Core positive sequence (wheel0, obstaclecenter0,halfwidth.025,radius.1,bottomvalues):
```python
step(-.32, .14)  # already airborne, no loaded baseline
step(0., .14)   # actual top.1+clearance.04
out = step(.30, 0., touch=True)
assert out['event_complete'].item()
assert not tracker.early_lift.item()
```
Negative support case: `step(-.32,0); step(-.22,.005,contacts=[False,False,True,True])` must fail independently of2cm.

- [ ] Run new tests before implementation. Expected semantic failures on missing autonomous success/retry/support checks, not dependency errors. Test fixture may omit new keyword on old signature to expose old behavior.
- [ ] Implement state allocations `flight_active`, `crossing_started`, `autonomous_mode`, `mode_known` as bool[B]. Reset all per row. Validate supplied bool[B] mask/device. Mode changes reset existing encounter/receipts and suppress same-frame phantom start; initial mode does not suppress first encounter.
- [ ] Update phase calculation (only enabled autonomous rows; all legacy operations masked with~mode):
```python
observed_flight = ~grounded & (bottom > last_contact_bottom | missing_reference)
flight_active = enabled & ~grounded & (flight_active | observed_flight)
crossing_started |= enabled & overlap
support_bad = ~grounded & (flight_active | crossing_started) & ~single_support
loaded_overlap = overlap & grounded
early_touchdown = crossing_started & grounded & ~fully_past & ~awaiting_recovery
```
Use parenthesized torch comparisons and finite measured-bottom checks in actual code; missing_reference is `~isfinite(last_contact_bottom)`. Retain existing per-overlap clearance/collision gates. For autonomous touchdown require crossing_started and targetgrounded/all4 contacts, plus existing landing_free/touchdown_safe. No mandatory prehistory, no reward budget reset on pre-obstacle touchdown.
- [ ] Run listed full test command. Expected allpass, including unchanged legacy tests. Extend finite/mode/receipt/reward edge cases as needed, RED before each correction.
- [ ] Commit only implementation and its tests: `git add Go2Pvcnn/ame_baseline/m1_dynamic_crossing.py Go2Pvcnn/tests/test_m1_autonomous_lift_timing.py; git commit -m 'Decouple autonomous lift timing from 2cm telemetry'`.

### Task 2: Progressive wrapper wiring and stage isolation

**Files:** same test file plus dynamic module (puremask helper), `Go2Pvcnn/ame_baseline/ame_env_wrapper.py`.

**Consumes:** Task1bool[B] mode. **Produces:** stage1–3/post-step/notdone enabled only forflatfirst.

- [ ] Write helper tests forlevels[0,1,2,3,4],done andflatfirstFalse; source AST assertion verifies wrapper passes post-step terrain levels anddone to helper and passes itsresult totracker. Expected missing helper/wiring assertions fail.
- [ ] Add helper and wrapper argument:
```python
def autonomous_lift_stage_mask(levels, done, *, flat_first):
    if levels.shape != done.shape or done.dtype != torch.bool:
        raise ValueError('levels/done must be aligned [B]')
    return ((levels >= 1) & (levels <= 3) & ~done) if flat_first else torch.zeros_like(done)
```
Validate rank/device too. Call inside actualcourse registry branch after reset(done), usingcurrentterrainlevels; pass keyword `autonomous_lift`. Existing donevalidmask blocks resetposes.
- [ ] Keep historical `prelift_events` name/meaning; comment vertical2cm telemetryonly forautonomousmode. Do not alter `.3/.02m` or rewardfallback API.
- [ ] Run Task1suite pluswrapper source tests and current requiredreward/route/reset tests. Expected pass; candidate modules import fromcandidate, notproduction.
- [ ] Commit named files only with message `Wire autonomous lift mode to progressive stages only`.

### Task 3: Review, replay, safe deployment and new model300 run

**Files:** README, pairedhuman/ai17, notes/T306/index/log, disposable validation/lifecycle scripts outsideproduction.

**Consumes:** candidatehashes/mode contract. **Produces:** verified runtime and newrun, or explicit blocker withoutfalse claims.

- [ ] Fresh whole-change review after tasks1/2 using requesting-code-review. Focus: mixedmask state, existing receipts, terminalpose pairing, earlier-than-encounter lift, reward rebasing, support-gate physical strength, no magic timing condition.
- [ ] Apply importantfindings using failingregressions; rerun fullsuite. CPU replay savedtrace700 must retain env283supportfailure,0success; compare legacy mode byte-equivalentoutputs where possible.
- [ ] Verify currentPID/cwd/argv and selectedmodel300 SHA4437ed429f6c2339284efb567b1dda5aabab83f59823bc376f80d23ebccdc075; CPUcheck39weights/33optimizer/16std/stage1/iter300,next301. Pause currentverifiedtraining safely, retain checkpoint while validationpending.
- [ ] With GPUreleased/noothernative, native candidate-only measurement uses realwrapper and4env, explicit mode masks/reward inputs parity, then exits. Not a learned-crossing assertion and not staticfoldfixture gate.
- [ ] Backup exact runtime files before replacing onlycandidatefiles; verify bytehashes. Launch new unique log via guarded existing `run_m1_pure_ppo.sh` with `CHECKPOINT=...18-49-19/bb57e7d/model_300.pt M1_LOAD_OPTIMIZER=1 NUM_ENVS=2048 MAX_ITERATIONS=9699 DEVICE=cuda:0 COURSE_PROFILE=flat-first`, keepstd/save100 inherited and verified.
- [ ] Verify actual firstupdates finite, correctrun/cwd/argv/2048/GPU0, no duplicateprocess. Retarget onlyidentifiedTB to newrun; no network/globalSSHchanges.
- [ ] Delete only user-confirmed oldPT scope after model300protected and newrun verified; enumerate exact files, resolvedcontainment, hashes andcounts. Retain logs. If userhasnot answered scope, leavePT untouched and reportpending.
- [ ] README and notes explicitly separate deployment/testproof from learnedability, include newrun, rollbackchoice300, deletionmanifest, geometryunchanged. Updateautomation currentidentity; normalpush m1-10-11 onlyexistingauthorization, noforce/globalGit.

## Review Focus

No supportloss forgiveness by lifting under2cm; no loaded-on-top false success; no historyless success without actualoverlap; no retry budget refresh; no stage4effect; mode switches invalidate stale receipts; donepre/post snapshotalignment; no deletedPT referenced by newrun; resume300latestuseroverride beats oldspec.
