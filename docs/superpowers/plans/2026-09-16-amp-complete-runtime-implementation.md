# Complete AMP Runtime and Fresh 10000-Update Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `/home/hexinkun/miniconda3/envs/amp`, prove that CUDA and Isaac's Vulkan loader work from that prefix, and launch one fresh uninterrupted 1024-environment M1 AME run for 10000 updates on GPU4.

**Architecture:** A reproducible setup script pins the AMP runtime and installs the checked-out Isaac Lab and merged `m1_rl` sources. A project-local EGL ICD manifest plus a small Vulkan probe forms a hard preflight gate. The existing headless launcher defaults to AMP, and a separate one-shot wrapper starts exactly one non-resume training process with no supervisor restart loop.

**Tech Stack:** Bash, Conda, Python 3.10, PyTorch 2.7/CUDA 12.8, Isaac Sim 4.5, Isaac Lab 2.2.1, ctypes/Vulkan, pytest, tmux, TensorBoard.

---

## File map

- Create `Go2Pvcnn/scripts/setup_amp_runtime.sh`: snapshot and complete the existing AMP Conda prefix with pinned packages and local editable sources.
- Create `Go2Pvcnn/config/vulkan/nvidia_egl_icd.json`: project-scoped NVIDIA EGL Vulkan ICD selection.
- Create `Go2Pvcnn/scripts/probe_isaac_vulkan.py`: locate Isaac's bundled loader, create/destroy an instance, and verify eight physical devices.
- Modify `Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh`: default to AMP, export the EGL ICD, run preflight, and print the actual training PID/interpreter.
- Create `Go2Pvcnn/scripts/run_m1_ame_10000_once.sh`: enforce fresh 1024-env/GPU4/10000-update one-shot launch without resume or restart.
- Modify `Go2Pvcnn/tests/ame_baseline/test_m1_ame_long_train_launcher.py`: cover AMP interpreter selection and the one-shot contract.
- Create `Go2Pvcnn/tests/test_isaac_vulkan_probe.py`: cover manifest, loader resolution, and Vulkan probe control flow.
- Create `Go2Pvcnn/tests/test_amp_runtime_setup.py`: cover pinned setup commands and local source ownership.
- Runtime artifacts only: `run_logs/environment_snapshots/*`, `run_logs/m1_ame_amp_10000.log`, and a new long-run directory under `logs/rsl_rl/m1_cross_large_complex_ame/`.

### Task 1: Add the reproducible AMP runtime setup

**Files:**
- Create: `Go2Pvcnn/tests/test_amp_runtime_setup.py`
- Create: `Go2Pvcnn/scripts/setup_amp_runtime.sh`

- [ ] **Step 1: Write the failing setup-contract test**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "scripts/setup_amp_runtime.sh"


def test_amp_setup_pins_the_complete_runtime_and_merged_sources():
    source = SETUP.read_text()
    assert 'AMP_PREFIX="${AMP_PREFIX:-/home/hexinkun/miniconda3/envs/amp}"' in source
    assert 'python=3.10' in source
    assert 'gcc_linux-64' in source
    assert 'gxx_linux-64' in source
    assert 'libegl=1.7.0' in source
    assert 'libglvnd=1.7.0' in source
    assert 'torch==2.7.0' in source
    assert 'torchvision==0.22.0' in source
    assert 'isaacsim[all,extscache]==4.5.0.0' in source
    assert 'numpy==1.26.4' in source
    assert 'gymnasium==1.2.0' in source
    assert 'warp-lang==1.17.0' in source
    assert 'pillow==11.2.1' in source
    assert '/home/hexinkun/IsaacLab45' in source
    assert '${REPO_ROOT}/Go2Pvcnn/rsl_rl' in source
    assert '${REPO_ROOT}/Go2Pvcnn' in source
    assert '/home/hexinkun/miniconda3/envs/m1' not in source
