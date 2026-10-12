# M1 Collision Budget Fresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Charge collision at most5/s, reset after20 actually charged, suppress duplicate terminal20, then start fresh2048 training.
**Architecture:** A tensor budget owns per-row accumulated costs. A manager termination term owns lifecycle and a once-per-control-step snapshot shared by the reward and failure-cost predicate. Preserve snapshot across automatic row reset; only live accumulator clears. Keep raw collision detection available to strict success checks.
**Tech Stack:** PyTorch, Isaac Lab manager terms, AME PPO, pytest.
**Spec:** ../specs/2026-10-12-m1-collision-five-fresh-design.md

## Global Constraints

- max collision rate5/s, episode budget20; max of two detectors, no double cost; dt once.
- Budget termination no additional20 even with simultaneous other failure; standalone other physical failure remains20, pure timeout0.
- Fixed ABAD0/8HIP-KNEE/.30wheel/2048/cuda0/root.62; all other reward/physics/success unchanged.
- Fresh stage0/network/Adam/std; no oldPT load; all oldPT/logs retained. Native must exit before training starts.
- Inline in user-selected mirror branch10-12; deployment explicitly authorized. User directed implementation then direct fresh launch, superseding an extra plan/start confirmation.

## Review Focus

- Repeated term calls in one step must not double debit (Task1/2).
- Asynchronous reset must clear only selected rows and retain terminal snapshots (Task1/2/3).
- Fractional last charge must cap precisely at20 (Task1).
- Detector invalid values cannot propagate NaN and bypass numerical failure protection (Task1/2).
- Budget + fall/timeout coincidence must not cause duplicate20 (Task2/3).

### Task 1: Tensor budget and manager adapter

**Files:** Create `Go2Pvcnn/ame_baseline/m1_collision_budget.py`, `Go2Pvcnn/tests/test_m1_collision_budget.py`.
**Interfaces:** `CollisionBudget(n, device, dt)` with `update(signal, step)` returning dict(cost,total,exhausted), `reset(env_ids)`; tensor-only. `CollisionBudgetTermination(ManagerTermBase)` manager callable obtains max of existing geometry/contact detectors; `reset` clears live rows without snapshot erasure. `collision_budget_cost(env)` returns negative discrete cost/dt; `collision_budget_exhausted(env)` reads existing current snapshot.
- [ ] Write tests: 199 full20ms ticks not exhausted, 200th exhausted/total20; same step id unchanged; signal0 holds; half signal costs.05; residual<.1 clipped; reset one of2 rows; invaliddt rejected, invalidsignal finite/conservative; resetting preserves old snapshot until nextstep.
- [ ] Run `python -m pytest tests/test_m1_collision_budget.py -q` in Go2Pvcnn: expected missing implementation failure.
- [ ] Implement core/adapter with float64 accumulator to avoid float32 drift at200 ticks; outputs use reward-compatible float32; manager calls use common_step_counter.
- [ ] Run same test: expected PASS. Commit only Task1 files.

### Task 2: Runtime, contract and terminal-cost wiring

**Files:** Modify `m1_ame_env_cfg.py`, `m1_ame_rewards.py`, `m1_ame_contract.py`, `ame_env_wrapper.py` only if needed for telemetry; extend tests/test_m1_collision_budget.py and test_m1_mirrored_collision_reset.py. Preserve raw obstacle_collision helper.
**Interfaces:** Task1 manager registered as collision_budget termination (time_out=False); old immediate obstacle_collision term removed. Reward collision_budget_cost weight1 replaces old geometry/non_support terms. Failure penalty masks current exhausted rows. Contract introduces collision_budget version/rate/budget/max/repeat semantics and changes immediate-reset metadata; fixedABAD trainingversion4/nonfixedversion3.
- [ ] Write failing runtime tests for reward/termination same snapshot, combined detectors no sum, standalone failure20, puretimeout0, exhausted+failure0, and stale checkpoint rejection before loading.
- [ ] Run focused tests: expected old semantics failure.
- [ ] Wire terms; preserve remaining physical termination and strict collision logic. Add collision cost/total/exhaustion metrics from terminal snapshot rather than post-reset state.
- [ ] Run budget + terminations + mirrored + fixedABAD + stall/slip regression. Run bare pytest separately and report dependency/legacy failures precisely. Commit scoped code/tests.

### Task 3: Real native gate and independent review

**Files:** Create `Go2Pvcnn/scripts/probe_m1_collision_budget.py`; tests assert evidence validator rejects vacuous success if needed.
**Interfaces:** production config on isolated candidate,4env, real detectors; COMPLETE only after exercised collision below budget, budget exhaustion, unchanged physical failures, reset row locality and raw/final reward agreement.
- [ ] Verify host no train/probe and GPU free; copy candidate package without editing production.
- [ ] Run actual flat/obstacle tests; use bounded controlled placement solely as collision fixture, never training action takeover. Pre-reset snapshot trace must prove -5dt charge and budget20 no duplicatefailure; ground negative control; after reset newrow0, otherrowsunchanged. Native config inspect combined rewards and unchanged8action contract.
- [ ] Native process must exit, GPU free. Any fixture failure is diagnosed without relaxing thresholds.
- [ ] Fresh-context whole-change reviewer checks spec and Review Focus; Important fixes require new RED/GREEN tests and full focused regression before deployment.

### Task 4: Authorized deployment, fresh training and evidence

**Files:** README.md; notes/log/2026-10-12-m1-collision-budget-fresh.md; notes/index.md, notes/todo.md, notes/todo/T306-m1-ame-long-train-stability.md, notes/log/index.md; scoped deploy/audit script in task workspace.
- [ ] Back up exact production runtime targets with hashes, deploy validated candidate, verify byte equality and no concurrent probe.
- [ ] Launch kernel-flock protected unique run via existing purePPO entry with fixedABAD/2048/cuda0/save100/max10000; strip CHECKPOINT/M1_LOAD_OPTIMIZER/resume flags. No destructive checkpoint actions.
- [ ] Verify cmdline/cwd/env/env_cfg, real finite updates0+, model0CPU freshAdam/8std/stage0/new collision contract/no conversions; confirm sourcePT never read.
- [ ] TensorBoard points newrun; leave local forwarding/old6007 untouched. Sync notes/hash; update existing monitor with latest authorized freshrun and collision budget semantics; old paused run never resumes.
- [ ] Commit scoped implementation/readme/tasknotes without old watcher/PT/unrelated diagnostic changes; publication only per existing authorization. Report verified start separately from unproven learnedcrossing.

## Self-review

All spec requirements map to Tasks1–4. Shared signatures are defined above; budget state belongs to termination lifecycle, not wrapper post-reset reads. Fresh training is contingent on CPU/review/native gates; no observation/control expansion.
