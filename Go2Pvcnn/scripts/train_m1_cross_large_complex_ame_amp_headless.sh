#!/usr/bin/env bash
set -euo pipefail

# Reuse the amp runtime, Vulkan preflight and physical GPU selection from AME.
: "${CHECKPOINT:?Set CHECKPOINT to a compatible M1 AME checkpoint}"
if [[ ! -f "${CHECKPOINT}" ]]; then
  echo "Checkpoint not found: ${CHECKPOINT}" >&2
  exit 2
fi

export TRAIN_ENTRYPOINT=Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_amp.py
export MAX_ITERATIONS="${MAX_ITERATIONS:-3500}"
export CHECKPOINT
exec bash "${REPO_ROOT:-/home/hexinkun/m1_rl}/Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh"
