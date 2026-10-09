# 2026-10-08 M1 single-wheel swing reference

This is a controller-building milestone, not crossing evidence. The user
reaffirmed that obstacle crossing is the first priority; fast return to the
previous balance is measured only after a strict crossing.

## Change and verification

- Updated `m1_wbc_swing.py`: the quintic horizontal path now takes explicit
  near/far obstacle bounds and explicit approach/exit distances. It raises the
  wheel envelope before the near edge, holds the required wheel-center height
  through the complete front-to-rear envelope overlap, and only then descends.
  The lift/hold/lower phases remain C2-continuous; endpoints must leave enough
  room for the full approach and far-side landing.
- Added a one-wheel QP tracking-task adapter with measured acceleration-bias
  compensation and bounded desired acceleration. It does not create support
  forces or override WBC hard constraints.
- Test-first verification: the new whole-overlap test failed against the old
  apex-only API. Sampling then caught an overly aggressive short ramp; the
  accepted scenario uses explicit 0.25 m approach and 0.20 m exit ramps and
  checks vertical reference acceleration stays at or below 3 m/s². The focused
  WBC/strict-crossing suite reports **225 passed** and `py_compile` passes.

## Still open

- The reference/task is still not wired into any runtime call site; source
  search finds only its definition and tests. It is not yet used in a physical obstacle scene or the
  receding-horizon QP loop. A later live USD probe aligned obstacles to the
  measured M1 wheel tracks; Jacobian finite-difference validation, collision
  filtering, and the dynamic swing/support allocation remain open. See
  [track alignment evidence](2026-10-08-m1-obstacle-track-alignment.md).
- Landing target selection must prove the wheel envelope lands beyond the
  obstacle's far edge; the other three wheels must remain supporting, with no
  paired-leg lift.
- No obstacle smoke, collision/clearance/touchdown metrics, or crossing video
  was produced. Strict crossing and post-cross recovery are both unverified;
  the 3 m/s² check is a reference-shape test, not a PhysX result.
- Training remains stopped. GPU7 was observed at 10,660 MiB on the user's
  specified GPU UUID, consistent with the existing `sleep.py` placeholder;
  no training process was started and GPUs 3--6 were untouched.

## Next gate

Integrate this task into a one-environment WBC obstacle probe using actual M1
wheel-center state/Jacobian, corrected obstacle bounds, and per-wheel contact
ownership. Verify Jacobian and terrain collision filters before applying the swing task.
Then run one-wheel trials in isolation and require early lift, at least 5 cm
wheel-envelope clearance, touchdown at least 4 cm beyond the far obstacle
edge, stable support for five frames, no contact/collision/reset, and only then
measure balance recovery. Do not begin PPO retraining until strict physical
crossing passes.
