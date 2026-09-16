# Isaac Sim Headless Vulkan ICD Stability Design

> Superseded on 2026-09-16 by `2026-09-16-amp-complete-runtime-design.md` after the user required training to run exclusively from the completed `amp` Conda environment and to start a fresh 10000-update run. This document is retained only as root-cause evidence.

## Goal

Run the M1 AME 1024-environment training in one Isaac Sim process from the latest valid checkpoint through iteration 10000, then let the program exit normally. Any exit before iteration 10000 is a failed run; supervisor restart/resume loops are not an acceptable completion mechanism.

## Confirmed failure

The current training repeatedly resumes from `model_2090.pt`, completes iterations 2091 through 2099, and exits during the iteration-2100 rollout. The process exits through Kit's native quick-shutdown path with code 0 and logs:

```text
PhysXFoundation: Calling createGpuFoundation without first releasing...
VkResult: ERROR_INCOMPATIBLE_DRIVER
vkCreateInstance failed
Unable to get IGpuFoundation
```

There is no Python traceback, CUDA out-of-memory error, NaN/Inf report, supervisor watchdog kill, or host-memory pressure.

## Root cause evidence

The server is a headless Ubuntu host. Its only system Vulkan ICD manifest, `/etc/vulkan/icd.d/nvidia_icd.json`, selects `libGLX_nvidia.so.0`.

Using Isaac Sim 4.5's bundled Vulkan loader:

- the system GLX ICD fails `vkCreateInstance` with `VK_ERROR_INCOMPATIBLE_DRIVER` (`-9`);
- `libGLX_nvidia.so.0` fails loader/driver interface negotiation and returns no `vkCreateInstance` procedure;
- the same installed NVIDIA driver's `libEGL_nvidia.so.0` negotiates interface version 7 and creates a Vulkan instance successfully.

The NVIDIA 575 driver documentation states that the EGL NVIDIA library can be used as the Vulkan ICD and is the appropriate alternative for environments without X11 client operation.

## Selected design

Add a project-scoped Vulkan ICD manifest for headless execution:

```json
{
  "file_format_version": "1.0.1",
  "ICD": {
    "library_path": "libEGL_nvidia.so.0",
    "api_version": "1.4.303"
  }
}
```

The long-training launcher will resolve this manifest to an absolute path and export both compatibility variables for the child Isaac process:

```text
VK_DRIVER_FILES=<absolute manifest path>
VK_ICD_FILENAMES=<absolute manifest path>
```

The override is process-local. It will not edit `/etc/vulkan`, replace the NVIDIA driver, require sudo, or affect other users.

Only the ICD selection changes in the first experiment. The checkpoint, seed (`42`), environment count (`1024`), device (`cuda:4`), algorithm configuration, and save interval remain unchanged. Keeping the previously failing deterministic trajectory makes the test causal.

## Implementation boundaries

The implementation will:

1. add the headless NVIDIA EGL ICD manifest under the project;
2. add a reusable Vulkan probe that returns nonzero when Isaac's bundled loader cannot create an instance;
3. make the launcher export the project ICD path to the training process and provide a one-shot mode with automatic restart disabled;
4. add automated static/unit coverage for manifest content and environment propagation;
5. launch only the 1024-env training from the latest validated checkpoint in one-shot mode.

The implementation will not:

- modify the host NVIDIA driver or system ICD files;
- change checkpoint frequency to hide exits;
- change the random seed in the first experiment;
- delete prior logs or checkpoints;
- re-enable the 2048-env job;
- combine the separate all-GPU-context optimization with this root-cause test.

## Verification

Verification is staged and evidence-based:

1. **Red probe:** with the system GLX ICD, Isaac's bundled Vulkan loader must reproduce return code `-9`.
2. **Green probe:** with the project EGL ICD override, the same loader must return `0` and destroy the instance cleanly.
3. **Command verification:** the launched training process environment must contain the absolute project ICD path.
4. **Regression tests:** targeted supervisor/manifest tests and the existing M1 AME test suite must pass.
5. **Known-failure boundary check:** the resumed process must first complete iteration 2100 and write a checkpoint newer than `model_2090.pt` without a restart. This is an early diagnostic milestone only, not final acceptance.
6. **Continuous-run check:** automatic restart must remain disabled, the PID must stay unchanged, iterations/checkpoints must continue increasing, and no `EARLY_TERMINATION`, `ERROR_INCOMPATIBLE_DRIVER`, or premature `Simulation App Shutting Down` marker may appear.
7. **Final acceptance:** that same PID must reach iteration 10000, write the final checkpoint, and then exit normally with exit code `0`. No replacement training PID, resume attempt, or supervisor restart may contribute iterations to this accepted run.

Crossing iteration 2100 only shows that the previously deterministic failure point has been cleared. It does not prove the bug fixed. The repair is complete only after the same uninterrupted process reaches iteration 10000 and exits normally.

## Failure handling

If the EGL probe succeeds but training exits at any point before iteration 10000, mark the run as failed and preserve its logs; do not hide the failure by automatically restarting. If it still fails at the deterministic iteration-2100 boundary, the next experiment changes only the seed from 42 to 43 for 20 updates to distinguish a deterministic environment/PhysX trajectory fault from the Vulkan loader fault.

If the EGL probe itself fails, do not restart long training. Report the exact loader diagnostics; the remaining repair requires an administrator-level NVIDIA Vulkan/driver correction.

## Rollback

Rollback removes the process-local ICD environment variables and restarts from the last validated checkpoint. The project manifest is inert unless explicitly selected. No checkpoint or training data needs to be converted.
