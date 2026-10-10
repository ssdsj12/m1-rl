#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/opt/conda/envs/env_issacsim/bin/python}"
ISAACLAB_ROOT="${ISAACLAB_ROOT:-/root/quad/isaac/IsaacLab}"
export OMNI_KIT_ACCEPT_EULA=Y
export PYTHONUNBUFFERED=1
export PYTHONPATH="$REPO_ROOT/Go2Pvcnn:$REPO_ROOT/Go2Pvcnn/rsl_rl:$ISAACLAB_ROOT/source/isaaclab:$ISAACLAB_ROOT/source/isaaclab_assets:$ISAACLAB_ROOT/source/isaaclab_tasks:$ISAACLAB_ROOT/source/isaaclab_rl${PYTHONPATH:+:$PYTHONPATH}"
export SAVE_INTERVAL=100
export M1_DISABLE_RANDOM_EP_LEN=1
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
cd "$REPO_ROOT"
# A kernel lock prevents duplicate jobs; no other user's process is touched.
exec 9>"$REPO_ROOT/.m1-pure-ppo.lock"
flock -n 9 || { echo 'M1 PPO job already holds the lock'; exit 2; }
args=(--num_envs "${NUM_ENVS:-2048}" --max_iterations "${MAX_ITERATIONS:-10000}"
      --device "${DEVICE:-cuda:0}" --headless --course-profile "${COURSE_PROFILE:-mixed}")
if [[ -n "${CHECKPOINT:-}" ]]; then
    args+=(--resume --checkpoint "$CHECKPOINT" --keep_std)
fi
printf 'M1_PURE_PPO_START pid=%s revision=%s envs=%s iterations=%s\n' \
    "$$" "$(git rev-parse HEAD)" "${NUM_ENVS:-2048}" "${MAX_ITERATIONS:-10000}"
exec "$PYTHON_BIN" Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py "${args[@]}"
