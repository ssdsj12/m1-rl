# M1 four-second PREPARE and measured PD UNLOAD diagnosis

Task: [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline `0768d96`; uncommitted candidate in `codex/m1-contact-crossing`.
Key files: `Go2Pvcnn/ame_baseline/m1_prepare_controller.py`,
`ame_baseline/m1_pd_unload.py`, `scripts/probe_m1_contact_prepare.py`.
Related [previous PREPARE experiment](2026-10-09-m1-batched-prepare-controller.md).

## Correcting acceptance scope

The approved dynamic-WBC design limits PREPARE to4s. The previous400step/8s
experiment demonstrated convergence but DID NOT satisfy that deadline. Its
"physical gate passed" wording was too broad. Restore the parser to<=200steps
and controller default to200, retaining the fresh final observation. Use the
design's allowed .04m/s reference speed with unchanged .05m/s2 acceleration,
.08m displacement, .5rad/s joint limits and measured readiness thresholds.
Two deadline regression tests failed before correction and passed afterward.

Fresh GPU0 run `/tmp/m1_prepare_4seconds_pd_20261009_8PnQZL.log`:
200steps atdt=.02,8/8freshready, nofailures; final margin32.24--36.35mm,
max roll/pitch component .009302rad, non-wheel contact-force magnitude0.
This is the in-deadline PREPARE evidence, not unload/lift/crossing.

## Why a PD-only UNLOAD counterexample

The actual training execution still uses leg position/wheel velocity PD. Before
attributing poor lift solely to PPO or proposing another reward, measure whether
that execution can unload a selected wheel after the verified load transfer.
This baseline experiment does NOT replace the approved dynamic WBC design.
It does not fabricate an effort-allocation certificate for the WBC UNLOAD gate.

New opt-in controller/guard:
- Handoff clones last executed prepared root/rpy/joints/anchors and identity.
- Shorten selected leg only, <=.01m/s, <=.02m, <=100steps/2s. Do not teleport.
- Other three measured supports must each be>=30N to advance the reference;
  force<=10N, margin<.02m, pose/rate violations, stale data or collision abort.
- Selected measured normal load<=5N plus other supports>=30N and valid posture
  must persist five fresh frames; no reference-height success label.
- Native named K/D must equal legs800/40, wheels0/5 and feedforward target0.
- Final observation does not advance another action. Exact normalized16 action
  bounds checked; no extra force compensation and no lifted-wheel rollout.

## Tests and first physical result

New tests exercised selected-leg FK isolation, unchanged support references,
five measured frames, stale/collision/actuator rejection, actual decoder
roundtrip, explicit two-second timeout, no-motion negative case and support
deficit pause. Missing module/guard failures were observed before implementation.
Focused combined suite:116passed in14.46s (includes unload regression selection).

`/tmp/m1_pd_unload_20261009_xFTNeT.log`, PID2266128 terminal:
PREPARE8/8; UNLOAD0/8, allreason9deadline. At last observation:
- selected wheel load27.83--38.18N (must be<=5N);
- requested selected-wheel rise16.61--19.19mm;
- actual selected-wheel rise0.514--2.295mm;
- all other supports stay above30N; maximum tilt component .025633rad;
- non-wheel contact force0. Whole-body COM drops1.78--2.58mm during unload.

This rules out claiming that2cm of commanded shortening equals a real2cm lift.
It does NOT yet prove which share comes from base-pose drift versus joint
tracking under load. Do not increase height/deadline simply to turn this green.

## Tracking decomposition experiment

`tracking_diagnostics` decomposes last-executed-command nominal FK, the same
command at measured base pose, measured-joint FK, and native wheel pose. One
new CPU counterexample passes after first failing missing helper;8PD tests pass.
The decomposition is read-only, not a dynamics proof or controller success.
Same-input runtime `/tmp/m1_pd_unload_tracking_20261009_mIPAPZ.log`,PID2283207,
was launched to expose root pose, measured joints/position targets and projected
joint forces. Completed: same0/8 outcome,101 observations. At the final sample,
base-pose change cancels10.413--13.729mm of nominal command rise and joint
tracking cancels2.627--6.298mm; FK-versus-native delta is <=2.5micrometres.
This locates lost displacement in whole-body pose/tracking, not an FK axis
error. It remains a decomposition, not proof of a unique dynamics cause.

## Existing world-height correction: negative physical counterexample

`/tmp/m1_pd_worldheight_20261009_P8oZg1.log`, process528404 ended; session75962
returned0 but the physical gate FAILED. Same production setup, with only the
existing `--pd_unload_world_height` diagnostic enabled. Fresh36focusedtests
passed before launch (PD unload, selected world, PREPARE).
PREPARE8/8; batch aborted atUNLOAD19, not at the2s deadline. Rows2,3,6,7
rejected the reference (reason5); remaining rows are unfinished (finish reason9)
because a peer failed. Do not label their shortened histories deadline failures.
Selected-wheel loads24.70--35.19N; measured wheel-center rise0.474--2.184mm.
Nominal-FK shortening17.69--19.98mm already approaches the2cm diagnostic cap.
Pose change cancels10.54--12.63mm, tracking cancels4.69--7.21mm.
Adding selected-leg frame correction alone is not an accepted fix. No change
to clearance, gain, torque, posture, deadline or success thresholds was made.

Next investigate the approved coupled-support/WBC path. Separately, vendor
Climb pose is unresolved: localV3URDF and meshes.rar contain mechanical exports,
not state presets; protocol names Climb but does not define12leg joint angles.
585mm exterior standing height is not a validated base-link height or Climb
preset. No guessed posture installed.

All experiments use existing production geometry/PD onGPU0,seed2,8envs and flat
ground. No training, checkpoint rewrite, display/driver edit or GPU reset.
User GPU7 placeholder1768831 remains untouched. Full dynamic support/rolling,
10cm obstacle crossing/landing and policy-only acceptance remain open.