```

- [ ] **Step 2: Run the test and confirm the missing-script failure**

Run:

```bash
cd /home/hexinkun/m1_rl/Go2Pvcnn
/home/hexinkun/miniconda3/envs/m1/bin/python -m pytest tests/test_amp_runtime_setup.py -q
```

Expected: FAIL because `scripts/setup_amp_runtime.sh` does not exist.

- [ ] **Step 3: Implement the setup script**

The script must use explicit binaries and fail on the first installation error:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/hexinkun/m1_rl}"
AMP_PREFIX="${AMP_PREFIX:-/home/hexinkun/miniconda3/envs/amp}"
CONDA_BIN="${CONDA_BIN:-/home/hexinkun/miniconda3/bin/conda}"
ISAACLAB_ROOT="${ISAACLAB_ROOT:-/home/hexinkun/IsaacLab45}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-${REPO_ROOT}/run_logs/environment_snapshots}"
STAMP="$(date +%Y%m%d_%H%M%S)"
PYTHON_BIN="${AMP_PREFIX}/bin/python"

mkdir -p -- "${SNAPSHOT_DIR}"
"${CONDA_BIN}" list -p "${AMP_PREFIX}" --explicit > "${SNAPSHOT_DIR}/amp_before_${STAMP}.conda.txt"
"${PYTHON_BIN}" -m pip freeze --all > "${SNAPSHOT_DIR}/amp_before_${STAMP}.pip.txt"

"${CONDA_BIN}" install -p "${AMP_PREFIX}" -y -c conda-forge \
  python=3.10 cmake make gcc_linux-64 gxx_linux-64 \
  "libegl=1.7.0" "libglvnd=1.7.0" \
  "libopengl=1.7.0" "libglu=9.0.3"
"${PYTHON_BIN}" -m pip install --upgrade "pip<27" "setuptools<81" wheel
"${PYTHON_BIN}" -m pip install \
  torch==2.7.0 torchvision==0.22.0 \
  --index-url https://download.pytorch.org/whl/cu128
"${PYTHON_BIN}" -m pip install \
  "isaacsim[all,extscache]==4.5.0.0" \
  --extra-index-url https://pypi.nvidia.com
"${PYTHON_BIN}" -m pip install \
  numpy==1.26.4 gymnasium==1.2.0 warp-lang==1.17.0 pillow==11.2.1

for package in isaaclab isaaclab_assets isaaclab_tasks isaaclab_rl isaaclab_mimic; do
  "${PYTHON_BIN}" -m pip install -e "${ISAACLAB_ROOT}/source/${package}"
done
"${PYTHON_BIN}" -m pip install -e "${REPO_ROOT}/Go2Pvcnn/rsl_rl"
"${PYTHON_BIN}" -m pip install -e "${REPO_ROOT}/Go2Pvcnn"

env -u PYTHONPATH -u CUDA_VISIBLE_DEVICES "${PYTHON_BIN}" -m pip check \
  | tee "${SNAPSHOT_DIR}/amp_after_${STAMP}.pip-check.txt"
"${CONDA_BIN}" list -p "${AMP_PREFIX}" --explicit > "${SNAPSHOT_DIR}/amp_after_${STAMP}.conda.txt"
"${PYTHON_BIN}" -m pip freeze --all > "${SNAPSHOT_DIR}/amp_after_${STAMP}.pip.txt"
```

Do not install the `isaaclab_rl[rsl_rl]` extra; the merged repository's local `rsl_rl` must own that import.

- [ ] **Step 4: Run the setup-contract test**

Run the Step 2 command again. Expected: `1 passed`.

- [ ] **Step 5: Commit the setup script and test**

```bash
git add Go2Pvcnn/scripts/setup_amp_runtime.sh Go2Pvcnn/tests/test_amp_runtime_setup.py
git commit -m "build: add reproducible AMP runtime setup"
```

### Task 2: Add the project EGL ICD and Vulkan preflight probe

**Files:**
- Create: `Go2Pvcnn/config/vulkan/nvidia_egl_icd.json`
- Create: `Go2Pvcnn/scripts/probe_isaac_vulkan.py`
- Create: `Go2Pvcnn/tests/test_isaac_vulkan_probe.py`

- [ ] **Step 1: Write failing tests for the manifest and probe helpers**

```python
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/vulkan/nvidia_egl_icd.json"
PROBE = ROOT / "scripts/probe_isaac_vulkan.py"


def _load_probe():
    spec = importlib.util.spec_from_file_location("probe_isaac_vulkan", PROBE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_manifest_selects_the_headless_nvidia_egl_icd():
    payload = json.loads(MANIFEST.read_text())
    assert payload == {
        "file_format_version": "1.0.1",
        "ICD": {"library_path": "libEGL_nvidia.so.0", "api_version": "1.4.303"},
    }


def test_resolve_loader_requires_exactly_one_isaac_gpu_foundation_loader(tmp_path):
    probe = _load_probe()
    loader = tmp_path / "lib/python3.10/site-packages/isaacsim/extscache/omni.gpu_foundation-x/bin/deps/libvulkan.so.1"
    loader.parent.mkdir(parents=True)
    loader.touch()
    assert probe.resolve_loader(tmp_path) == loader
    second = tmp_path / "lib/python3.10/site-packages/isaacsim/extscache/omni.gpu_foundation-y/bin/deps/libvulkan.so.1"
    second.parent.mkdir(parents=True)
    second.touch()
    with pytest.raises(RuntimeError, match="exactly one"):
        probe.resolve_loader(tmp_path)
```

