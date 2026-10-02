#!/usr/bin/env bash
set -uo pipefail
cd "${REPO_ROOT:-/home/hexinkun/m1_rl}"
: "${VALIDATION_LOG:?Set VALIDATION_LOG to a new validation log file}"
bash Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh > "${VALIDATION_LOG}" 2>&1
rc=$?
# Isaac's native shutdown can return zero while unwinding a Python exception.
if [[ "${rc}" == 0 ]] && ! grep -qE '^(Training Complete -|M1_PROBE_COMPLETE|M1_EVALUATION_COMPLETE)' "${VALIDATION_LOG}"; then
  printf '\nEARLY_TERMINATION missing_completion_marker native_exit_code=0\n' >> "${VALIDATION_LOG}"
  rc=1
fi
printf '\nVALIDATION_EXIT_CODE=%s\n' "${rc}" >> "${VALIDATION_LOG}"
exit "${rc}"
