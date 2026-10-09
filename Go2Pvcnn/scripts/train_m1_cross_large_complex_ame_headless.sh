#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
ISAAC_ENV="${ISAAC_ENV:-/home/hexinkun/miniconda3/envs/amp}"
PYTHON_BIN="${PYTHON_BIN:-${ISAAC_ENV}/bin/python}"
VULKAN_ICD_MANIFEST="${VULKAN_ICD_MANIFEST:-${REPO_ROOT}/Go2Pvcnn/config/vulkan/nvidia_egl_icd.json}"
VULKAN_PROBE="${VULKAN_PROBE:-${REPO_ROOT}/Go2Pvcnn/scripts/probe_isaac_vulkan.py}"

cd "${REPO_ROOT}"
printf 'TRAIN_REPO_ROOT=%s\n' "$(pwd -P)"

export PATH="${ISAAC_ENV}/bin:${PATH}"
export PYTHONUNBUFFERED=1
export DISPLAY="${DISPLAY:-:7}"
export M1_MPC_TEACHER_RATIO_START="${M1_MPC_TEACHER_RATIO_START:-1.0}"
export M1_MPC_TEACHER_RATIO_END="${M1_MPC_TEACHER_RATIO_END:-0.0}"
export M1_MPC_TEACHER_WARMUP_PCT="${M1_MPC_TEACHER_WARMUP_PCT:-0.10}"
export M1_MPC_TEACHER_DECAY_END_PCT="${M1_MPC_TEACHER_DECAY_END_PCT:-0.80}"
export PYTHONPATH="${REPO_ROOT}/Go2Pvcnn:${REPO_ROOT}/Go2Pvcnn/rsl_rl:/home/hexinkun/IsaacLab45/source/isaaclab:/home/hexinkun/IsaacLab45/source/isaaclab_rl:/home/hexinkun/IsaacLab45/source/isaaclab_tasks:/home/hexinkun/IsaacLab45/source/isaaclab_assets:${ISAAC_ENV}/lib/python3.10/site-packages"
export OMNI_KIT_ACCEPT_EULA="${OMNI_KIT_ACCEPT_EULA:-Y}"
export VK_DRIVER_FILES="${VULKAN_ICD_MANIFEST}"
export VK_ICD_FILENAMES="${VULKAN_ICD_MANIFEST}"
# Isaac Lab passes the physical device index to both CUDA and PhysX/Kit.  CUDA
# remapping makes those two index spaces disagree and is explicitly unsupported
# by Omniverse, so select the card with DEVICE=cuda:N instead.
unset CUDA_VISIBLE_DEVICES
export LD_LIBRARY_PATH="${ISAAC_ENV}/lib/python3.10/site-packages/torch/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cuda_nvrtc/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cudnn/lib:${ISAAC_ENV}/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cuda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64:${LD_LIBRARY_PATH:-}"

if [[ "${SKIP_VULKAN_PREFLIGHT:-0}" != "1" ]]; then
  "${PYTHON_BIN}" "${VULKAN_PROBE}" \
    --prefix "${ISAAC_ENV}" \
    --expect-device-count 8
fi
printf 'TRAIN_PROCESS_START pid=%s python=%s device=%s\n' \
  "$$" "${PYTHON_BIN}" "${DEVICE:-cuda:7}"

# Isaac Sim initializes Vulkan even in headless mode.  The project ICD above
# selects NVIDIA's EGL entry point, while disabling renderer multi-GPU keeps
# CUDA and PhysX on the explicitly requested physical device.
DISABLE_RENDERER_MULTI_GPU="${DISABLE_RENDERER_MULTI_GPU:-1}"
KIT_ARGS="${KIT_ARGS:-}"
if [[ "${DISABLE_RENDERER_MULTI_GPU}" == "1" ]]; then
  renderer_kit_args="--/renderer/multiGpu/enabled=false --/renderer/multiGpu/autoEnable=false"
  KIT_ARGS="${KIT_ARGS:+${KIT_ARGS} }${renderer_kit_args}"
fi

args=(
  "${TRAIN_ENTRYPOINT:-Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py}"
  --num_envs "${NUM_ENVS:-1024}"
  --max_iterations "${MAX_ITERATIONS:-10000}"
  --device "${DEVICE:-cuda:7}"
  --headless
)

if [[ -n "${KIT_ARGS}" ]]; then
  args+=(--kit_args "${KIT_ARGS}")
fi

if [[ -n "${CHECKPOINT:-}" ]]; then
  args+=(--resume --checkpoint "${CHECKPOINT}")
  if [[ "${KEEP_STD:-1}" == "1" ]]; then
    args+=(--keep_std)
  fi
fi

exec "${PYTHON_BIN}" "${args[@]}"