- [ ] **Step 2: Run the tests and confirm both missing-artifact failures**

```bash
cd /home/hexinkun/m1_rl/Go2Pvcnn
/home/hexinkun/miniconda3/envs/m1/bin/python -m pytest tests/test_isaac_vulkan_probe.py -q
```

Expected: FAIL because the manifest and probe do not exist.

- [ ] **Step 3: Add the EGL manifest**

```json
{
  "file_format_version": "1.0.1",
  "ICD": {
    "library_path": "libEGL_nvidia.so.0",
    "api_version": "1.4.303"
  }
}
```

- [ ] **Step 4: Implement the probe with these public functions and CLI contract**

`resolve_loader(prefix: Path) -> Path` must glob only:

```python
pattern = "lib/python3.10/site-packages/isaacsim/extscache/omni.gpu_foundation-*/bin/deps/libvulkan.so.1"
```

and raise unless exactly one loader exists. `probe_vulkan(loader: Path) -> int` must use `ctypes` to call `vkCreateInstance`, `vkEnumeratePhysicalDevices`, and `vkDestroyInstance`; it returns the physical-device count and always destroys a successfully created instance. The CLI accepts:

```text
--prefix PATH
--loader PATH
--expect-device-count INTEGER
```

It prints all three machine-readable lines and exits nonzero on any mismatch:

```text
loader=<absolute path>
vkCreateInstance=0
physical_device_count=8
```

- [ ] **Step 5: Run the probe unit tests**

Run the Step 2 command again. Expected: all tests PASS.

- [ ] **Step 6: Commit the manifest, probe, and tests**

```bash
git add Go2Pvcnn/config/vulkan/nvidia_egl_icd.json Go2Pvcnn/scripts/probe_isaac_vulkan.py Go2Pvcnn/tests/test_isaac_vulkan_probe.py
git commit -m "fix: add Isaac headless Vulkan preflight"
```

### Task 3: Make the headless launcher use AMP and fail closed on Vulkan

**Files:**
- Modify: `Go2Pvcnn/tests/ame_baseline/test_m1_ame_long_train_launcher.py`
- Modify: `Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh`

- [ ] **Step 1: Extend the launcher test to capture interpreter and ICD environment**

Update the fake Python in `test_headless_launcher_builds_physical_cuda4_compute_only_argv` so the preflight call succeeds and the training call records:

```bash
printf 'PYTHON=%s\n' "$0"
printf 'VK_DRIVER_FILES=%s\n' "${VK_DRIVER_FILES-unset}"
printf 'VK_ICD_FILENAMES=%s\n' "${VK_ICD_FILENAMES-unset}"
printf 'CUDA_VISIBLE_DEVICES=%s\n' "${CUDA_VISIBLE_DEVICES-unset}"
printf '%s\n' "$@"
```

Add static assertions:

```python
source = LAUNCHER.read_text()
assert 'ISAAC_ENV="${ISAAC_ENV:-/home/hexinkun/miniconda3/envs/amp}"' in source
assert 'VULKAN_ICD_MANIFEST="${VULKAN_ICD_MANIFEST:-${REPO_ROOT}/Go2Pvcnn/config/vulkan/nvidia_egl_icd.json}"' in source
assert 'export VK_DRIVER_FILES="${VULKAN_ICD_MANIFEST}"' in source
assert 'export VK_ICD_FILENAMES="${VULKAN_ICD_MANIFEST}"' in source
assert "probe_isaac_vulkan.py" in source
assert "/envs/m1" not in source
```

- [ ] **Step 2: Run the targeted launcher test and confirm it fails**

```bash
cd /home/hexinkun/m1_rl/Go2Pvcnn
/home/hexinkun/miniconda3/envs/m1/bin/python -m pytest \
  tests/ame_baseline/test_m1_ame_long_train_launcher.py::test_headless_launcher_builds_physical_cuda4_compute_only_argv -q
```

Expected: FAIL on the missing AMP/ICD assertions.

- [ ] **Step 3: Modify the launcher**

At the top of the launcher use:

