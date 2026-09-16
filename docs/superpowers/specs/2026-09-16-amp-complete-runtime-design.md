# Complete AMP Runtime and Fresh 10000-Iteration Training Design

## Goal

Complete the existing Conda environment at `/home/hexinkun/miniconda3/envs/amp`, use that environment exclusively for M1 AME training, and start a fresh 1024-environment run on physical GPU 4 for 10000 updates. The accepted run starts at zero, uses one uninterrupted Python/Isaac Sim process, completes all 10000 configured updates, writes its final checkpoint, and exits normally.

## Confirmed current state

The prior training did not run in the requested AMP environment. Its process executable was:

```text
/home/hexinkun/miniconda3/envs/m1/bin/python
```

The `/home/hexinkun/amp/Go2Pvcnn` source tree was present on `PYTHONPATH`, but that did not change the active Python runtime.

The existing `amp` environment is Python 3.10 and approximately 964 MB. Direct import inspection shows that it currently lacks:

```text
torch
numpy
gymnasium
isaacsim
```

It therefore cannot run the requested training yet. The old `m1ame_supervisor` session has been stopped, and no hexinkun training process remains on the GPUs. Existing logs and checkpoints are preserved.

## Selected approach

Complete the existing environment in place instead of cloning the broken `m1` runtime or creating another environment name. Every install and verification command will explicitly use:

```text
/home/hexinkun/miniconda3/envs/amp/bin/python
```

The runtime will be pinned to the versions already required by the checked-out Isaac Lab tree and the M1 integration:

- Python 3.10;
- Isaac Sim `4.5.0.0` with `all` and `extscache` extras;
- Isaac Lab checkout `/home/hexinkun/IsaacLab45` at tag `v2.2.1`;
- PyTorch `2.7.0+cu128` and torchvision `0.22.0+cu128`;
- NumPy `1.26.4` and Gymnasium `1.2.0`;
- the local M1-RL project `/home/hexinkun/m1_rl/Go2Pvcnn`;
- the intended AMP/RSL-RL source required by the synthesized `m1_rl` branch.

Native GLVND libraries will be completed inside the AMP environment, including `libEGL.so.1`, `libglvnd`, `libopengl`, and `libglu`. This addresses the confirmed incomplete Vulkan dependency chain instead of inheriting the incomplete native libraries from `m1`.

## Dependency installation boundaries

Installation will be additive inside the existing `amp` prefix. It will not:

- delete or overwrite `/home/hexinkun/miniconda3/envs/m1`;
- remove old checkpoints or TensorBoard event files;
- change `/etc/vulkan`, the NVIDIA driver, CUDA kernel modules, or any system package;
- use `sudo`;
- install Isaac Sim 5.x;
- copy the entire `m1` environment into `amp`;
- resume `model_2090.pt` or any other old checkpoint.

Before installation, the current AMP Conda explicit package list and pip freeze output will be saved under `/home/hexinkun/m1_rl/run_logs/environment_snapshots/`. After installation, a second snapshot and `pip check` output will be recorded there for reproducibility.

## Source and import ownership

The launcher must no longer contain `/home/hexinkun/miniconda3/envs/m1` as its default `ISAAC_ENV`. It will default to:

```text
/home/hexinkun/miniconda3/envs/amp
```

The launched process must report and verify all of the following before training:

```text
sys.executable == /home/hexinkun/miniconda3/envs/amp/bin/python
isaacsim version == 4.5.0.0
torch version == 2.7.0+cu128
torch.cuda.is_available() == True
torch can allocate and synchronize a tensor on cuda:4
```

The `m1_rl` repository remains the training entrypoint and owns the synthesized M1 AME task. AMP/RSL-RL imports must resolve to the explicitly selected local source, not accidentally to a different site-packages release. Import origins will be printed and checked before the smoke test.

## Vulkan acceptance gate

A new environment is not considered complete merely because `pip install` succeeds. Before Isaac Sim smoke testing, the Isaac-bundled Vulkan loader must create and destroy a Vulkan instance successfully while the AMP environment's native library directory is active.

The gate fails if any of the following appear:

```text
VK_ERROR_INCOMPATIBLE_DRIVER
vkCreateInstance failed
Unable to get IGpuFoundation
```

If the completed GLVND/EGL dependency chain still cannot satisfy the system NVIDIA ICD, a project-local EGL ICD manifest pointing to `libEGL_nvidia.so.0` is the fallback. The fallback must pass the same create/destroy probe before any long training starts.

## Training sequence

Verification proceeds in increasing cost order:

1. dependency and import audit in the AMP environment;
2. `pip check` and exact interpreter/path assertions;
3. CUDA allocation and synchronization on physical GPU 4;
4. Vulkan create/destroy probe using Isaac Sim's bundled loader;
5. M1 AME 8-environment smoke test for at least two updates;
6. M1 AME 1024-environment short stability test that crosses the former deterministic early-exit duration without Vulkan or GPU Foundation errors;
7. one fresh 1024-environment, GPU4, 10000-iteration training process with no checkpoint resume and no automatic restart.

Smoke-test output goes to separate log directories and is never selected as a long-run checkpoint.

## Long-run launch contract

The accepted long run uses:

```text
environment: /home/hexinkun/miniconda3/envs/amp
repository: /home/hexinkun/m1_rl
num_envs: 1024
device: cuda:4
max_iterations: 10000
resume: false
checkpoint: unset
automatic restart: disabled
```

The launcher records the training Python PID, `sys.executable`, environment snapshot path, exact command, log directory, and Git commit. TensorBoard must point only to the newly created long-run directory.

## Final acceptance

Installation is complete only when all environment, import, CUDA, Vulkan, and smoke gates pass.

Training is complete only when the same training Python PID that starts at zero completes all 10000 configured updates, writes the final checkpoint, prints the normal completion marker, and exits with code 0. With the runner's zero-based counter this normally means updates `0..9999` and a terminal next-iteration value of `10000`; the acceptance check uses completed-update metadata rather than assuming that the log must print a line labelled `10000`. Crossing iteration 2100 or running for a fixed number of minutes is only an intermediate observation and is not final acceptance.

Any exit before completing all 10000 updates is a failed run. It must be recorded and diagnosed; it must not be hidden by a supervisor restart or by adding iterations from multiple processes.

## Rollback

Because the old `m1` environment, logs, and checkpoints remain untouched, rollback consists only of stopping the AMP run and reverting launcher/configuration commits. No old data is deleted. The incomplete pre-install AMP package snapshots remain available to reconstruct the prior prefix state if needed.
