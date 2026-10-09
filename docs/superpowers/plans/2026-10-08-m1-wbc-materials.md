# M1 effective material friction implementation

Approved parent: [WBC design](../specs/2026-10-08-m1-dynamic-wbc-design.md).
Use TDD inline in the existing isolated worktree; production config unchanged.

1. RED/GREEN pure coefficient combination matching PhysX precedence:
   average < min < multiply < max. For unknown active shape among a wheel's
   shapes take minimum across every candidate combination and both static and
   dynamic coefficients. Reject absent/invalid data, do not fill guessed mu.
2. Add read-only --wbc_snapshot material audit. Create rigid wheel views before
   warmup; read live material values after startup randomization. Read bound
   USD material combine modes and ground coefficients (ground unrandomized).
   If exact native shape-to-USD order is unknown, use all-pairs combinations
   as conservative bound, explicitly mark scope. Do not assume shape order.
3. Full CPU regressions and bounded GPU7 observer capture; restore exact own
   placeholder. Log raw per-wheel properties/modes and computed bound.
4. Commit evidence/notes. This does not certify dynamic support or crossing;
   rolling acceleration constraint and stance test remain mandatory.