```bash
ISAAC_ENV="${ISAAC_ENV:-/home/hexinkun/miniconda3/envs/amp}"
PYTHON_BIN="${PYTHON_BIN:-${ISAAC_ENV}/bin/python}"
VULKAN_ICD_MANIFEST="${VULKAN_ICD_MANIFEST:-${REPO_ROOT}/Go2Pvcnn/config/vulkan/nvidia_egl_icd.json}"
VULKAN_PROBE="${VULKAN_PROBE:-${REPO_ROOT}/Go2Pvcnn/scripts/probe_isaac_vulkan.py}"

export VK_DRIVER_FILES="${VULKAN_ICD_MANIFEST}"
export VK_ICD_FILENAMES="${VULKAN_ICD_MANIFEST}"
```

Remove old `m1` environment paths from `PYTHONPATH`. Keep only the merged repository, Isaac Lab source trees, and `${ISAAC_ENV}` site-packages. Before constructing training arguments, run:

```bash
if [[ "${SKIP_VULKAN_PREFLIGHT:-0}" != "1" ]]; then
  "${PYTHON_BIN}" "${VULKAN_PROBE}" --prefix "${ISAAC_ENV}" --expect-device-count 8
fi
printf 'TRAIN_PROCESS_START pid=%s python=%s device=%s\n' "$$" "${PYTHON_BIN}" "${DEVICE:-cuda:4}"
```

Leave `exec "${PYTHON_BIN}" "${args[@]}"` as the last command so the printed PID becomes the Python PID.

- [ ] **Step 4: Run all launcher tests**

```bash
/home/hexinkun/miniconda3/envs/m1/bin/python -m pytest tests/ame_baseline/test_m1_ame_long_train_launcher.py -q
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the launcher migration**

```bash
git add Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh Go2Pvcnn/tests/ame_baseline/test_m1_ame_long_train_launcher.py
git commit -m "fix: run M1 AME from the AMP environment"
```

### Task 4: Add a one-shot fresh 10000-update launcher

**Files:**
- Create: `Go2Pvcnn/scripts/run_m1_ame_10000_once.sh`
- Modify: `Go2Pvcnn/tests/ame_baseline/test_m1_ame_long_train_launcher.py`

- [ ] **Step 1: Write a failing one-shot contract test**

Use a fake `TRAIN_LAUNCHER` that writes its environment and increments a counter. Assert:

```python
assert result.returncode == 0
assert launch_count.read_text().splitlines() == ["1"]
assert captured["NUM_ENVS"] == "1024"
assert captured["MAX_ITERATIONS"] == "10000"
assert captured["DEVICE"] == "cuda:4"
assert captured["CHECKPOINT"] == ""
```

Also assert the script contains one `exec` and does not reference `supervise_m1_ame_long_train.sh`, `RESTART_DELAY_SECONDS`, or `--resume`.

- [ ] **Step 2: Run the new test and confirm the missing-script failure**

```bash
/home/hexinkun/miniconda3/envs/m1/bin/python -m pytest \
  tests/ame_baseline/test_m1_ame_long_train_launcher.py -k one_shot -q
```

Expected: FAIL because the one-shot script does not exist.

- [ ] **Step 3: Implement the one-shot wrapper**

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/hexinkun/m1_rl}"
TRAIN_LAUNCHER="${TRAIN_LAUNCHER:-${REPO_ROOT}/Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh}"

cd "${REPO_ROOT}"
exec env \
  NUM_ENVS="${NUM_ENVS:-1024}" \
  MAX_ITERATIONS="${MAX_ITERATIONS:-10000}" \
  DEVICE="${DEVICE:-cuda:4}" \
  SAVE_INTERVAL="${SAVE_INTERVAL:-10}" \
  KEEP_STD="${KEEP_STD:-1}" \
  CHECKPOINT= \
  "${TRAIN_LAUNCHER}"
```

- [ ] **Step 4: Run the one-shot test and launcher suite**

