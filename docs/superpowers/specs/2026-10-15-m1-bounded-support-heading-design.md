# Bounded support heading channel design

Parent T306/teacher/actual-crossing. User explicitly authorizes direct scoped execution without repeated approval. Objective remains real 10cm crossing and recovery, no production training.

## Evidence and alternatives
v30 removes active intent attenuation but actual wheel bottom stays near .05mm. Native frame129 yaw error .159308rad freezes progress while support and COM gates pass; frame134 LR execution IK then fails. Frozen command yaw perturbation .01rad produces exactly zero support goal response at115/120/125/128. Mode1 load-aware translation uses measured orientation, eliminating yaw together with tilt. Wheel correction alone exhibits tracking errors. This is a structural missing channel, not proof of the sole physical cause.
Increasing wheel gains is unproven and changes PD assumptions. Restoring full command orientation would reintroduce proven roll/pitch XY conflict. Select yaw-only support correction while keeping measured tilt and world-Z load feedback.

## Geometry and contract
Only mode1 with support_reference_w_z present. Compute wrapped measured yaw minus command yaw, clamp to [-.05,.05]rad. .05 is a provisional bounded experiment, not optimized or a relaxed safety threshold.
From existing completed body_goal, rotate to measured-world-relative vector. Rotate its XY about measured root by bounded yaw error; preserve Z exactly. Convert back to measured body. Apply only three support legs; active goal unchanged. Existing world-Z reference/heave/load corrections remain unchanged. Then original fraction and IK/nominal/branch/joint/rate/caller-validator gates apply. Never promote invalid baseline.
Mode0/2 and missing-height paths retain original behavior. Invalid command pose remains invalid. No new histories/integral, no PD/wheel/std changes, no gate relaxation. Frame equivariance and dtype/device behavior must hold.

## Evidence
ExecutionTarget.heading_delta defaults zero for compatibility, included by dataclass merges. Diagnostic execution_heading_delta and fingerprint v31-bounded-support-heading. Independent verifier reconstructs wrapped/clamped yaw from raw measured/command quaternions and verifies support world XY, unchanged world Z/active goal, delta, step and existing FK residual. It must not call producer helper. Tampered delta/support XY/support Z must be rejected.

## Validation
Frozen actual134 must become valid without relaxing .1mm tolerance; valid115/120/125/128 controls remain valid. Test signs, wrap at pi, saturation, yaw equality, all active legs, float32/64, modes/missingheight, invalid/nonfinite pose, global yaw/translation equivariance, exact Z/active preservation, full transaction rollback. Legacy shared-rotation tests updated only where their expected yaw insensitivity conflicts with this explicit contract.
Full regression + one fresh review before candidate deployment. v30 process must exit and source/trace/video/results archive must be SHA-verified first. Isolated same10cm slow-rolling four-env probe only, no concurrent native/training. Actual video and full events, not CPU pass, establish crossing/recovery.

## Self-review and authority
No success criterion changed. Correction is execution heading feedback, not prescribed swing or trajectory. Existing linked worktree reused. No Git identity changes/forced commit; preserve artifacts. User direct-execution authority overrides repeated design approval prompts.
