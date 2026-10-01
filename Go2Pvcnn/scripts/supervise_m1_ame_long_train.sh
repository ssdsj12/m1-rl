#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="${REPO_ROOT:-/home/hexinkun/m1_rl}"
CHECKPOINT_ROOT="${CHECKPOINT_ROOT:-${REPO_ROOT}/logs/rsl_rl/m1_cross_large_complex_ame}"
LOG_DIR="${LOG_DIR:-${REPO_ROOT}/run_logs}"
STATE_DIR="${STATE_DIR:-${LOG_DIR}/m1_ame_1024_supervisor_state}"
MASTER_LOG="${MASTER_LOG:-${LOG_DIR}/m1_ame_1024_supervisor.log}"
LOCK_FILE="${LOCK_FILE:-${LOG_DIR}/m1_ame_1024_supervisor.lock}"
LINEAGE_FILE="${LINEAGE_FILE:-${STATE_DIR}/checkpoint_lineage}"
CURRENT_CHECKPOINT_FILE="${CURRENT_CHECKPOINT_FILE:-${STATE_DIR}/current_checkpoint}"
TRAIN_LAUNCHER="${TRAIN_LAUNCHER:-${REPO_ROOT}/Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh}"
CHECKPOINT_PYTHON="${CHECKPOINT_PYTHON:-/home/hexinkun/miniconda3/envs/m1/bin/python}"
CHECKPOINT_VALIDATOR="${CHECKPOINT_VALIDATOR:-}"
INITIAL_CHECKPOINT="${INITIAL_CHECKPOINT:-}"
EXPECTED_AME_SIGNATURE="${EXPECTED_AME_SIGNATURE:-ame_xyz_semantic_v1_c6_s16_mha64_h16}"
EXPECTED_AME_ACTOR_OBS="${EXPECTED_AME_ACTOR_OBS:-1585}"
EXPECTED_AME_CRITIC_OBS="${EXPECTED_AME_CRITIC_OBS:-1588}"
EXPECTED_AME_ACTIONS="${EXPECTED_AME_ACTIONS:-16}"
TARGET_ITERATIONS="${TARGET_ITERATIONS:-10000}"
NUM_ENVS="${NUM_ENVS:-1024}"
DEVICE="${DEVICE:-cuda:4}"
SAVE_INTERVAL="${SAVE_INTERVAL:-10}"
KEEP_STD="${KEEP_STD:-1}"
STALL_TIMEOUT_SECONDS="${STALL_TIMEOUT_SECONDS:-300}"
STARTUP_GRACE_SECONDS="${STARTUP_GRACE_SECONDS:-180}"
WATCH_INTERVAL_SECONDS="${WATCH_INTERVAL_SECONDS:-15}"
RESTART_DELAY_SECONDS="${RESTART_DELAY_SECONDS:-10}"
TERM_GRACE_SECONDS="${TERM_GRACE_SECONDS:-15}"

TRAIN_PID=""
TRAIN_PGID=""
TRAIN_WAITED=0
TRAIN_RC=0
ATTEMPT_LOG=""
ATTEMPT_NUMBER=0

log_event() {
  local message="$1"
  printf '%s\n' "${message}" | tee -a -- "${MASTER_LOG}"
  if [[ -n "${ATTEMPT_LOG}" ]]; then
    printf '%s\n' "${message}" >> "${ATTEMPT_LOG}"
  fi
}

goal_iteration() {
  printf '%s\n' "$((TARGET_ITERATIONS - 1))"
}

# A checkpoint's iter is the last completed zero-based update. Resume starts
# at iter + 1, so model_1037 has completed 1,038 of a 10,000-update run.
remaining_iterations() {
  local last_completed_iteration="$1"
  printf '%s\n' "$((TARGET_ITERATIONS - last_completed_iteration - 1))"
}

