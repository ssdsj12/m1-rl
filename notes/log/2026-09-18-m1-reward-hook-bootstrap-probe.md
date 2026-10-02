# M1 diagnostic bootstrap hook: one-step runtime result

## Purpose / Stage / Related Todo

Test whether simulation initialization clears the one-off Python profiling hook before reward collection. This is a child of [T306.6g.1](../todo/T306-m1-ame-long-train-stability.md), not a change to training or rewards.

## Method / Inputs

Following two complete 500-step evaluations with missing diagnostic output, add a temporary transparent `EpisodeMetrics.__init__` wrapper only in the one-off runner. It prints the live hook identity and actual code paths after simulation setup, rearms only a missing hook, refuses to overwrite another profiler, and restores the original constructor/path on Python unwind. Reward math, configuration, actions, timestep and disk production files are unchanged. The pre-imported metrics package contains Torch definitions, no Isaac launch or model instantiation.

New tests first RED3, then main-agent CPU union **50 passed in3.13s** (18 trace +32 existing). Tests cover cleared/own/foreign hooks and preservation of a foreign hook on refusal. Independent review PASS. Frozen runner SHA256 `2213d443cce70ffd40b11e706d14556b9108e0abad60fd543ed976dc925dccfb`.

Only **8 env ×1 step**, amp/physicalGPU4, same model119, fixedsmall scenario. [Runtime log](../../run_logs/m1_reward_hook_probe_1step.log), PID2218373. Original wrapper used `TRAIN_ENTRYPOINT=run_logs/m1_reward_exposure_trace.py`, `MAX_ITERATIONS=1`, unique log and tmux `m1reward_hook_probe`.

## Actual Evidence

- `M1_TRACE_HOOK_BOOTSTRAP`: `hook_is_none=false`, `hook_is_own=true`, type `builtins.method`.
- All seven helper/wrapper/metrics `co_filename` paths match the expected production paths.
- `M1_TRACE_HOOK_ARMED`: `kept_existing_hook`, own=true.
- Underlying one-step evaluation completes with its marker and exit0; process is gone.
- **No `M1_REWARD_EXPOSURE` JSON or diagnostic COMPLETE appears.** The collector still fails acceptance.

The hypothesis that startup simply sets the Python hook to None is **not supported** by this observation. Correct hook identity does not establish that the required callbacks were observed; there is no valid exposure dataset to interpret. The two preceding 500-step evaluations both exactly matched baseline behavior and completed; missing diagnostic data is not evidence of premature training exit.

## Result / Decision / Follow-up

Third real diagnostic attempt failed. Stop the `sys.setprofile` approach under systematic-debugging's three-failed-attempt architecture review rule; do not perform another full evaluation or claim gates are measured. Runtime checks of the production reward/config/evaluator/scanner SHA256 hashes exactly match the pre-diagnostic snapshot. No active Isaac process remains; no formal10000 run was launched.

Proposed replacement (pending user design approval): an explicit opt-in diagnostic dictionary/collector passed through the actual reward calculation and fixed evaluator, preserving default return values, reward math, RNG, safety/termination and observation/action contracts. Collect pre-reset data and first-episode denominators directly; validate default-versus-diagnostic tensor equality, terminal/reset handling and one-step real output before a500-step replay. Alternative is deeper native profiling investigation, which does not directly advance robot learning. No new reward weights, curriculum or objective is proposed from the absent data.

The recurring monitor is paused while this diagnostic-interface decision is pending; it must not repeatedly replay these completed tests. [Earlier attempts and tests](2026-09-18-m1-wheelreward-exposure-trace.md), [valid pilot and behavior evidence](2026-09-18-m1-wheelreward-tail-audit.md).

## Git Refs

Candidate740f07e + preserved dirty M1 reward implementation. Only one-off diagnostic scripts and evidence notes changed during this diagnostic sequence; no new production fix or training behavior improvement is claimed.
