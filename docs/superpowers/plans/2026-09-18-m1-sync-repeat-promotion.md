# M1 Sync Repeat and Promotion Implementation Plan

> **For agentic workers:** Use subagent-driven-development for independent audits/reviews. The user now requests continued work until acceptance; do not stop after each substep for another “continue”. Preserve the established safety/behavior gates.

**Goal:** Establish three independent full8×1600 passes for the unchanged accepted controller before promoting it and preparing1024 validation.

**Architecture:** Run14 is pass1. Runs15/16 use identical frozen candidate files, amp, physicalGPU7, seed/config/source and independent verifier. Only after both additional runs pass, copy the exact reviewed/tested implementation into the formal reference adapter; the AME task and SDK remain outside this promotion.

**Tech Stack:** ampPython3.10, IsaacLab45, PyTorch/NumPy/pytest, SSH4090.

## Fixed boundaries

- Existing approved specs: reference-controller-validation and post-cross-wheel-sync, both2026-09-18. GPU7 user amendment supersedes older GPU4 text.
- Reference `/home/hexinkun/m1` and installed SDK remain read-only. No sweep, automatic restart, changed denominator or relaxed threshold.
- Candidate `/home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter`, hash-identical to run14; core18aeb0c7,bridge817ed035,verdict1e93707e,runba2b2700,runtime1825d125.
- Work remains in the user-approved isolated candidate. Formal target `/home/hexinkun/m1_rl/tools/m1_reference_validation` on existingm1_rl branch is clean againsta86cbf5; do not create/rebase/reset the user's branch or overwrite unrelated changes.
- Preserve15GiBreservation for8env. Before1024, only verified own reservation may be stopped under existing user authorization; restore it when no task compute process remains. Never signal other jobs.

## Task1: repeatability, no implementation changes

- [x] Read current notes/specs, confirm source hashes, GPU7UUID/resources and formal target status.
- [x] Launchrun15 in a new output directory, once:

```bash
ulimit -c 0
bash /home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter/run.sh \
  --num-envs 8 --steps 1600 \
  --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_15_sync_repeat \
  > /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_15_sync_repeat.log 2>&1
```

- [x] Require external native/wrapper0, exact1600/6400sensorupdates, strict8/8,0resets. Execute immutable `sync_verdict.py --output <run15> --baseline /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_12_normal_clone`; exit0/acceptedtrue/noerrors required.
- [x] Only on pass, launchrun16 with identical command replacing15with16; require the same original+independent gates. Preserve both raw artifacts. Failure stops scale-up and starts evidence-based diagnosis, not an automatic rerun.
- [x] Comparethree run identities/source hashes and all per-env gates. Fixed geometry/seed repeats prove repeatability, not generalization. Runs15/16 each match run14's2700non-timing NPZ arrays bitwise; differentPID/runID, no restart.

## Task2: promote the exact accepted reference implementation

- [x] Recheck formal tracked diff and absence of all six new paths; retain any unrelated work.
- [x] Test-first promotion: copy only three reviewed new test files into formal `tests/`, run focused tests to demonstrate missing implementation before source promotion. Do not rewrite existing tests or thresholds.
- [x] Copy exactly the three new source files and two minimal wiring files from frozen candidate. No semantic edits during promotion; verifySHA256 ofall8copiedfiles identical to tested candidate. Existing `metrics.py`, `provenance.py`, `run.sh`, geometry and finalizer unchanged.
- [x] Run formal fullsuite373tests with amp, USDlibs environment, no bytecode/plugin/cache; bashsyntaxcheck. Independent specification check then quality check: actual formal diff must be only approved candidate. Recheckdirty unrelatedpaths preserved.
- [x] Commit only these8paths after verification, leaving unrelated working changes unstaged. Record reference-adapter feature/verified commit646f486 separately from broaderAME refs; no push required.

## Task3:1024 readiness audit before new scale code or physical work

- [x] Independently read-only audit1024memory/disk, quadratic contactmatrix, source/config scaling and current fixed8×1600 verifier limitations. Do not reuse its8-env baseline comparison for1024randomization.
- [x] Define a scale-specific verification plan from that evidence, retaining original1024/1024strict criteria and actual post-cross diagnostics; require tests/reviews before launching1024x32then1024x1600. Design/plan5553e84. A completed8-envpromotion is not a1024orAMEclaim.
- [x] Update dashboard/T306/logindex and per-run evidence with actual outcomes and active next leaf. Persistent overall goal remains active until single10000and learned crossing/avoidance acceptance, or a real external blocker requiring user action.
