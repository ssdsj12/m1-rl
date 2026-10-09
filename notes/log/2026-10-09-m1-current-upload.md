# Current M1 snapshot publication

## Purpose / stage / related node

User requests uploading the current version to GitHub ssdsj12/m1-rl branch
m1-10-9. This is source publication, not controller acceptance or training.
Parent: [T306](../todo/T306-m1-ame-long-train-stability.md),
execution-physical/contact-transition-consistency.

## Included changes and boundaries

Baseline eaa2c30 includes base-priority diagnostics and released material-point
acceleration correction. Current snapshot also includes two pure helpers and
their tests: contact_inventory retains unloaded approaching points, preserves
distinct moment arms and aggregates duplicate normal forces; measured_loaded
does not imply attached. near_contact_gap_constraints uses material bias and
enforces nonnegative semiimplicit gap at EVERY preview substep, not just the
terminal point. It adds no force variables or fictitious support. Frozen-state
prediction does not certify future changing geometry. Neither helper is wired
into default actuation/training in this snapshot. No runtime contract changed
by the publication itself; no GPU or display configuration changes.

## Fresh verification

Remote worktree: /home/hexinkun/m1_rl/.worktrees/m1-contact-crossing.
From Go2Pvcnn:

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=. /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q tests/test_m1_wbc*.py
```

Result:215 passed in3.81s. git diff --check clean before documentation changes.
Native diagnostic PID794230 still existed at precheck; its pending result is
NOT treated as success. Actual lift, contact transition and full crossing
remain unverified; no long training is started for this upload.

## Publication procedure / refs

Source baseline:eaa2c30 on codex/m1-contact-crossing, plus the four current
helper/test files and this documentation. Preserve existing GitHub parent
951c6e4a77d53cd6b2033bfd18e281b23c1cd855; publish an exact source tree snapshot
with a normal fast-forward push. Existing LFS robot asset is unchanged.
Check published commit and tree against local publication ref after push.
Do not import unrelated development history or include runtime logs/checkpoints.
Final publication commit is reported in the task response.

## Follow-up

Continue native contact-transition validation separately. CPU helper tests do
not demonstrate obstacle crossing. Training remains gated by physical evidence.
