# M1 reference amp Vulkan recheck

## Purpose / Stage / Todo

Read-only runtime prerequisite for [T306.6h](../todo/T306-m1-ame-long-train-stability.md). Reuse current validated project ICD and amp libraries before reference-controller startup. No driver/environment changes.

## Command / Inputs

In projectroot, `PYTHONDONTWRITEBYTECODE=1`, both `VK_DRIVER_FILES` and `VK_ICD_FILENAMES` point to `Go2Pvcnn/config/vulkan/nvidia_egl_icd.json`. Run amp python `Go2Pvcnn/scripts/probe_isaac_vulkan.py --prefix /home/hexinkun/miniconda3/envs/amp --expect-device-count 8`.

## Metrics / Result

Exit0. Loader is amp's isaacsim/extscache/omni.gpu_foundation-0.0.0+d02c707b.lx64.r.cp310/bin/deps/libvulkan.so.1. `vkCreateInstance=0`, `physical_device_count=8`.

## Conclusion / Follow-up

Current ICD initialization prerequisite passes; historical incompatible-driver failure did not reproduce in this check. Not evidence for long simulation completion or physical obstacle crossing. Continue new8-env adapter gate, no automaticrestart or10000training.

## Git Refs

BaselineRef88888f7 pluspreservedwork; no productioncode changes. Keyfile [existingprobe](../../Go2Pvcnn/scripts/probe_isaac_vulkan.py). Linkedfrom[mainpreflight](2026-09-18-m1-reference-preflight.md).
