# 2026-10-08 M1 full dynamics snapshot implementation

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:7b74415. Candidate Ref:this implementation commit.
Stage: read-only WBC dynamics adapter, not actuator/control integration.
Key Files: [adapter](../../Go2Pvcnn/ame_baseline/m1_wbc_dynamics.py),
[tests](../../Go2Pvcnn/tests/test_m1_wbc_dynamics.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-dynamics.md).

User approved written design with “按此设计实施”. Existing independent worktree
verified clean before work. Baseline point-Jacobian tests:3passed.
RED:18new tests failed on explicit missing-module assertion before implementation.
GREEN:21passed (18new+3existing),1.40s, amp Python CPU, PYTHONPATH=.,
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2, pytest -q tests/test_m1_wbc_dynamics.py
tests/test_m1_dynamics.py. No GPU simulation or training launched.

Adapter reads only full generalized APIs, requires22coordinates, maps both M axes
and gravity/Coriolis vectors by16joint names. Rejects malformed/duplicate names,
truncated dynamics, nonfinite/mixed dtype, asymmetric/nonpositive-definite M,
and invalid/stale episode/step identity. Cloned output does not alias backend or
identity buffers. No deprecated fallback or silent matrix regularization.
API-boundary fixture is used without simulation; assertions use real torch matrix
operations. Sum of native compensation terms is preserved, not physically certified.

Next: native shape/frame/sign and finite-difference oracle before QP or actuator
use. Whole-body controller, rolling contact, recovery, true obstacle/avoidance and
policy-only gates are still unverified. Existing runtime defaults and human/AI
runtime documentation unchanged. GPU7 placeholder was not stopped.
