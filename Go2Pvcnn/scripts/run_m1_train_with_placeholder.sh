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
