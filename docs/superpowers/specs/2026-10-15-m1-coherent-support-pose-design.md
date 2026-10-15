# Coherent support-pose execution — v36 isolated design

## Goal and authority
Actual slow-moving10cm crossing and return to original pose, not static leg motion.
User explicitly authorized support/IK redesign and direct run without repeated permission.
No production/BC/PPO, PD/physics/safety relaxation, PT deletion, global configuration or Git identity changes.
Existing isolated worktree and SHA provenance retained. No visual design question.

## Verified diagnosis
v35 FAILED_DIAGNOSTIC,0success. Immutable archive1b201cc0fd4193f270f9cb2b72a07214d7274a47b9c0506754251dd3b0558099.
Frozen frame130 selected tilt -> level with fixed other inputs gives execution body_goal difference0.
Old v25 intentionally discarded full rotation XY because XYZ was already split by support-height override; restoring only XY would repeat that defect.
Current geometry predicts a tilted rigid body but executes translation plus captured Z and indirect differential load preference.
CPU frozen full transaction comparison at frames119/125/130/138 removing height/origin/heave execution overrides while retaining load offsets:
valid all4, execution fractions .46875/.453125/.40625/.140625, max joint target step .04894572/.04852927/.04983795/.04795063rad.
All reported IK residuals <.0001m. Script compare_coherent_execution.py in v35 ledger.
These are single-frame counterfactuals, not physical trajectories or proof that load support improves.

## Alternatives and selected architecture
A: expand candidate attitude/gains, rejected: doesn't fix prediction/execution mismatch.
B: directly restore rotation XY but retain captured-height override, rejected: repeats v24 inconsistent rigid transform.
C: optional coherent XYZ support geometry plus bounded load correction, chosen for isolated falsifiable experiment.
This is a replacement of competing channels in the opt-in path, not another correction added on top.

## Opt-in contract
New TeacherConfig coherent_support_pose: bool=False. True requires bounded_crossing_attitude, slow_rolling, load_feedback.
Fingerprint v36 includes flag. Probe CLI --coherent-support-pose explicitly propagates config/source/raw contract. No default or production change.
During LIFT/PASS/RESTORE coherent mode:
- Support base body targets are Rd^T*(wheel_anchor_world - desired_body_position) using full requested/feedback-command quaternion Rd.
- Active LIFT/PASS wheel remains measured-body transform Rm^T*(active_world_target-pm); its world intent/progress gates unchanged.
- Apply existing bounded zero-sum load offset through Rm^T*[0,0,offset] with its original single-fraction accounting.
- Do not pass support_reference_w_z/support_capture_root_z/support_heave to execution builder in coherent mode.
- Do not add indirect attitude preference to propose_load_feedback in coherent mode: selected full rigid orientation already commands posture. Retain load-only target/offset caps/rate/projection and actual input validity.
- Therefore do not capture/commit new support height, heave, or attitude-error baseline histories in coherent mode. Archived legacy path remains exact.
- Existing full-pose builder when no height context already implements base geometry; avoid duplicate geometry implementation.
- RESTORE uses original captured yaw/level/nominal posture, existing bounded offset return and original recovery receipt; no new tilted recovery baseline.

Physical candidate pose is still an ideal reference, not measured support. Load offsets and actuator compliance mean predictions remain estimates; actual support/collision/progress always authoritative.
Maintain nominal IK plus executed IK, branch/knee/rate/encoding, rollback, duplicate frame, row reset, measured load>30N, physical failure, actual crossing and stable recovery.
No early physical gate bypass to make a frozen test pass.

## Validation requirements
1. Failing regression establishes that true coherent config is unavailable, then direct orientation changes all expected support axes while active world intent unchanged. Scalar independent transform, four active legs and float32/64.
2. Frozen v35 full transaction comparison must be encoded as regression with actual field/config integration, not monkeypatch deployment. Target step <=.05rad, residual <=.0001m, named actual encoded targets.
3. Legacy flagsfalse exact. Invalid boolean/dependency flags reject. Final encode reject rolls back all new-mode state. Duplicate/peer reset correct; RESTORE level/original baseline.
4. Probe independent execution audit must use scalar full rigid geometry + selected load offset and selected beta, not merely repeat producer. Reject mutation to support XY/Z or silently passed legacyheight. Replay and source fingerprint must agree with flag.
5. Relevant full1024+new tests, honest bare collection limits, one final independent review.
6. Deploy only isolated candidate after no live train/native/test; snapshot v35 runtime and archive. New prefix first-obstacle-coherent-pose-v1 under kernel flock, same4env/seed101/10cm/video.
7. Read terminal result + raw same-env timing + video, archive originals. Only actual lifted passage and post-cross recovery can close goal. If failure, compare actual target/load sequence without blind gain increase.

## Self-review
Coherent mode replaces height/heave/attitude branches together because keeping any duplicate direct posture channel defeats coherence. It does not remove load limits or success criteria. Supports' full transform can change XY direction relative to translation alone; unlike v24 its Z is no longer overwritten. Actual safety/performance remains unproven and requires isolated run.
Direct-run approval waives repeated question/spec approval, not tests/review. No Git commit required under preserved constraints.
Implementation plan next; production runtime currently v35 unchanged.