```bash
/home/hexinkun/miniconda3/envs/m1/bin/python -m pytest tests/ame_baseline/test_m1_ame_long_train_launcher.py -q
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the one-shot launcher**

```bash
git add Go2Pvcnn/scripts/run_m1_ame_10000_once.sh Go2Pvcnn/tests/ame_baseline/test_m1_ame_long_train_launcher.py
git commit -m "feat: add one-shot M1 AME long training"
```

### Task 5: Install and verify the completed AMP runtime

**Files:**
- Runtime output: `run_logs/environment_snapshots/*`

- [ ] **Step 1: Verify no old training process is active**

```bash
pgrep -af 'supervise_m1_ame|train_m1_cross_large_complex_ame' || true
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
```

Expected: no hexinkun M1 training process.

- [ ] **Step 2: Execute the setup script**

```bash
cd /home/hexinkun/m1_rl
bash Go2Pvcnn/scripts/setup_amp_runtime.sh 2>&1 | tee run_logs/setup_amp_runtime_$(date +%Y%m%d_%H%M%S).log
```

Expected: exit 0 and final `pip check` reports `No broken requirements found.`

- [ ] **Step 3: Verify interpreter, versions, import ownership, CUDA, and absence of CUDA 13 wheels**

```bash
env -u PYTHONPATH -u CUDA_VISIBLE_DEVICES \
  /home/hexinkun/miniconda3/envs/amp/bin/python - <<'PY'
import importlib.metadata as md
import pathlib
import sys
import torch
import isaaclab
import rsl_rl

expected = pathlib.Path('/home/hexinkun/miniconda3/envs/amp/bin/python').resolve()
assert pathlib.Path(sys.executable).resolve() == expected
assert md.version('isaacsim') == '4.5.0.0'
assert torch.__version__ == '2.7.0+cu128'
assert md.version('torchvision') == '0.22.0+cu128'
assert torch.cuda.is_available()
assert '/home/hexinkun/m1_rl/Go2Pvcnn/rsl_rl' in str(pathlib.Path(rsl_rl.__file__).resolve())
x = torch.ones(1, device='cuda:4')
torch.cuda.synchronize(4)
print('python=', sys.executable)
print('isaaclab=', isaaclab.__file__)
print('rsl_rl=', rsl_rl.__file__)
print('cuda4=', x.item(), torch.cuda.get_device_name(4))
PY
/home/hexinkun/miniconda3/envs/amp/bin/python -m pip freeze | grep -Ei '^nvidia-.*-cu13' && exit 1 || true
```

Expected: all assertions pass, GPU name is RTX 4090, and no CUDA 13 packages are printed.

- [ ] **Step 4: Record the system-ICD baseline without the project override**

```bash
env -u VK_DRIVER_FILES -u VK_ICD_FILENAMES \
  /home/hexinkun/miniconda3/envs/amp/bin/python \
  Go2Pvcnn/scripts/probe_isaac_vulkan.py \
  --prefix /home/hexinkun/miniconda3/envs/amp --expect-device-count 8
```

The previously observed result is `vkCreateInstance=-9`. Record the actual result after installing `libEGL`; this baseline is diagnostic and does not replace the mandatory project-ICD gate. A nonzero exit here must not stop the plan.

- [ ] **Step 5: Prove the project EGL override is green**

```bash
ICD=/home/hexinkun/m1_rl/Go2Pvcnn/config/vulkan/nvidia_egl_icd.json
VK_DRIVER_FILES="$ICD" VK_ICD_FILENAMES="$ICD" \
  /home/hexinkun/miniconda3/envs/amp/bin/python \
  Go2Pvcnn/scripts/probe_isaac_vulkan.py \
  --prefix /home/hexinkun/miniconda3/envs/amp --expect-device-count 8
```

Expected: `vkCreateInstance=0`, `physical_device_count=8`, exit 0.

### Task 6: Run regression and staged Isaac training gates

**Files:**
- Runtime logs only under `run_logs/` and new smoke run directories.

- [ ] **Step 1: Run targeted tests with AMP Python**

```bash
cd /home/hexinkun/m1_rl/Go2Pvcnn
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest \
  tests/test_amp_runtime_setup.py \
  tests/test_isaac_vulkan_probe.py \
  tests/ame_baseline/test_m1_ame_long_train_launcher.py -q
```

Expected: all targeted tests PASS.

- [ ] **Step 2: Run the existing M1 AME regression suite**

```bash
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest \
  tests/test_ame_entrypoints_static.py \
  tests/test_ame_observations.py \
  tests/test_ame_vec_env_and_cfg.py \
  tests/test_m1_ame_config_static.py \
  tests/test_m1_parallelism_rl_adapter.py \
  tests/ame_baseline -q
```

Expected: PASS with no import from the `m1` environment.

- [ ] **Step 3: Run a fresh 8-env, two-update Isaac smoke**

```bash
cd /home/hexinkun/m1_rl
env NUM_ENVS=8 MAX_ITERATIONS=2 DEVICE=cuda:4 CHECKPOINT= \
  ./Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh \
  2>&1 | tee run_logs/m1_ame_amp_8env_smoke.log
```

Expected: two completed updates, normal completion, and no Vulkan/GPU Foundation error markers.

- [ ] **Step 4: Run a fresh 1024-env, 20-update stability gate**

```bash
env NUM_ENVS=1024 MAX_ITERATIONS=20 DEVICE=cuda:4 CHECKPOINT= \
  ./Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh \
  2>&1 | tee run_logs/m1_ame_amp_1024env_20update_gate.log
```

Expected: all 20 updates in one PID and normal exit. Reject the gate if the log contains `ERROR_INCOMPATIBLE_DRIVER`, `vkCreateInstance failed`, `Unable to get IGpuFoundation`, `EARLY_TERMINATION`, or an unplanned shutdown.

### Task 7: Start and monitor the one-shot 10000-update run

**Files:**
- Runtime log: `run_logs/m1_ame_amp_10000.log`
- Runtime run directory: discovered from the emitted `[AME] log_dir=...` line.

- [ ] **Step 1: Record the pre-launch state and start one tmux session**

```bash
cd /home/hexinkun/m1_rl
test -z "$(pgrep -u hexinkun -f '[t]rain_m1_cross_large_complex_ame.py' || true)"
rm -f run_logs/m1_ame_amp_10000.log
tmux new-session -d -s m1ame_amp_10000 \
  'cd /home/hexinkun/m1_rl && bash -o pipefail -c '\''./Go2Pvcnn/scripts/run_m1_ame_10000_once.sh 2>&1 | tee /home/hexinkun/m1_rl/run_logs/m1_ame_amp_10000.log; rc=${PIPESTATUS[0]}; printf "LONG_RUN_EXIT_CODE=%s\n" "$rc" | tee -a /home/hexinkun/m1_rl/run_logs/m1_ame_amp_10000.log; exit "$rc"'\'''
```

The explicit `rm` is limited to the known new log path and must not touch any checkpoint or prior event file.

- [ ] **Step 2: Verify one AMP Python process, no resume argument, and the EGL environment**

```bash
pid=$(pgrep -u hexinkun -n -f '/home/hexinkun/miniconda3/envs/amp/bin/python[[:space:]]+Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py')
ps -p "$pid" -o pid=,ppid=,pgid=,sid=,etime=,stat=,args=
tr '\0' '\n' < "/proc/$pid/environ" | grep -E '^(VK_DRIVER_FILES|VK_ICD_FILENAMES)='
ps -p "$pid" -o args= | grep -- '--num_envs 1024'
ps -p "$pid" -o args= | grep -- '--max_iterations 10000'
if ps -p "$pid" -o args= | grep -q -- '--resume'; then exit 1; fi
```

Expected: exactly one matching training PID, executable under `envs/amp`, both ICD variables point to the project manifest, and no `--resume`.

- [ ] **Step 3: Point TensorBoard only at the new run**

```bash
run_dir=$(sed -n 's/^\[AME\] log_dir=//p' run_logs/m1_ame_amp_10000.log | tail -n 1)
test -n "$run_dir" && test -d "$run_dir"
tmux kill-session -t m1ame_tensorboard 2>/dev/null || true
tmux new-session -d -s m1ame_tensorboard \
  "/home/hexinkun/miniconda3/envs/amp/bin/tensorboard --logdir '$run_dir' --host 127.0.0.1 --port 6007"
```

- [ ] **Step 4: Monitor without restarting**

```bash
tail -F /home/hexinkun/m1_rl/run_logs/m1_ame_amp_10000.log \
  | grep --line-buffered -E 'TRAIN_PROCESS_START|Learning iteration|Total timesteps|Computation:|Mean reward|Training Complete|Traceback|ERROR_INCOMPATIBLE_DRIVER|vkCreateInstance failed|Unable to get IGpuFoundation|NaN|Inf'
```

If the PID exits before all 10000 updates, record the exit as failure and diagnose it. Do not start a replacement process.

- [ ] **Step 5: Perform final acceptance after normal completion**

Verify all of the following from the one run directory and master log:

```text
the initial TRAIN_PROCESS_START PID never changed
10000 updates completed (zero-based updates 0..9999)
the terminal checkpoint metadata has next_iter=10000
the normal completion marker is present
the tmux command exited with code 0
no Vulkan/GPU Foundation fatal marker is present
no second training process contributed progress
```

Record the final run directory, checkpoint path, PID, wall time, and TensorBoard command in the delivery message.
