#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/home/hexinkun/m1_rl}
AMP_PREFIX=${AMP_PREFIX:-/home/hexinkun/miniconda3/envs/amp}
CONDA_BIN=${CONDA_BIN:-/home/hexinkun/miniconda3/bin/conda}
ISAACLAB_ROOT=${ISAACLAB_ROOT:-/home/hexinkun/IsaacLab45}
SNAPSHOT_DIR=${SNAPSHOT_DIR:-${REPO_ROOT}/run_logs/environment_snapshots}

mkdir -p "${SNAPSHOT_DIR}"

capture_before_snapshot() {
    "${CONDA_BIN}" list --prefix "${AMP_PREFIX}" --explicit \
        > "${SNAPSHOT_DIR}/amp-before-conda-explicit.txt"
    "${AMP_PREFIX}/bin/python" -m pip freeze \
        > "${SNAPSHOT_DIR}/amp-before-pip-freeze.txt"
}

capture_after_snapshot() {
    "${CONDA_BIN}" list --prefix "${AMP_PREFIX}" --explicit \
        > "${SNAPSHOT_DIR}/amp-after-conda-explicit.txt"
    "${AMP_PREFIX}/bin/python" -m pip freeze \
        > "${SNAPSHOT_DIR}/amp-after-pip-freeze.txt"
    env -u PYTHONPATH -u CUDA_VISIBLE_DEVICES "${AMP_PREFIX}/bin/python" -m pip check \
        > "${SNAPSHOT_DIR}/amp-after-pip-check.txt"
}

capture_before_snapshot

"${CONDA_BIN}" install --yes --prefix "${AMP_PREFIX}" -c conda-forge \
    python=3.10 cmake make gcc_linux-64 gxx_linux-64 \
    libegl=1.7.0 libglvnd=1.7.0 libopengl=1.7.0 libglu=9.0.3

"${AMP_PREFIX}/bin/python" -m pip install --upgrade \
    'pip<27' 'setuptools<81' wheel
"${AMP_PREFIX}/bin/python" -m pip install \
    --index-url https://download.pytorch.org/whl/cu128 \
    torch==2.7.0 torchvision==0.22.0
"${AMP_PREFIX}/bin/python" -m pip install \
    --extra-index-url https://pypi.nvidia.com \
    'isaacsim[all,extscache]==4.5.0.0'
"${AMP_PREFIX}/bin/python" -m pip install \
    numpy==1.26.4 gymnasium==1.2.0 warp-lang==1.17.0 pillow==11.2.1

"${AMP_PREFIX}/bin/python" -m pip install --editable \
    "${ISAACLAB_ROOT}/source/isaaclab"
"${AMP_PREFIX}/bin/python" -m pip install --editable \
    "${ISAACLAB_ROOT}/source/isaaclab_assets"
"${AMP_PREFIX}/bin/python" -m pip install --editable \
    "${ISAACLAB_ROOT}/source/isaaclab_tasks"
"${AMP_PREFIX}/bin/python" -m pip install --editable \
    "${ISAACLAB_ROOT}/source/isaaclab_rl"
"${AMP_PREFIX}/bin/python" -m pip install --editable \
    "${ISAACLAB_ROOT}/source/isaaclab_mimic"
"${AMP_PREFIX}/bin/python" -m pip install --editable \
    "${REPO_ROOT}/Go2Pvcnn/rsl_rl"
"${AMP_PREFIX}/bin/python" -m pip install --editable "${REPO_ROOT}/Go2Pvcnn"

capture_after_snapshot
