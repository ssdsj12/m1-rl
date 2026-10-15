# Legal knee-boundary IK candidate steps

## Intent and evidence

Actual10cm v25 frame123/126 failed although frozen same-target optimization found solutions inside all existing limits. Current DLS rejects the whole leg when the knee component crosses its branch's near-straight boundary. It thereby discards legal ABAD/HIP progress. Baseline residual .158/.281mm becomes .047/.067mm with a legal knee candidate; no target changes.

## Alternatives

1. Constrain the knee component of each optimization candidate to its configured branch half-space, then apply existing full legality and strict residual-improvement checks (selected).
2. Shrink the entire DLS vector near the boundary: preserves direction but can prevent needed tangential ABAD/HIP progress and repeat stalling.
3. Relax residual/near-straight limits or move support targets: changes safety/task geometry and is not justified by the demonstrated feasible same-target solution.

## Contract

Only solve_constrained_ik candidate construction changes. After q+dq, if branch_sign*knee < cfg.min_knee_abs_rad, candidate knee becomes branch_sign*cfg.min_knee_abs_rad. Exact floating dtype representation is permitted by existing >= check. Never change seed eligibility, targets, cfg bounds, max32 iterations, .25rad component bound, branch/joint/workspace checks, final residual validity, outer slew/encoding/backtracking, load feedback or actual success.

Projection is part of proposed optimization step, not post-hoc clipping of an invalid final result. Candidate is accepted only if finite, whole-leg legal and strictly improving. Illegal/nonfinite seeds remain invalid; infeasible targets stay invalid. Non-boundary iterations unchanged. Use configured bound, not hardcoded .10; active eligible rows only are committed.

Fingerprint v26-ik-boundary-step identifies behavior change. No production/PPO/BC launch. Native only after tests and independent review, one unique4env10cm run with flock, full traces/video/verification/archive.

## Verification

Frozen123/126 regression must fail old solver then pass new at original.1mm. Cover fourlegs/two dtypes/both knee signs and stricter configured minima; illegal seeds cannot be repaired into valid; unreachable/no improvement cases remain invalid; prior alliterate limits/monotonicity tests still pass. Full related suite and final independent review precede isolated physical verification. CPU success never substitutes crossing and recovery.

## Authority and self-review

User direct-run/self-permit covers this scoped repair; no repeatedapproval. Existing isolatedworktree/evidence preserve; no Gitidentity edits/commits without configuredidentity. Scope self-review: no new controller/targets/safety relaxation; one numerical proposal update plus fingerprint/tests. Actual crossing remainsOPEN.
