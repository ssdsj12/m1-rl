# 2026-10-08 M1 guarded numerical QP fallback

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:f0c1364. Candidate/Verified Ref:this numerical fallback commit.
Plan [active-set](../../docs/superpowers/plans/2026-10-08-m1-wbc-active-set.md).
Scope: CPU regression and native read-only zero-velocity counterfactual only.

## Root cause and rejected alternatives

Captured exact native kwargs in M1_WBC_REPLAY_INPUT; original allattached
OSQP reaches solved inaccurate. This is not evidence of infeasibility.
Variable scaling worsened other modes; exact row deduplication did not fix it.
Equality-reduced OSQP also failed a later tier. These were not promoted.
Installed quadprog with SVD equality reduction solved the captured case;
it did not solve every other mode alone, so it is a fallback, not replacement.

## Implementation and RED/GREEN

Exact native fixture stored in tests/fixtures/m1_wbc_rest_fixture.json.
Missing helper and original inaccurate result observed RED before implementation.
Primary OSQP gets .03s, fallback the remainder of overall .05s per stage.
No physical bound, residual tolerance1e-5 or task lock1e-7 relaxed.
SVD reduces dependent equalities; reconstructed solution checked against ALL
original rows. Inconsistent equalities, missing backend, exceeded budget and
invalid result return no command. Corrupt primary solutions still rejected.
Fallback native call is not interruptible; elapsed checked on return.
This is not a hard-real-time certified actuator backend.

Latest full WBC/dynamics regression:105 passed in2.19s. Includes duplicate and
inconsistent equality, fixed solution, zero-budget and captured native tests.

## Native verification

Raw:/tmp/m1_wbc_active_set_native_20261008.log; local artifacts/wbc_active_set_native.log.
Bounded --num_steps1 --wbc_snapshot --device cuda:0 --headless exited0,
completion markers present. No WBC torque applied.

- Allattached: primary solved inaccurate at8619 iterations/30.01ms; fallback
  solved in4.40ms. Full final constraint violation5.53e-7. However FAR angular
  acceleration only1.31e-5 vs target.5210613; rolling error.5210482.
  Feasible allocation is NOT successful rolling.
- FAR rearpoint released: primary solves all tiers; rolling error2.286e-7,
  constraint violation4.289e-8, released normal acceleration+.0286816,
  released force4.354e-8N. Matches previous counterfactual.
- Opposite release: valid constraints but rolling error.5210477; not accepted
  as successful rolling either.

GPU7 verified sole placeholder806527 stopped; EXIT restored867270, verified
exact sleep.py command and10624MiB sole compute. No otherGPU/process, driver,
display, source USD or default actuator changes. No training started.

## Remaining gate

Moving-state gap/slip/velocity mode validity and contact transitions, followed
by sole-owner physical stance/rolling, then all4 single-leg obstacle cycles.
Only physical trajectories/video and strict metrics can authorize retraining.
