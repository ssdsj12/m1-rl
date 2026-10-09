# LIFT torque audit and bounded pose-feedback experiment

Stage: diagnostic LIFT; parent
[T306.contact-transfer.lift-support-tracking](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref: `fef68bd`; Candidate Ref: commit containing this log.
Key files: `m1_single_lift.py`, `test_m1_single_lift.py`, `probe_m1_contact_prepare.py`.

## Investigation

Added previous applied position target, joint velocity, estimated raw/clipped
torque and configured effort limits to the physical trace. Installed IsaacLab
ImplicitActuator.compute explicitly calls its torque calculation approximate;
these are not independent measured joint torques.

Unchanged controller repeat `/tmp/m1_contact_lift_effort_20261007.log`, native0:
same stop atstep36, env3 support8.794N. All37 samples: peak estimated leg torque
61.923Nm, configured leg limit150Nm, maximum raw/clipped difference0Nm.
Thus observed data do not support effort saturation as the immediate explanation.
Do not raise gains/limits based on the earlier tracking-error magnitude alone.

## Scoped candidate and TDD

Opt-in pose_feedback counters translation and RPY change relative to frozen
measured LIFT-entry pose using unit proportional gain. Root/RPY command baselines
remain fixed at prepared values; compensation is NOT integrated. Reject errors
over25mm total translation or .08rad on any wrapped axis (reason7).
Backtrack pose and Cartesian lift progress together under existing .5rad/s joint
slew, actual M1 IK and joint limits. Existing force/pose/COM guards unchanged.

Three new tests first failed with `pose feedback missing`, then passed: zero
error parity, bounded sag/roll compensation without drift integration, excessive
error fail-closed. Focused eleven-file suite86 passed in5.08s, exit0. Same command
as [single-lift log](2026-10-07-m1-single-lift.md), with extended lift tests.
The pose-feedback flag defaults false; production training remains untouched.

## Physical result — FAILED, not a successful fix

GPU7, flat8 seed2, standing32/PREPARE100, speed.04/bound.08, dt.02,
`--lift_steps 200 --lift_pose_feedback`. Log:
`/tmp/m1_contact_lift_feedback_20261007.log`, native0, stops atliftstep24.
Env1 nonselected leg2 force8.477N<10N (reason2); all selected-wheel forces are0.
Final target rise36.8..38.4mm; measured rise -2.75..1.25mm. Final maximum tilt
.02460rad, COM margins8.56..23.06mm. Earlier unloading/lower tilt does not prove
stable lift: another support unloads and meaningful clearance is still absent.
Different target progress rates mean step24 vs36 is not an apples-to-apples
stability-duration comparison. Neither experiment is accepted.

## Resources

Exact placeholder598258 stopped/restored620471 for torque trace, then620471
stopped/restored634517 for feedback. Both native0, final placeholder verified.
No other job stopped, GPU reset, display changes, long training or push.

## Next action / remaining scope

The pose-only hypothesis is insufficient; retain optional experiment and negative
evidence, not default enable. Next child under lift-support-tracking:
`support-load-distribution` — inspect three-support force distribution alongside
measured COM during selected-wheel unloading; develop a bounded support-aware
transfer/hold that does not keep lifting into a declining support margin.
Recovery remains mandatory; do not reinterpret guard abort as recovery or relax
10N limits to pass. Full obstacle clearance/traverse/landing, collision oracle,
multi-seed video, bypass and learned policy gates remain open.
