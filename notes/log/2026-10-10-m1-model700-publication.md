# Persistent PPO model700 and GitHub publication

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md),
`pure-ppo-learning/required-crossing/persistent-reward`.
Baseline/Candidate: implementation0286e95, verification/deployment notes through
a7d1820. No production source, reward contract, layout, std or training process
was changed in this check.

## Checkpoint and runtime verification

2026-10-10 22:37CST: verified actual PID14800 cmdline/cwd, iteration703,
GPU0 21922MiB. No traceback/CUDA/OOM/fatal-Python log match. Same2048env
purePPO run2026-10-10_22-09-27/bb57e7d remains active. Raw TensorBoard advanced
through706; there is still no2cm prelift event, stable landing or strict success.
Maximum aggregate normalized prelift_progress_delta is0.0002363998064538464,
not proof of centimeters of lift or a completed crossing. Latest complete
window2048 episodes: pass0.505859375, strict attempts2751, successes0.

CPU-only torch.load(map_location='cpu') verified the newly saved file:

```text
logs/rsl_rl/m1_cross_large_complex_ame/2026-10-10_22-09-27/bb57e7d/model_700.pt
```

- size5,911,163bytes; iter700, next_iter701.
- optimizer_state_dict present;39 model-state entries, all tensor values finite.
- std has16 finite entries; leg dimensions roughly.0202--.0287 and wheel
  dimensions.1632--.1682. No manual std change was made.
- m1_learning_curriculum version1, stage1, streak0 and saved window metadata.

This verifies a usable saved training checkpoint, not learned crossing. No
parallel native/GPU probe, restart or process interruption was performed.

## Publication verification

GitHub connectivity recovered. Scoped diff --check passed, and only the two
previously excluded untracked watcher files remained outside commits.
Normal non-force push updated ssdsj12/m1-rl:m1-10-10 from5af7a29 toa7d1820.
An independent post-push ls-remote read returned exactly
`a7d18202f94eaeb5fe2f556fd828cdb17c49f4c9`, matching localHEAD.

The remote branch now includes implementation0286e95 (persistent strict-wheel
receipts and full-target actual prelift reward), deployment evidence1e631b6,
and raw-metric/terminal-space audit a7d1820. Previous upload-failure notes are
historical; do not keep retrying the same completed code publication. No PT
files, old watcher scripts, global Git config or network config were uploaded
or changed. This follow-up note is documentation only.

## Remaining acceptance

Continue current run; no verified10cm crossing yet. Stage1 learning trend,
early real single-wheel lift, sampled positive bottom clearance and stable
strict recovery remain open. The stage3 terminal-space candidate remains
unimplemented and must be verified before whole-course acceptance; no boundary
relaxation. Keep notifications quiet except substantive changes.
