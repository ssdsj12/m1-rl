# User-selected model300 continuation boundary

User explicitly selected model300 as the stable-forward starting policy.
This overrides the previous latest-model1400 continuation choice, but not
the unfinished equal8 native-layout acceptance gate. Parent: T306/
lift-roll-layout/native-readiness/placement-validity.

## Selection and CPU evidence

Remote search found three model_300.pt files. Select current fresh lineage
`2026-10-10_18-49-19/bb57e7d`, established by required-crossing and subsequent
model500/600 deployment records, not older12-14-11 or14-16-08 runs.
Exact file, relative to production root:
`logs/rsl_rl/m1_cross_large_complex_ame/2026-10-10_18-49-19/bb57e7d/model_300.pt`.

Read-only `/tmp/m1-validate-current-pt.py`, CUDA hidden, OMP/OPENBLAS1:

- SHA256 `4437ed429f6c2339284efb567b1dda5aabab83f59823bc376f80d23ebccdc075`.
- iter300 / explicit next_iter301;39finite weights,33finite optimizer states,
  16positive std; CUDA uninitialized.
- Architecture ame_xyz_semantic_v1_c6_s16_mha64_h16,actor1589/critic1592/actions16.
- Course stage1/streak0,pending0. Last completed2048window,pass1.0,
  velocity_error.10416679779513442,strict_attempts0,strict_successes0.
- This is prior forward-phase evidence, not strict success or fresh replay.
- Leg std .0072828424–.0134814978; wheel std .0792559236–.0832295194.
  Preserve these checkpoint values; no manual std/exploration reset.

## Runtime / follow-up

No training/native process;GPU0=1MiB. No PT overwritten or production source
changed. model1400 remains a backup. After native layout acceptance, use
**model300 / next301 +9699 updates to exclusive10000**,2048env/GPU0/save100,
M1_LOAD_OPTIMIZER1,--keep_std,course preserved, separate newrun directory.
Changing checkpoint alone does not fix the
[native diagnostic fixture](2026-10-11-m1-lift-roll-native-screen.md).
Current outcome: recovery source selected/validated, training NOT launched.

BaselineRef900f249; no new production behavior. Notes/plan/monitoring must
prefer this human-selected boundary over old model1400-only instructions.
