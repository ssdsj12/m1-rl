#!/usr/bin/env bash
set -euo pipefail

PLACEHOLDER="/home/hexinkun/sleep.py"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLACEHOLDER_PID=""
PLACEHOLDER_RESTORED=0
restore_placeholder() {
  if [[ "${PLACEHOLDER_RESTORED}" -eq 1 ]]; then return; fi
  PLACEHOLDER_RESTORED=1
  if ! pgrep -u "${USER}" -f "^/home/hexinkun/miniconda3/envs/amp/bin/python /home/hexinkun/sleep\.py$" >/dev/null 2>&1; then
    (cd /home/hexinkun && nohup env CUDA_VISIBLE_DEVICES=7 PYTHONUNBUFFERED=1 /home/hexinkun/miniconda3/envs/amp/bin/python "${PLACEHOLDER}" >/tmp/m1_placeholder.log 2>&1 &)
    for _ in {1..10}; do
      if pgrep -u "${USER}" -f "^/home/hexinkun/miniconda3/envs/amp/bin/python /home/hexinkun/sleep\.py$" >/dev/null 2>&1; then
        echo "PLACEHOLDER_READY path=${PLACEHOLDER}"
        return
      fi
      sleep 1
    done
    echo "PLACEHOLDER_RESTART_FAILED path=${PLACEHOLDER}" >&2
  else
    echo "PLACEHOLDER_ALREADY_RUNNING path=${PLACEHOLDER}"
  fi
}
trap restore_placeholder EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

# Keep Isaac confined to the requested physical GPU.  With CUDA_VISIBLE_DEVICES
# set, that GPU is device 0 from the process' point of view; remap the common
# external ``cuda:7`` spelling so callers cannot accidentally create contexts
# on the other cards.
VISIBLE_GPU="${M1_CUDA_VISIBLE_DEVICES:-7}"
export CUDA_VISIBLE_DEVICES="${VISIBLE_GPU}"

# The repository's EGL ICD crashes Vulkan enumeration on the current 575.64.05
# driver.  Prefer the system NVIDIA ICD (GLX-backed on this Xorg display), while
# allowing a server-specific override for installations that provide another
# validated NVIDIA ICD.  Fail closed rather than inheriting a known-bad value.
VULKAN_ICD="${M1_VULKAN_ICD:-${SCRIPT_DIR}/../config/vulkan/nvidia_egl_icd.json}"
if [[ ! -r "${VULKAN_ICD}" ]]; then
  echo "NVIDIA Vulkan ICD is not readable: ${VULKAN_ICD}" >&2
  exit 2
fi
export VK_DRIVER_FILES="${VULKAN_ICD}"
export VK_ICD_FILENAMES="${VULKAN_ICD}"

# Only a GPU7 run may stop the GPU7 memory placeholder.  A bounded smoke on
# another card must leave GPU7 untouched, otherwise validation itself can
# disrupt the user's reserved display/placeholder context.
if [[ "${VISIBLE_GPU}" == "7" ]]; then
  while read -r pid cmd; do
    if [[ "${cmd}" == *"python sleep.py"* ]] || [[ "${cmd}" == *"python /home/hexinkun/sleep.py"* ]]; then
      PLACEHOLDER_PID="${pid}"
      kill -TERM "${pid}" 2>/dev/null || true
      break
    fi
  done < <(ps -u "${USER}" -o pid=,args= | grep -E 'python(3)? .*/home/hexinkun/[s]leep\.py|python(3)? [s]leep\.py' || true)

  if [[ -n "${PLACEHOLDER_PID}" ]]; then
    for _ in {1..20}; do
      kill -0 "${PLACEHOLDER_PID}" 2>/dev/null || break
      sleep 1
    done
    kill -KILL "${PLACEHOLDER_PID}" 2>/dev/null || true
    echo "PLACEHOLDER_STOPPED pid=${PLACEHOLDER_PID}"
  else
    echo "PLACEHOLDER_NOT_FOUND"
  fi
else
  echo "PLACEHOLDER_KEEP gpu=${VISIBLE_GPU}"