checkpoint_metadata() {
  local checkpoint="$1"
  local output iteration next_iteration extra base filename_iteration

  [[ -f "${checkpoint}" ]] || return 1
  if [[ -n "${CHECKPOINT_VALIDATOR}" ]]; then
    output="$("${CHECKPOINT_VALIDATOR}" "${checkpoint}" 2>/dev/null)" || return 1
  else
    output="$("${CHECKPOINT_PYTHON}" - \
      "${checkpoint}" \
      "${EXPECTED_AME_SIGNATURE}" \
      "${EXPECTED_AME_ACTOR_OBS}" \
      "${EXPECTED_AME_CRITIC_OBS}" \
      "${EXPECTED_AME_ACTIONS}" 2>/dev/null <<'PY'
import sys

import torch

path = sys.argv[1]
expected_metadata = {
    "ame_architecture_signature": sys.argv[2],
    "ame_num_actor_obs": int(sys.argv[3]),
    "ame_num_critic_obs": int(sys.argv[4]),
    "ame_num_actions": int(sys.argv[5]),
}
payload = torch.load(path, map_location="cpu", weights_only=False)
if not isinstance(payload, dict):
    raise TypeError("checkpoint payload is not a dict")
for key in ("model_state_dict", "optimizer_state_dict", "iter"):
    if key not in payload:
        raise KeyError(key)
for key, expected in expected_metadata.items():
    if payload.get(key) != expected:
        raise ValueError(f"incompatible {key}: {payload.get(key)!r}")
iteration = payload["iter"]
next_iteration = payload.get("next_iter", iteration + 1)
if isinstance(iteration, bool) or not isinstance(iteration, int):
    raise TypeError("iter is not an int")
if isinstance(next_iteration, bool) or not isinstance(next_iteration, int):
    raise TypeError("next_iter is not an int")
if next_iteration != iteration + 1:
    raise ValueError("next_iter must equal iter + 1")
print(iteration, next_iteration)
PY
)" || return 1
  fi

  read -r iteration next_iteration extra <<< "${output}"
  [[ "${iteration}" =~ ^[0-9]+$ ]] || return 1
  [[ "${next_iteration}" =~ ^[0-9]+$ ]] || return 1
  [[ -z "${extra:-}" ]] || return 1
  (( next_iteration == iteration + 1 )) || return 1

  base="$(basename -- "${checkpoint}")"
  [[ "${base}" =~ ^model_([0-9]+)\.pt$ ]] || return 1
  filename_iteration="${BASH_REMATCH[1]}"
  (( 10#${filename_iteration} == iteration )) || return 1
  printf '%s %s\n' "${iteration}" "${next_iteration}"
}

path_is_under_checkpoint_root() {
  local path="$1"
  local resolved root
  resolved="$(realpath -m -- "${path}")" || return 1
  root="$(realpath -m -- "${CHECKPOINT_ROOT}")" || return 1
  case "${resolved}" in
    "${root}"|"${root}"/*) return 0 ;;
    *) return 1 ;;
  esac
}

add_lineage_dir() {
  local directory="$1"
  local resolved
  resolved="$(realpath -m -- "${directory}")" || return 1
  path_is_under_checkpoint_root "${resolved}" || return 1
  [[ -d "${resolved}" ]] || return 1
  if ! grep -Fqx -- "${resolved}" "${LINEAGE_FILE}" 2>/dev/null; then
    printf '%s\n' "${resolved}" >> "${LINEAGE_FILE}"
  fi
}

persist_current_checkpoint() {
  local checkpoint="$1"
  local temporary
  temporary="$(mktemp "${STATE_DIR}/current_checkpoint.XXXXXX")" || return 1
  printf '%s\n' "$(realpath -- "${checkpoint}")" > "${temporary}"
  mv -f -- "${temporary}" "${CURRENT_CHECKPOINT_FILE}"
}

latest_valid_checkpoint_from_roots() {
  local candidates ranked root checkpoint base filename_iteration
  local metadata candidate_iteration candidate_next mtime
  (( $# > 0 )) || return 1

  candidates="$(mktemp "${STATE_DIR}/checkpoint_candidates.XXXXXX")" || return 1
  ranked="$(mktemp "${STATE_DIR}/checkpoint_ranked.XXXXXX")" || {
    rm -f -- "${candidates}"
    return 1
  }

  for root in "$@"; do
    [[ -d "${root}" ]] || continue
    find "${root}" -type f -name 'model_*.pt' -print >> "${candidates}" 2>/dev/null || true
  done

  # Rank numerically by the filename first, then validate content in descending
  # order. checkpoint_metadata requires filename iter == payload iter, so this
  # avoids loading hundreds of historical files on every watchdog poll without
  # allowing a newer-mtime model_0.pt to roll progress back from model_1040.pt.
  while IFS= read -r checkpoint; do
    base="$(basename -- "${checkpoint}")"
    if [[ "${base}" =~ ^model_([0-9]+)\.pt$ ]]; then
      filename_iteration="${BASH_REMATCH[1]}"
      mtime="$(stat -c '%Y' -- "${checkpoint}" 2>/dev/null || printf '0')"
      printf '%020d\t%020d\t%s\n' "$((10#${filename_iteration}))" "${mtime}" "${checkpoint}" >> "${ranked}"
    fi
  done < "${candidates}"

  sort -r -o "${ranked}" -- "${ranked}"
  while IFS=$'\t' read -r _ _ checkpoint; do
    metadata="$(checkpoint_metadata "${checkpoint}")" || {
      continue
    }
    read -r candidate_iteration candidate_next <<< "${metadata}"
    printf '%s\t%s\t%s\n' "${checkpoint}" "${candidate_iteration}" "${candidate_next}"
    rm -f -- "${candidates}" "${ranked}"
    return 0
  done < "${ranked}"

  rm -f -- "${candidates}" "${ranked}"
  return 1
}

latest_lineage_checkpoint() {
  local -a roots=()
  [[ -s "${LINEAGE_FILE}" ]] || return 1
  mapfile -t roots < "${LINEAGE_FILE}"
  latest_valid_checkpoint_from_roots "${roots[@]}"
}

select_initial_checkpoint() {
  local selected metadata directory checkpoint iteration next_iteration

  if [[ -n "${INITIAL_CHECKPOINT}" ]]; then
    checkpoint="$(realpath -- "${INITIAL_CHECKPOINT}" 2>/dev/null)" || return 1
    path_is_under_checkpoint_root "${checkpoint}" || return 1
    metadata="$(checkpoint_metadata "${checkpoint}")" || return 1
    : > "${LINEAGE_FILE}"
    add_lineage_dir "$(dirname -- "${checkpoint}")" || return 1
    persist_current_checkpoint "${checkpoint}" || return 1
    read -r iteration next_iteration <<< "${metadata}"
    printf '%s\t%s\t%s\n' "${checkpoint}" "${iteration}" "${next_iteration}"
    return 0
  fi

  if [[ -s "${LINEAGE_FILE}" ]]; then
    selected="$(latest_lineage_checkpoint)" || return 1
    IFS=$'\t' read -r checkpoint iteration next_iteration <<< "${selected}"
    persist_current_checkpoint "${checkpoint}" || return 1
    printf '%s\t%s\t%s\n' "${checkpoint}" "${iteration}" "${next_iteration}"
    return 0
  fi

  selected="$(latest_valid_checkpoint_from_roots "${CHECKPOINT_ROOT}")" || return 1
  IFS=$'\t' read -r checkpoint iteration next_iteration <<< "${selected}"
  directory="$(dirname -- "${checkpoint}")"
  add_lineage_dir "${directory}" || return 1
  persist_current_checkpoint "${checkpoint}" || return 1
  printf '%s\t%s\t%s\n' "${checkpoint}" "${iteration}" "${next_iteration}"
}

discover_attempt_lineage() {
  local run_dir
  [[ -f "${ATTEMPT_LOG}" ]] || return 1
  run_dir="$(sed -n 's/^\[AME\] log_dir=//p' "${ATTEMPT_LOG}" | tail -n 1)"
  [[ -n "${run_dir}" ]] || return 1
  add_lineage_dir "${run_dir}"
}

process_group_has_live_members() {
  local pgid="$1"
  [[ "${pgid}" =~ ^[0-9]+$ ]] || return 1
  ps -eo pgid=,stat= 2>/dev/null \
    | awk -v target="${pgid}" '$1 == target && $2 !~ /^Z/ { found = 1 } END { exit !found }'
}

verify_training_group() {
  local group_info observed_pgid observed_sid
  [[ "${TRAIN_PID}" =~ ^[0-9]+$ ]] || return 1
  group_info="$(ps -o pgid=,sid= -p "${TRAIN_PID}" 2>/dev/null)"
  read -r observed_pgid observed_sid <<< "${group_info}"
  if [[ "${observed_pgid}" == "${TRAIN_PID}" \
    && "${observed_sid}" == "${TRAIN_PID}" ]]; then
    TRAIN_PGID="${observed_pgid}"
    return 0
  fi
  return 1
}

reap_training() {
  if [[ -n "${TRAIN_PID}" ]] && (( TRAIN_WAITED == 0 )); then
    wait "${TRAIN_PID}" 2>/dev/null
    TRAIN_RC=$?
    TRAIN_WAITED=1
  fi
}

terminate_training() {
  local waited=0
  if ! [[ "${TRAIN_PGID}" =~ ^[0-9]+$ ]]; then
    # The child may have completed setsid between the launch poll and a signal.
    # Re-verify here before deciding whether a negative group signal is safe.
    verify_training_group || true
  fi
  if [[ "${TRAIN_PGID}" =~ ^[0-9]+$ ]] && process_group_has_live_members "${TRAIN_PGID}"; then
    kill -TERM -- "-${TRAIN_PGID}" 2>/dev/null || true
    while process_group_has_live_members "${TRAIN_PGID}" && (( waited < TERM_GRACE_SECONDS )); do
      sleep 1
      waited=$((waited + 1))
    done
    if process_group_has_live_members "${TRAIN_PGID}"; then
      kill -KILL -- "-${TRAIN_PGID}" 2>/dev/null || true
    fi
  elif [[ "${TRAIN_PID}" =~ ^[0-9]+$ ]] && kill -0 "${TRAIN_PID}" 2>/dev/null; then
    # A signal can arrive while setsid is still establishing the new group.
    # In that state only the exact child PID is trusted; never send a negative
    # signal to an inherited, unverified process group.
    kill -TERM "${TRAIN_PID}" 2>/dev/null || true
    while kill -0 "${TRAIN_PID}" 2>/dev/null && (( waited < TERM_GRACE_SECONDS )); do
      sleep 1
      waited=$((waited + 1))
    done
    if kill -0 "${TRAIN_PID}" 2>/dev/null; then
      kill -KILL "${TRAIN_PID}" 2>/dev/null || true
    fi
  fi
  reap_training
}

request_shutdown() {
  local signal_name="$1"
  local exit_code="$2"
  trap - INT TERM HUP
  log_event "SUPERVISOR_SHUTDOWN $(date -Is) signal=${signal_name}"
  terminate_training
  exit "${exit_code}"
}

cleanup() {
  terminate_training
}

launch_training() {
  local checkpoint="$1"
  local remaining="$2"

  TRAIN_WAITED=0
  TRAIN_RC=0
  env \
    NUM_ENVS="${NUM_ENVS}" \
    MAX_ITERATIONS="${remaining}" \
    DEVICE="${DEVICE}" \
    SAVE_INTERVAL="${SAVE_INTERVAL}" \
    CHECKPOINT="${checkpoint}" \
    KEEP_STD="${KEEP_STD}" \
    MASTER_LOG="${MASTER_LOG}" \
    ATTEMPT_LOG="${ATTEMPT_LOG}" \
    setsid bash -o pipefail -c \
      '"$1" 2>&1 | tee -a -- "$MASTER_LOG" "$ATTEMPT_LOG"' \
      supervisor-attempt "${TRAIN_LAUNCHER}" 9>&- &
  TRAIN_PID=$!

  TRAIN_PGID=""
  for _ in {1..100}; do
    verify_training_group && return 0
    if ! kill -0 "${TRAIN_PID}" 2>/dev/null; then
      reap_training
      return 0
    fi
    sleep 0.02
  done

  log_event "TRAIN_GROUP_UNVERIFIED $(date -Is) pid=${TRAIN_PID}"
  terminate_training
  return 1
}

main() {
  local selected checkpoint current_iteration current_next goal remaining
  local started_at last_progress_at last_iteration last_next stalled now
  local new_selected new_checkpoint new_iteration new_next rc attempt_id

  if ! [[ "${TARGET_ITERATIONS}" =~ ^[1-9][0-9]*$ ]]; then
    printf 'SUPERVISOR_ERROR %s invalid TARGET_ITERATIONS=%s\n' "$(date -Is)" "${TARGET_ITERATIONS}" >&2
    return 2
  fi

  mkdir -p -- "${LOG_DIR}" "${STATE_DIR}"
  cd "${REPO_ROOT}" || return 2

  exec 9>"${LOCK_FILE}"
  if ! flock -n 9; then
    printf 'SUPERVISOR_ALREADY_RUNNING %s lock=%s\n' "$(date -Is)" "${LOCK_FILE}" | tee -a -- "${MASTER_LOG}"
    return 73
  fi

  trap 'request_shutdown INT 130' INT
  trap 'request_shutdown TERM 143' TERM
  trap 'request_shutdown HUP 129' HUP
  trap cleanup EXIT

  selected="$(select_initial_checkpoint)" || {
    log_event "SUPERVISOR_ERROR $(date -Is) no valid isolated checkpoint under ${CHECKPOINT_ROOT}"
    return 2
  }
  IFS=$'\t' read -r checkpoint current_iteration current_next <<< "${selected}"
  goal="$(goal_iteration)"

  while true; do
    if (( current_next >= TARGET_ITERATIONS )); then
      log_event "TRAINING_COMPLETE $(date -Is) target_iterations=${TARGET_ITERATIONS} checkpoint=${checkpoint} next_iteration=${current_next}"
      return 0
    fi

    remaining="$(remaining_iterations "${current_iteration}")"
    if (( remaining <= 0 )); then
      log_event "SUPERVISOR_ERROR $(date -Is) invalid remaining=${remaining} checkpoint=${checkpoint}"
      return 2
    fi

    ATTEMPT_NUMBER=$((ATTEMPT_NUMBER + 1))
    attempt_id="$(date +%Y%m%d_%H%M%S_%N)_$$_${ATTEMPT_NUMBER}"
    ATTEMPT_LOG="${LOG_DIR}/m1_ame_1024_attempt_${attempt_id}.log"
    : > "${ATTEMPT_LOG}"
    log_event "=== RESTART $(date -Is) current=${current_iteration} next=${current_next} goal=${goal} remaining=${remaining} checkpoint=${checkpoint} device=${DEVICE} ==="

    if ! launch_training "${checkpoint}" "${remaining}"; then
      log_event "SUPERVISOR_ERROR $(date -Is) failed to establish isolated training process group"
      return 2
    fi
    started_at="$(date +%s)"
    last_progress_at="${started_at}"
    last_iteration="${current_iteration}"
    last_next="${current_next}"
    stalled=0

    while process_group_has_live_members "${TRAIN_PGID}"; do
      sleep "${WATCH_INTERVAL_SECONDS}"
      now="$(date +%s)"
      discover_attempt_lineage || true
      new_selected="$(latest_lineage_checkpoint)" || new_selected=""
      if [[ -n "${new_selected}" ]]; then
        IFS=$'\t' read -r new_checkpoint new_iteration new_next <<< "${new_selected}"
        if (( new_next > last_next )); then
          checkpoint="${new_checkpoint}"
          current_iteration="${new_iteration}"
          current_next="${new_next}"
          last_iteration="${new_iteration}"
          last_next="${new_next}"
          last_progress_at="${now}"
          persist_current_checkpoint "${checkpoint}"
          log_event "CHECKPOINT_PROGRESS $(date -Is) pid=${TRAIN_PID} iteration=${last_iteration} next_iteration=${last_next} checkpoint=${checkpoint}"
        fi
      fi

      if (( now - started_at >= STARTUP_GRACE_SECONDS )) \
        && (( now - last_progress_at >= STALL_TIMEOUT_SECONDS )); then
        log_event "STALL_DETECTED $(date -Is) pid=${TRAIN_PID} pgid=${TRAIN_PGID} last_iteration=${last_iteration} no_checkpoint_progress_seconds=$((now - last_progress_at))"
        stalled=1
        terminate_training
        break
      fi
    done

    reap_training
    rc="${TRAIN_RC}"
    discover_attempt_lineage || true
    new_selected="$(latest_lineage_checkpoint)" || new_selected=""
    if [[ -n "${new_selected}" ]]; then
      IFS=$'\t' read -r new_checkpoint new_iteration new_next <<< "${new_selected}"
      if (( new_next > current_next )); then
        checkpoint="${new_checkpoint}"
        current_iteration="${new_iteration}"
        current_next="${new_next}"
        persist_current_checkpoint "${checkpoint}"
      fi
    fi

    TRAIN_PID=""
    TRAIN_PGID=""
    TRAIN_WAITED=0

    if grep -Fq 'Training Complete - m1_cross_large_complex_ame' "${ATTEMPT_LOG}" \
      && (( current_next >= TARGET_ITERATIONS )); then
      log_event "TRAINING_COMPLETE $(date -Is) target_iterations=${TARGET_ITERATIONS} checkpoint=${checkpoint} next_iteration=${current_next}"
      return 0
    fi

    log_event "EARLY_TERMINATION $(date -Is) python_exit_code=${rc} stalled=${stalled} last_checkpoint=${checkpoint} last_iteration=${current_iteration} next_iteration=${current_next}"
    sleep "${RESTART_DELAY_SECONDS}"
  done
}

if [[ "${SUPERVISOR_SOURCE_ONLY:-0}" != "1" ]]; then
  main "$@"
fi
