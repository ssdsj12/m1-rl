# 2026-10-08 M1 WBC ground-contact observability

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md). Stage: real
single-environment contact observability only; not stance, crossing, or training.

## Change and evidence

- Added `Go2Pvcnn/scripts/probe_m1_wbc_ground_init.py` and a source contract test.
  It creates one flat-ground M1, disables native implicit K/D before creation,
  writes/readbacks explicit zero effort, and advances only bounded raw PhysX
  ticks (never the manager action step).
- Single-env GPU7 smoke: reset wheel-center heights were about 0.09615--0.09618 m
  against the 0.095958 m nominal wheel radius. Native wheel contact forces were
  zero for the first seven ticks; all four exceeded 1 N by raw tick 8. On tick 8,
  measured wheel normal loads were approximately 101.9, 218.5, 226.4, and 217.6 N.
- This is a transient touchdown/contact-observer result, not static support:
  force is highly unequal/transient and the cached manager sensor remained zero
  because the probe intentionally bypasses `env.step`. No balance, leg lift,
  obstacle crossing, clearance, landing, or recovery was tested.
- GPU7 placeholder PID 1409284 was stopped only for this smoke, then restored as
  PID 1421919; GPU3/5 and all unrelated jobs were untouched. No training ran.
- CPU QP oracle previously failed one fixture because the OSQP stage exhausted
  the old 50 ms total fallback budget under host load. The oracle now has a fixed
  0.5 s per-tier wall-clock budget; it remains bounded and is explicitly not the
  hard-real-time controller. Full `tests/test_m1_wbc_*.py`: 142 passed.

## Next

Implement a measured same-state actuator handoff from settled support to explicit
WBC torque, with no physics tick between disabling implicit PD and applying its
measured equivalent. Verify named 16-DOF order and actual native readback, then
prove sustained four-wheel support and slow roll before single-wheel obstacles.
Do not start PPO training until strict physical crossing gates pass.

Baseline: `0768d96`; isolated `codex/m1-contact-crossing` worktree; no commit yet.
