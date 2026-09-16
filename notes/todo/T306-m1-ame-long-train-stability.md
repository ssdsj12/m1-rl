# T306 M1 AME Long-Train Stability

## Current State

The M1 AME 1024-environment run reached checkpoint `model_1030.pt`, then
entered repeated clean-looking exits and finally hung during Isaac Sim
shutdown. The Python process reported exit code `0` without traceback, OOM,
NaN, or Inf. The host Vulkan ICD independently fails a minimal
`vkCreateInstance` call with `VK_ERROR_INCOMPATIBLE_DRIVER`.

The single-GPU M1 launcher now avoids CUDA device remapping, disables Isaac
Sim renderer multi-GPU, selects physical `cuda:4`, and preserves policy noise
std on resume. Vulkan still initializes on Linux and reports the broken host
ICD, but a controlled 1024-env A/B proved that the two renderer multi-GPU
flags are sufficient for training to proceed without the invalid
`app.vulkan=false`/DX12 setting.

The supervisor now owns an isolated process group and checkpoint lineage,
uses a single-instance lock, validates checkpoint contents, and recovers a
five-minute checkpoint stall with bounded TERM/KILL cleanup. AME checkpoints
are atomically replaced and record `next_iter`, so resume no longer repeats
the last completed optimizer update. The final real 1024-env supervisor smoke
resumed `model_1040.pt`, performed exactly three updates, and completed at
`model_1043.pt` with exit code `0`.

The committed target-10000 run is active in `m1ame_supervisor`. Its first
attempt advanced from `model_1043.pt` through validated `model_1100.pt`
without restart or stall, exceeding the earlier approximately 50-update exit
window while preserving policy noise std.

## Open Children

- T306.1: repair the host NVIDIA graphics/Vulkan userspace installation with
  administrator access, then require `vulkaninfo` to enumerate all eight GPUs.
- T306.2: continue the supervised run to the 10000-update boundary and inspect
  long-horizon learning metrics rather than treating smoke stability as a
  behavior-quality result.

## Closed Children Archive

- Identified that the prior supervisor was not limited by `MAX_ITERATIONS`;
  all 22 premature runs stopped before `Training Complete`.
- Removed `CUDA_VISIBLE_DEVICES=4` / `cuda:0` ordinal mismatch from the M1
  launcher; physical GPU selection now uses `DEVICE=cuda:4`.
- Resume now keeps checkpoint policy std by default instead of resetting it to
  approximately `1.0` on every restart.
- Added a single-instance, process-group checkpoint-progress watchdog with
  bounded TERM/KILL cleanup and signal-safe shutdown.
- Added atomic AME checkpoint writes, strict metadata validation, isolated
  attempt lineage, and correct zero-based resume math.
- Verified the single-GPU launcher and supervisor against real 1024-env Isaac
  runs; the focused AME baseline suite is `30 passed`.

## Related Logs

- [2026-09-16 M1 AME long-train Vulkan/watchdog fix](../log/2026-09-16-m1-ame-long-train-vulkan-watchdog-fix.md)

## Git Refs

- Current Work Ref: `375e5f5`
- Last Feature Commit: `375e5f5`
- Last Verified Ref: `375e5f5`
- Key Files:
  - [M1 AME headless launcher](../../Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh)
  - [M1 AME long-train supervisor](../../Go2Pvcnn/scripts/supervise_m1_ame_long_train.sh)
  - [launcher regression](../../Go2Pvcnn/tests/ame_baseline/test_m1_ame_long_train_launcher.py)

## Next Step

Continue monitoring the active target-10000 supervisor to `model_9999.pt`,
and keep T306.1 open until an administrator repairs the system Vulkan ICD.

## Node Details

The supervisor interprets `TARGET_ITERATIONS=10000` with the runner's
zero-based iteration labels, so successful completion is checkpoint
`model_9999.pt`. It uses per-attempt logs and the cumulative supervisor log.
The default five-minute no-checkpoint window is comfortably above the current
ten-iteration checkpoint interval while still recovering shutdown deadlocks.
`model_N.pt` means update `N` is complete and `next_iter=N+1`; therefore the
10000-update run ends at `model_9999.pt` without replaying the checkpointed
iteration.
