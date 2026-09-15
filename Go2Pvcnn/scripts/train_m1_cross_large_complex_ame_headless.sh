#!/usr/bin/env bash
set -euo pipefail

cd /home/hexinkun/m1_rl

ISAAC_ENV="/home/hexinkun/miniconda3/envs/m1"
export PATH="${ISAAC_ENV}/bin:${PATH}"
export PYTHONPATH="/home/hexinkun/m1_rl/Go2Pvcnn:/home/hexinkun/amp/Go2Pvcnn:/home/hexinkun/amp/Go2Pvcnn/rsl_rl:/home/hexinkun/IsaacLab45/source/isaaclab:/home/hexinkun/IsaacLab45/source/isaaclab_rl:/home/hexinkun/IsaacLab45/source/isaaclab_tasks:/home/hexinkun/IsaacLab45/source/isaaclab_assets:/home/hexinkun/miniconda3/envs/m1/lib/python3.10/site-packages:${PYTHONPATH:-}"
export OMNI_KIT_ACCEPT_EULA="${OMNI_KIT_ACCEPT_EULA:-Y}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export LD_LIBRARY_PATH="${ISAAC_ENV}/lib/python3.10/site-packages/torch/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cuda_nvrtc/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cudnn/lib:${ISAAC_ENV}/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cuda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64:${LD_LIBRARY_PATH:-}"

args=(
  Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py
  --num_envs "${NUM_ENVS:-1024}"
  --max_iterations "${MAX_ITERATIONS:-10000}"
  --device "${DEVICE:-cuda:0}"
  --headless
)

if [[ -n "${CHECKPOINT:-}" ]]; then
  args+=(--resume --checkpoint "${CHECKPOINT}")
  if [[ "${KEEP_STD:-0}" == "1" ]]; then
    args+=(--keep_std)
  fi
fi

exec "${ISAAC_ENV}/bin/python" "${args[@]}"