fi
# Validated M1 serial foot trajectory defaults.  Callers may override these
# for a bounded probe, but ordinary GPU7 training must not silently fall back
# to the old diagonal/low-knee teacher.
export M1_TEACHER_FOOT_TRAJECTORY="${M1_TEACHER_FOOT_TRAJECTORY:-1}"
export M1_TEACHER_SERIAL_FORCE="${M1_TEACHER_SERIAL_FORCE:-1}"
export M1_TEACHER_PHASE_BLOCK="${M1_TEACHER_PHASE_BLOCK:-128}"
export M1_TEACHER_LEG_SEQUENCE="${M1_TEACHER_LEG_SEQUENCE:-0,3,2,1}"
export M1_TEACHER_STRICT_SEQUENCE="${M1_TEACHER_STRICT_SEQUENCE:-1}"
export M1_TEACHER_USE_ACTUAL_CONTACT="${M1_TEACHER_USE_ACTUAL_CONTACT:-0}"
export M1_TEACHER_COLLISION_LOOKAHEAD_M="${M1_TEACHER_COLLISION_LOOKAHEAD_M:-0.0}"
export M1_TEACHER_COLLISION_LOOKAHEAD_X_M="${M1_TEACHER_COLLISION_LOOKAHEAD_X_M:-0.0}"
export M1_TEACHER_USE_PLANNER_FOOT_TARGET="${M1_TEACHER_USE_PLANNER_FOOT_TARGET:-1}"
export M1_TEACHER_USE_PLANNER_CONTACT="${M1_TEACHER_USE_PLANNER_CONTACT:-0}"
export M1_TEACHER_SLEW_RAD="${M1_TEACHER_SLEW_RAD:-0.10}"
export M1_TEACHER_FOOT_LIFT_M="${M1_TEACHER_FOOT_LIFT_M:-0.20}"
export M1_TEACHER_FOOT_LIFT_SCALE="${M1_TEACHER_FOOT_LIFT_SCALE:-1.20,1.30,1.05,1.05}"
export M1_TEACHER_FOOT_ADVANCE_M="${M1_TEACHER_FOOT_ADVANCE_M:-0.22}"
export M1_TEACHER_FOOT_BACKSTEP_M="${M1_TEACHER_FOOT_BACKSTEP_M:-0.12}"
export M1_TEACHER_DRIVE_WHEELS="${M1_TEACHER_DRIVE_WHEELS:-1}"
export M1_TEACHER_REPROJECT_STANCE="${M1_TEACHER_REPROJECT_STANCE:-0}"
export M1_TEACHER_UPRIGHT_SUPPORT="${M1_TEACHER_UPRIGHT_SUPPORT:-0}"
export M1_TEACHER_UPRIGHT_SUPPORT_BLEND="${M1_TEACHER_UPRIGHT_SUPPORT_BLEND:-0.15}"
export M1_TEACHER_UPRIGHT_SUPPORT_MAX_SHIFT_M="${M1_TEACHER_UPRIGHT_SUPPORT_MAX_SHIFT_M:-0.012}"
export M1_TEACHER_IK_FALLBACK="${M1_TEACHER_IK_FALLBACK:-1}"
export M1_TEACHER_USE_MEASURED_HOLD="${M1_TEACHER_USE_MEASURED_HOLD:-1}"
export M1_TEACHER_USE_PLANNER_TOUCHDOWN="${M1_TEACHER_USE_PLANNER_TOUCHDOWN:-1}"
export M1_TEACHER_IGNORE_PLANNER_VALID="${M1_TEACHER_IGNORE_PLANNER_VALID:-1}"
export M1_TEACHER_INVALID_HOLD_CURRENT="${M1_TEACHER_INVALID_HOLD_CURRENT:-1}"
export M1_TEACHER_RECOVERY_HOLD="${M1_TEACHER_RECOVERY_HOLD:-0}"
export M1_TEACHER_RECOVERY_TILT_RAD="${M1_TEACHER_RECOVERY_TILT_RAD:-0.45}"
export M1_TEACHER_HOLD_FOOT_USE_CURRENT="${M1_TEACHER_HOLD_FOOT_USE_CURRENT:-1}"
export M1_TEACHER_WHEEL_SWING_SCALE="${M1_TEACHER_WHEEL_SWING_SCALE:-0.15}"
export M1_TEACHER_SUPPORT_WHEEL_SWING_SCALE="${M1_TEACHER_SUPPORT_WHEEL_SWING_SCALE:-0.50}"
export M1_TEACHER_CROSSING_MAX_TILT_RAD="${M1_TEACHER_CROSSING_MAX_TILT_RAD:-0.45}"
export M1_TEACHER_INITIAL_FALLBACK="${M1_TEACHER_INITIAL_FALLBACK:-0}"
export M1_TEACHER_PRELIFT="${M1_TEACHER_PRELIFT:-1}"
export M1_TEACHER_HOLD_CONTACT_BLEND="${M1_TEACHER_HOLD_CONTACT_BLEND:-0.20}"
export M1_TEACHER_MAX_HIP_LIFT_RAD="${M1_TEACHER_MAX_HIP_LIFT_RAD:-0.40}"
export M1_TEACHER_MAX_ABAD_RAD="${M1_TEACHER_MAX_ABAD_RAD:-0.10}"
export M1_TEACHER_MAX_KNEE_LIFT_RAD="${M1_TEACHER_MAX_KNEE_LIFT_RAD:-2.20}"
# Keep exactly one physical swing leg by default.  Raising an opposite leg as
# "support compensation" is still available as an explicit experiment, but
# it violates the M1 single-foot crossing contract in normal training.
export M1_TEACHER_SUPPORT_KNEE_COMP_RAD="${M1_TEACHER_SUPPORT_KNEE_COMP_RAD:-0.0}"
export M1_TEACHER_STANCE_KNEE_RAISE_RAD="${M1_TEACHER_STANCE_KNEE_RAISE_RAD:-0.0}"
export M1_TEACHER_MAX_STEPS="${M1_TEACHER_MAX_STEPS:-2048}"
export M1_TEACHER_CLEAR_STEPS="${M1_TEACHER_CLEAR_STEPS:-512}"
ARGS=("$@")
for ((i=0; i<${#ARGS[@]}; i++)); do
  if [[ "${ARGS[$i]}" == "cuda:7" ]]; then
    ARGS[$i]="cuda:0"
  elif [[ "${ARGS[$i]}" == "--device=cuda:7" ]]; then
    ARGS[$i]="--device=cuda:0"
  fi
done
"${ARGS[@]}"
rc=$?
exit "$rc"
