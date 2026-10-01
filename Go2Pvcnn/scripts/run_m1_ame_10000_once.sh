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
