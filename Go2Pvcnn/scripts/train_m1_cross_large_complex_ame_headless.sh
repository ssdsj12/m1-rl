#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/hexinkun/m1_rl}"
ISAAC_ENV="${ISAAC_ENV:-/home/hexinkun/miniconda3/envs/m1}"
PYTHON_BIN="${PYTHON_BIN:-${ISAAC_ENV}/bin/python}"

cd "${REPO_ROOT}"

export PATH="${ISAAC_ENV}/bin:${PATH}"
export PYTHONPATH="${REPO_ROOT}/Go2Pvcnn:/home/hexinkun/amp/Go2Pvcnn:/home/hexinkun/amp/Go2Pvcnn/rsl_rl:/home/hexinkun/IsaacLab45/source/isaaclab:/home/hexinkun/IsaacLab45/source/isaaclab_rl:/home/hexinkun/IsaacLab45/source/isaaclab_tasks:/home/hexinkun/IsaacLab45/source/isaaclab_assets:${ISAAC_ENV}/lib/python3.10/site-packages:${PYTHONPATH:-}"
export OMNI_KIT_ACCEPT_EULA="${OMNI_KIT_ACCEPT_EULA:-Y}"
# Isaac Lab passes the physical device index to both CUDA and PhysX/Kit.  CUDA
# remapping makes those two index spaces disagree and is explicitly unsupported
# by Omniverse, so select the card with DEVICE=cuda:N instead.
unset CUDA_VISIBLE_DEVICES
export LD_LIBRARY_PATH="${ISAAC_ENV}/lib/python3.10/site-packages/torch/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cuda_nvrtc/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cudnn/lib:${ISAAC_ENV}/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cuda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64:${LD_LIBRARY_PATH:-}"

# Isaac Sim still initializes Vulkan on Linux, so the host ICD must ultimately
# be repaired by an administrator.  Disabling renderer multi-GPU avoids the
# unstable cross-device renderer path while preserving CUDA/PhysX on DEVICE.
DISABLE_RENDERER_MULTI_GPU="${DISABLE_RENDERER_MULTI_GPU:-1}"
KIT_ARGS="${KIT_ARGS:-}"
if [[ "${DISABLE_RENDERER_MULTI_GPU}" == "1" ]]; then
  renderer_kit_args="--/renderer/multiGpu/enabled=false --/renderer/multiGpu/autoEnable=false"
  KIT_ARGS="${KIT_ARGS:+${KIT_ARGS} }${renderer_kit_args}"
fi

args=(
  Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py
  --num_envs "${NUM_ENVS:-1024}"
  --max_iterations "${MAX_ITERATIONS:-10000}"
  --device "${DEVICE:-cuda:4}"
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
