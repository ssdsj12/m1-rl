#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ISAAC_ENV="/home/hexinkun/miniconda3/envs/amp"
PYTHON_BIN="${ISAAC_ENV}/bin/python"
REFERENCE="/home/hexinkun/m1/Go2Pvcnn"
OUTPUT=""
previous=""
for argument in "$@"; do
  if [[ "${previous}" == "--output" ]]; then OUTPUT="${argument}"; fi
  case "${argument}" in --output=*) OUTPUT="${argument#--output=}" ;; esac
  previous="${argument}"
done
if [[ -z "${OUTPUT}" || -e "${OUTPUT}" ]]; then
  printf 'A new --output directory is required.\n' >&2
  exit 64
fi
export PATH="${ISAAC_ENV}/bin:${PATH}"
export PYTHONPATH="${REFERENCE}:${REFERENCE}/rsl_rl:/home/hexinkun/IsaacLab45/source/isaaclab:/home/hexinkun/IsaacLab45/source/isaaclab_rl:/home/hexinkun/IsaacLab45/source/isaaclab_tasks:/home/hexinkun/IsaacLab45/source/isaaclab_assets:${ISAAC_ENV}/lib/python3.10/site-packages"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export OMNI_KIT_ACCEPT_EULA=Y
export VK_DRIVER_FILES="/home/hexinkun/m1_rl/Go2Pvcnn/config/vulkan/nvidia_egl_icd.json"
export VK_ICD_FILENAMES="${VK_DRIVER_FILES}"
unset CUDA_VISIBLE_DEVICES
export LD_LIBRARY_PATH="${ISAAC_ENV}/lib/python3.10/site-packages/torch/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cuda_nvrtc/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cudnn/lib:${ISAAC_ENV}/lib:${ISAAC_ENV}/lib/python3.10/site-packages/nvidia/cuda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64:${LD_LIBRARY_PATH:-}"
"${PYTHON_BIN}" "${SCRIPT_DIR}/run.py" "$@" --device cuda:4 --headless \
  --kit_args "--/renderer/multiGpu/enabled=false --/renderer/multiGpu/autoEnable=false" &
SIM_PID=$!
wait "${SIM_PID}"
NATIVE_EXIT_CODE=$?
printf 'M1_REFERENCE_NATIVE_EXIT pid=%s code=%s\n' "${SIM_PID}" "${NATIVE_EXIT_CODE}"
"${PYTHON_BIN}" "${SCRIPT_DIR}/runtime.py" finalize --output "${OUTPUT}" \
  --native-exit-code "${NATIVE_EXIT_CODE}" --expected-pid "${SIM_PID}"
WRAPPER_RETURN_CODE=$?
printf 'M1_REFERENCE_WRAPPER_RETURN code=%s\n' "${WRAPPER_RETURN_CODE}"
exit "${WRAPPER_RETURN_CODE}"
