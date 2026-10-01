# M1 reference GPU7 shutdown diagnostic reproduction

## Purpose / Stage / Todo

T306.6h.5, child blocking the independent controller startup gate T306.6h.2. Diagnose native139 after all32 steps and both close calls; not PPO and not automatic restart. See [first attempt](2026-09-18-m1-reference-gpu7-smoke.md).

## Procedure / Conditions

Same amp/GPU7/source/seed/controller/thresholds as ddad702, keeping user's15GB sleep.py PID2795762. Only diagnostic change: `PYTHONFAULTHANDLER=1`. Fresh output `run_logs/m1_reference_validation/20260918_gpu7_8x32_02_faulttrace` and sibling `.log`; PID2834408, run_id `68bc0b04-1032-4c0c-a6b4-c7b1f5acffd2`. Command form: `PYTHONFAULTHANDLER=1 bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 32 --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x32_02_faulttrace`.

## Metrics / Result

All8 have32 active samples, no reset or hard failure;32 prepare/IK calls,128 substep updates; candidate issues empty.15.298s warm-cache collection. Same ENV_CLOSED→APP_CLOSED→POST_CLEANUP→SIGSEGV139; finalizer completed/startup_passed=false, wrapper2. No readable faulthandler stack. No available core/gdb/coredumpctl; apport log and dmesg permissions unavailable. No privileged changes or installs attempted.

## Conclusion / Follow-up

Reproducible post-close failure, not an iteration-budget stop or demonstrated GPU memory exhaustion. Source audit finds caller sink/holder/sensor/wrapper/env retaining native PhysX/callback owners after SimulationApp.close unloads plugins. This is a concrete lifetime risk, NOT yet a proven native crash cause. Reference evaluator has similar locals but default fast_shutdown=True, so its success cannot validate our normal-interpreter-exit path. Test minimal owned-object release/gc before app.close with TDD and a fresh8×32 run. No forced exit, no false completion marker, no controller changes, no1600/1024 until startup passes.

## Git Refs

Baseline/Candidate ddad702. No behavior fix in this reproduction. Key code: tools/m1_reference_validation/run.py and runtime.py; installed SimulationApp.close lines561–617 inspected read-only.
