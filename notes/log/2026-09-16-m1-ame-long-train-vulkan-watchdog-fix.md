# 2026-09-16 M1 AME Long-Train Vulkan/Watchdog Fix

## Purpose

Determine why the M1 AME 1024-env run repeatedly exited before 10000
iterations, fix the application-level failure mode, preserve correct resume
state, and prevent an Isaac shutdown deadlock from blocking the run forever.

## Stage

- Workflow: M1 AME training and checkpoint resume
- Runtime: Isaac Lab 4.5, headless, 1024 environments
- Operations: long-train supervision and recovery

## Related Todo

- [T306 M1 AME long-train stability](../todo/T306-m1-ame-long-train-stability.md)

## Command / Procedure

1. Parsed every `RESTART` / `EARLY_TERMINATION` boundary in the cumulative
   supervisor log and inspected the matching Kit logs.
2. Checked kernel-visible GPU use, process/thread state, disk/memory pressure,
   checkpoint finiteness, and driver/userspace versions.
3. Ran a minimal Vulkan instance probe with and without
   `CUDA_VISIBLE_DEVICES`.
4. Reproduced the pre-update clean exit from `model_1030.pt` at 1024 envs.
5. A/B tested the Linux Kit arguments and proved that renderer multi-GPU,
   rather than the invalid `app.vulkan=false` DX12 selection, owns the
   application-level failure path.
6. Added RED unit/integration tests, then implemented the single-GPU launcher,
   atomic checkpoint, exact resume, and supervisor-v2 changes.
7. Ran direct launcher and supervisor real-resume smokes.

## Input Conditions

- Baseline Ref: `55aa891`
- Initial checkpoint: `model_1030.pt`
- GPU: physical card 4, RTX 4090
- NVIDIA driver: `575.64.05`
- Runtime Python: `/home/hexinkun/miniconda3/envs/m1/bin/python`
- Algorithm source: `/home/hexinkun/amp/Go2Pvcnn`

## Key Metrics

- Historical premature exits: `22`; supervisor restarts: `23`.
- Python exit code on historical premature exits: always `0`.
- Python traceback/OOM/NaN/Inf: none observed.
- Stuck state: GPU utilization `0%`, about `9.6 GiB` retained, one CPU thread
  spinning, Kit already logged `Simulation App Shutting Down`.
- Minimal Vulkan probe: `VK_ERROR_INCOMPATIBLE_DRIVER (-9)` with
  `CUDA_VISIBLE_DEVICES=4` and with the variable unset.
- TDD covered physical-device argv, signal shutdown, process-group cleanup,
  single-instance locking, lineage isolation, corrupted checkpoint rejection,
  exact resume arithmetic, and atomic checkpoint replacement.
- Focused AME baseline regression with production `PYTHONPATH`: `30 passed`.
- Direct fixed-launcher resume: `3` updates, `model_1032 -> model_1034`, exit
  `0`, `Training Complete` present.
- Supervisor resume smoke: `4` updates, `model_1034 -> model_1037`, checkpoint
  progress detected, exit `0`, `TRAINING_COMPLETE` present.
- Multi-GPU-only A/B: `2` updates, `model_1037 -> model_1039`, exit `0`; Kit
  remained on Vulkan and no invalid DX12/default-plugin conflict was emitted.
- Final supervisor-v2 integration: exact `3` updates,
  `model_1040 -> model_1043`, exit `0`, checkpoint `next_iter=1044`, and
  `TRAINING_COMPLETE` present.

## Result

Pass for the application-level training and recovery contract. The launcher
uses a physical `cuda:N` index, disables renderer multi-GPU, and preserves
policy std on resume. The persistent supervisor records progress, premature
exit, and stalls; owns the complete process group; isolates and validates its
checkpoint lineage; and uses bounded TERM/KILL cleanup. AME saves are atomic
and resume starts at `next_iter`.

## Conclusion

The old behavior was not caused by the requested iteration count. The host
Vulkan ICD is broken, while the old launcher also mixed CUDA-remapped and Kit
physical GPU indices and left renderer multi-GPU enabled on an eight-card
host. That multi-GPU renderer path turned the otherwise tolerable Vulkan probe
failure into a native training exit. Isaac shutdowns could return `0` or
deadlock, which made the original supervisor repeatedly restart or block
indefinitely. Single-GPU renderer configuration plus the supervisor are
verified at 1024 envs, but the underlying host Vulkan installation still
requires an administrator repair.

## Follow-Up

- Run the persistent supervisor to checkpoint `model_9999.pt`.
- Repair the host NVIDIA Vulkan userspace and validate all eight GPUs with
  `vulkaninfo`; afterward test `DISABLE_RENDERER_MULTI_GPU=0` separately.
- Treat long-run reward/behavior quality as a separate result from this runtime
  stability smoke.

## Git Refs

- Baseline Ref: `55aa891`
- Candidate Ref: T306 working tree based on `55aa891`
- Key Files:
  - [M1 AME headless launcher](../../Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh)
  - [M1 AME supervisor](../../Go2Pvcnn/scripts/supervise_m1_ame_long_train.sh)
  - [launcher tests](../../Go2Pvcnn/tests/ame_baseline/test_m1_ame_long_train_launcher.py)
