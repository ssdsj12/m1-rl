# Bounded pose-IK seed recovery

Goal: allow a safe constrained solution to be found when a measured knee is slightly inside the algorithmic near-extension guard; this does not label that measurement safe or prove actual crossing.

Evidence: v28 frame133 measured LR knee .0975438, command .100000024. All nominal candidates reject with reason4. Selector-only seed correction restores candidate but full transaction still rejects a second nominal solve. Frozen full pose-solver correction restores133/134 with execution residual <=.1mm, while137 remains rejected at.111552mm. Runtime stays frozen until v28 audit exits and is archived.

Alternatives: (1) globally relax min knee guard: rejected, changes output safety. (2) use whole last-command vector: rejected as unnecessary ~.12rad seed differences and measurement/initialization ambiguity. (3) selected: bounded per-leg initialization helper only for pose callers; keep base IK unchanged and final output validation unchanged.

Contract: recover only finite target/seed/branch, hardware-limit-valid seed, matching nonzero knee branch, positive knee magnitude, and deficit 0<min_knee_abs_rad-abs(seed knee)<=.01rad. Change knee initialization only to signed existing configured boundary. All other joints/legs and original tensors unchanged. Larger deficit, opposite/zero branch, NaN, hardware violation do not recover. No valid flag is fabricated: original solver must pass unchanged joint, branch, workspace and residual requirements. Existing transaction still validates execution slew/encoded residual/support. Measurement and raw contact/safety gates unchanged.

Implementation: pure m1_teacher_seed_recovery.py exposes recovered_pose_seed and solve_pose_ik wrapper; m1_teacher_pose imports wrapper under existing solve_constrained_ik name so selector and nominal/execution pose paths share the rule. Base m1_teacher_ik API and active-progress helper remain unchanged. Fingerprint v29 identifies behavior; raw dynamic input records allow deterministic replay of transformed initialization. Preserve exact input when no eligible recovery.

Verification: all4legs and both dtypes, legal-input no-op, range/branch/NaN/limits rejects, immutable inputs, target residual and strict output boundary. Exact v28 frame132 remains unchanged,133/134 valid with final encoded audit;137 still invalid rather than relaxing residual. Full788+new regressions and independent final review before candidate native deployment. Actual10cm passage plus recovery remains required. No training, deletion or production deployment.

Approval: user's direct scoped execution authorization replaces repeated approval; no visualization decision needed. Self-review: bounds and default base-solver behavior explicit; no output safety change. Git identity absent, preserve docs without commit/global config changes.
