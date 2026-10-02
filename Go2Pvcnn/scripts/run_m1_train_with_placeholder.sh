#!/usr/bin/env bash
set -euo pipefail

PLACEHOLDER="/home/hexinkun/sleep.py"
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

# Keep Isaac confined to the requested physical GPU.  With CUDA_VISIBLE_DEVICES
# set, that GPU is device 0 from the process' point of view; remap the common
# external ``cuda:7`` spelling so callers cannot accidentally create contexts
# on the other cards.
VISIBLE_GPU="${M1_CUDA_VISIBLE_DEVICES:-7}"
export CUDA_VISIBLE_DEVICES="${VISIBLE_GPU}"
# Validated M1 serial foot trajectory defaults.  Callers may override these
# for a bounded probe, but ordinary GPU7 training must not silently fall back
# to the old diagonal/low-knee teacher.
export M1_TEACHER_FOOT_TRAJECTORY="${M1_TEACHER_FOOT_TRAJECTORY:-1}"
export M1_TEACHER_SERIAL_FORCE="${M1_TEACHER_SERIAL_FORCE:-1}"
export M1_TEACHER_PHASE_BLOCK="${M1_TEACHER_PHASE_BLOCK:-16}"
export M1_TEACHER_LEG_SEQUENCE="${M1_TEACHER_LEG_SEQUENCE:-0,1,2,3}"
export M1_TEACHER_COLLISION_LOOKAHEAD_M="${M1_TEACHER_COLLISION_LOOKAHEAD_M:-0.0}"
export M1_TEACHER_COLLISION_LOOKAHEAD_X_M="${M1_TEACHER_COLLISION_LOOKAHEAD_X_M:-0.0}"
export M1_TEACHER_USE_PLANNER_FOOT_TARGET="${M1_TEACHER_USE_PLANNER_FOOT_TARGET:-0}"
export M1_TEACHER_USE_PLANNER_CONTACT="${M1_TEACHER_USE_PLANNER_CONTACT:-0}"
export M1_TEACHER_SLEW_RAD="${M1_TEACHER_SLEW_RAD:-0.28}"
export M1_TEACHER_FOOT_LIFT_M="${M1_TEACHER_FOOT_LIFT_M:-0.25}"
export M1_TEACHER_FOOT_ADVANCE_M="${M1_TEACHER_FOOT_ADVANCE_M:-0.18}"
export M1_TEACHER_MAX_HIP_LIFT_RAD="${M1_TEACHER_MAX_HIP_LIFT_RAD:-0.40}"
export M1_TEACHER_MAX_ABAD_RAD="${M1_TEACHER_MAX_ABAD_RAD:-0.10}"
export M1_TEACHER_MAX_KNEE_LIFT_RAD="${M1_TEACHER_MAX_KNEE_LIFT_RAD:-2.20}"
export M1_TEACHER_SUPPORT_KNEE_COMP_RAD="${M1_TEACHER_SUPPORT_KNEE_COMP_RAD:-0.0}"
export M1_TEACHER_STANCE_KNEE_RAISE_RAD="${M1_TEACHER_STANCE_KNEE_RAISE_RAD:-0.0}"
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
