# M1 numerical fallback for dependent contact equalities

Parent [WBC design](../specs/2026-10-08-m1-dynamic-wbc-design.md).
Inline TDD, no physical threshold or task objective changes.

1. Capture exact native solver kwargs for deterministic CPU replay.
2. Diagnose raw/scaled/duplicate-removed OSQP and equality-reduced variants.
   Do not promote variants that worsen other cases. Original allattached failure
   is numerical, not proof of infeasibility.
3. Installed quadprog active-set plus SVD equality reduction solves original
   failingcase. Add regression fixture and tests before implementation.
4. Reserve fallback time: OSQP limit.03s, independent active-set on non-solved
   status only within remaining overall.05s stage budget. Keep primary backend, original full constraints/residual
   check1e-5 and tasklock1e-7. No fallback after detected corrupt solution.
   SVD machineprecision rank, equality consistency1e-8. Reconstruct and validate
   against full original rows; no limit clipping or tolerance relaxation.
5. Record timing after native noninterruptible call; reject overbudget and do not
   claim hard real-time certification. Existing outer native timeout remains.
6. CPU/native replay regressions, notes/evidence. No WBC actuation or training yet.
