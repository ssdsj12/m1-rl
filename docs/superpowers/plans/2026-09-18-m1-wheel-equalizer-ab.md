# M1 wheel equalizer A/B implementation plan

> **For agentic workers:** Execute the approved single-variable design task by task using executing-plans and independent review. Do not turn this bounded diagnostic into a parameter sweep or long training run.

**Goal:** Test whether the existing gain3 wheel equalizer creates the observed saturated period-two targets.

**Architecture:** Use an isolated copy of formal reference adapter a86cbf5. Override exactly `wave_wheel_equalize_gain=0.0`; preserve all source, low-level actuator control, feedforward, terrain, randomization and strict metrics. Label the candidate in provenance/configuration.

**Tech Stack:** amp Python, IsaacLab45, pytest, NumPy, GPU7.

## Paths

- Baseline: `/home/hexinkun/m1_rl/tools/m1_reference_validation` (clean against a86cbf5).
- Local candidate: `C:/Users/xk/Documents/project/m1_reference_validation_stage/equalizer_off/adapter`.
- Remote candidate: `/home/hexinkun/m1_debug_tools/equalizer_off_20260918/adapter`.
- Candidate output: `/home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_13_equalizer_off`.

## Task1: freeze copy and test-first override

- [x] Copy baseline to the new isolated directory; baseline212tests passed24.43s.
- [x] Extend fake cfg with gain3 and before3/after0 assertions. Corrected RED8failed/9passed includes gain unchanged, missing source guard and missing metadata.
- [x] Extend partial-main integration test and negative cfg-diff tests. No new simulator mocks.
- [x] Implement exact override and metadata in runtime.py/run.py only. Focused17passed0.37s; full225passed24.49s. No control-loop or metric edits.
- [x] Focused17/full225 tests and bash syntax passed, spec then quality review PASS; post-run full225passed24.77s. Only four approved candidate files differ; formal adapter unchanged.

## Task2: one physical test

- [x] GPU7 identity/resources rechecked; original15GiB reservation2795762 remained alive, no process signals.
- [x] Run once with exact `bash /home/hexinkun/m1_debug_tools/equalizer_off_20260918/adapter/run.sh --num-envs 8 --steps 1600 --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_13_equalizer_off`, stdout/stderr at output-prefix.log, core dumps disabled. PID3589897; no restart/GDB/timeout signal.
- [x] Exact1600steps/6400sensor updates, cleanup markers then native0. Completed=true, strict1/8, wrapper3. Behavior rejected despite normal completion.

## Task3: comparison and handoff

- [x] Exact gain-only config delta; before/source snapshots, provenance minus candidate label, scene, bindingbefore/after and all6initialarrays match.
- [x] Full strict reports and event samples compared; paired first-episode tail800 targetRMS.848488→0, speedRMS.784206→.237260. Env1 has only135first-episode samples; do not mix its11raw resets into strict means. No metric/window change.
- [x] Candidate rejected: env1 reference-predicate termination; env2/5 RAR lateral corridor miss; strict4/8→1/8. Dashboard/branch/log/index updated; new.6a synchronization/crossing coupling design required.
- [x] Candidate/evidence preserved outside formal code; no promotion, cleanup, extra simulation or1024/10000 claim.

## CPU command

```bash
cd /home/hexinkun/m1_debug_tools/equalizer_off_20260918/adapter
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 \
LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin \
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q -p no:cacheprovider tests
```
