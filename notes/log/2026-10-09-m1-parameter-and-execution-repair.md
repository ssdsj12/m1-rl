# M1 parameter and actual execution contract repair

Related task: [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline ref: `0768d96`; candidate: uncommitted changes in `codex/m1-contact-crossing`.
Existing dirty changes are retained. No training or model-quality claim.

## Manufacturer versus asset

Checked https://www.genisomai.com/product-robot/m1 on 2026-10-09. Detailed table:
41 kg including batteries; 30 kg **additional payload**, not robot mass; 12 leg
motors plus 4 wheel motors; torso -30/+40 degrees (right USD axes mirrored),
hip +/-140 degrees, knee +/-160 degrees. Maximum joint torque is 180 Nm;
the page does not assign this to every joint or specify continuous ratings.
Standing dimensions 930x480x585 mm (Pro/Ultra height 595 mm). This outer size
is not the root height, hip spacing, link length, or wheel radius.

Fresh CPU inspection of the actually loaded USD: 17 bodies sum to
41.045319557 kg, metersPerUnit=1, 16 revolute joints, leg drive maxima150 Nm,
wheel maxima50 Nm. Preserve mass/inertia and these conservative authored
drive limits; do not add30kg in empty-load training or increase every motor
to180Nm. Wheel radius .095958m and .26/.28m links are model-derived, not
published specifications. Public `zsibot/genisom_model` currently lists only
zsl-1/zsl-1w, not a replacement M1 model.

Source knee limit160.485deg exceeds published160deg: planner/decoder now use
the conservative intersection and the spawned USD gets identical bounds.
Source asset remains untouched. Tests retain narrower per-instance limits
and preserve motor drive maxima.

## Reproduced execution failures and changes

1. Current-code CPU teacher->decoder->FK reproduction requested +.156m
   vertical lift on each leg; post-IK knee floor made it +.32657m with up to
   .07072m XY drift. Removed post-IK knee mutation; Cartesian segment IK now
   satisfies action/hardware/slew bounds before encoding. Unreachable full
   targets remain invalid. Eight regressions failed before, passed after.
2. Event-held wheels inherited planner forward/backward arcs and root-height
   sag. Keep latched heading-relative XY carried by the chassis, absolute
   world targetZ, and only descend after measured clearance/far-edge events.
   Reset per-row anchors at auto-reset and capture selected-leg handoffs.
   Four new moving-body/heave regressions failed before, passed after.
3. PPO runner interpolated student/teacher joints by default50%, unlike the
   physics probe. Analytic M1 counterexample: .20m requested lift becomes
   .087621m for zero student output. Selected teacher leg commands now remain
   exact; ratio chooses ownership, not geometric attenuation. Existing valid,
   finite and safety gates remain. Both production-block tests failed before.
4. M1 actor lacked wheel speeds and wheel action history. Added four named
   wheel surface speeds (m/s), expanded history12->16; leave leg positions and
   velocities12 each and exclude unbounded wheel angle. Actor45->53 and
   critic48->56; full obs1589/1592. Old checkpoint dimensions are rejected.
   AMP's separate39-D reference schema is unchanged. Fresh training required.
5. Fixed course included a5cm sphere; shared grounding buried shapes1.5cm.
   M1 small shape pool now cuboid/cylinder only with zero embed depth, so all
   six 5cm-wide obstacles expose10cm height. Shared Go2 defaults untouched.
6. Headless launcher/supervisor defaulted to main checkout, bypassing worktree
   repairs. Both now resolve their own script location. Probe and training
   apply a shared teacher-default module; legacy shell values match.
7. Safety/fallback execution permission was reused as a valid imitation label.
   Preserve raw IK validity before safety overrides; exclude fallback,
   recovery and failed-event rows from imitation and plan_valid. Keep safe
   command ownership separate. Two regressions failed before, passed after;
   the physical recheck reports32 executable rows but only27 valid references.
8. SAVE_INTERVAL100 conflicted with a300s checkpoint-only stall timeout.
   Monotonically increasing iteration heartbeats now govern liveness;
   validated checkpoints have an independent3600s deadline. Seven new tests
   and six existing supervisor tests pass. Reward probe now expects1589/1592.
9. The0.10rad Cartesian bound exposed an old timed fallback descent that
   cannot complete in32 ticks. Four arc tests failed by3.3--6.6cm. Shared
   fallback phase length128 fixes those tests without increasing slew; actual
   obstacle events still require measured clearance/touchdown, not timeout.

## Verification

Latest focused CPU suite:124 passed,1 skipped (Isaac application-dependent config
test). Includes all teacher tests, production runner assembly, action/observation
contracts, official limits/in-memory USD, six-shape course, launcher dry-run.
Commands run from `Go2Pvcnn`, AMP Python, OMP_NUM_THREADS=1; USD tests use
installed omni.usd.libs on PYTHONPATH and its bin directory on LD_LIBRARY_PATH.
Compilation of edited Python modules passes. Repository-wide diff check has
pre-existing CRLF/trailing-whitespace findings in unrelated dirty files.

Physical candidate validation is separate: bounded128-step GPU0 run,
`/tmp/m1_cartesian_m1contract_20261009_VeGI8x.log`, timeoutPID1985742. GPU7
placeholderPID1768831 remains untouched. No display/driver changes.

This run completed but FAILED crossing: strictcount0, max tilt.33767rad,
geometry collisions34steps. At first post-step sample, FBL is selected but
COM is already19.35685mm outside FAR/RBL/RAR triangle. Static force weights
[.540168887,.514981315,-.055150202] imply an impossible -22.206N RAR support
load (41.0453kg). This is a quasi-static explanation, not a full dynamic proof
or an observation before the first command. RAR unloads bystep8; rootZ falls
.555->.458m bystep27. At step27 the invalid hold still looked teacher-valid
under the old metric, now separated by item7.

Single-variable HOLD_CONTACT_BLEND=0 ablation:
- Initial64step run `/tmp/m1_support_freeze_20261009_WvRTgt.log` timed out240s
  after41steps under a separate root-owned all-GPU process. No final verdict.
- Repeated32step run `/tmp/m1_support_freeze32_20261009_TaxgD7.log` completed.
  Real observation shapes1589/1592 passed. Selected FBL bottom max19.316mm,
  whereas global max128.976mm was the wrong, opposite support wheel. Final
  tilt.443799rad, rootZ.467417m; strictcrosscount0. Freezing the other joints
  alone is not the balance fix. The0.20production blend was NOT changed on
  this evidence. Both experiments predate the shared128tick fallback change;
  their effective_environment captures the32tick setting.
- Probe now supports optional per-sample flushed JSON so timeout does not
  discard the recorded wheel/COM/force/action evidence.

No training is running. Exact bounded probe processes finished; GPU7 user's
placeholder1768831 was never stopped. Root-owned GPU process1998748 and all
other users' workloads remain untouched.

## Corrected WBC attribution (read-only independent review)

Current failure log has4 deduplicated points, one per wheel, not8 welded
constraints. Rolling transport is already present. At1ms, submicrometre gap
and measured separating velocity become large hard normal accelerations
through `max(0,-gap/dt^2)-vn/dt`. Same-state complete matrices were not saved,
so neither this nor effort slew alone is proven as the unique cause.
The shadow labelled unbounded still receives the main slew bounds; welded
versus rolling also changes tangent time constant1ms->20ms. Neither is a clean
single-variable experiment. Total friction force application moments need
verification separately from normal-contact points. Production WBC integration
and physical support/roll control remain open; do not confuse the PD teacher
repairs above with completion of dynamic WBC.

## Remaining acceptance

The missing production stage is measured load transfer BEFORE the lift.
Existing `m1_anticipatory_support`, `m1_support_observer`, `m1_prepare_gate`,
`m1_unload_gate`, `m1_load_transfer` only run in diagnostic paths, not this
teacher. Reuse per-environment PREPARE->UNLOAD ownership; do not rebuild an
unrelated gait. Preserve actual COM/forces, bounded four-leg IK root-shift,
five fresh ready frames and phase/episode reset. No kinematic root teleport.

Independent review verified the older original-SDF diagnostic
`/tmp/m1_unload_support_goal_20261008.log`:8/8 unload,159.359--159.799mm lift,
22.10--24.50mm roll, then LAND11 failed (row5 RBL8.193N). It also used phase
effort compensation and wheel hold. Merely copying its IK into production
PD does NOT inherit that result. A static anticipatory-only version already
failed during lift. Current dynamic WBC rolling also remains unverified; do
not enable it as a shortcut or certify its shadow solve as physical success.

Next: production-equivalent four-support PREPARE and measured UNLOAD gate,
then seamless selected-wheel Cartesian lift. Need four-leg physical lift/hold/roll/landing, all required front/rear
wheel-obstacle pairs, no collision, and recovery after crossing. Only then
start fresh authorized long training and check policy-only crossing, actual
teacher application ratio, collision and strict success separately.
