# Placement diagnostic repair: loaded reference, not unloaded nominal pose

Parent: T306 / lift-roll-layout / native-readiness / placement-validity.
User requested diagnostic repair, after selecting current-lineage model300
as the next learning baseline. BaselineRef `900f249`; candidate is the
diagnostic-only diff in this change. No production reward/controller/terrain
selector, std, initial stance or strict success threshold was changed.

## Cause and bounded fix

The original native test compared gravity-loaded measured joints/root to
unloaded nominal FK: root 2cm / joint .04rad absolute limits failed in both
the first recovery placement and the empty-spawn control, at the same tick.
The historical [585mm stance check](2026-10-10-m1-585mm-stance.md) also records
loaded settling. This does not establish obstacle-induced extrusion.

The repaired diagnostic compares complete, same-target, same-sampling measured
trajectories with empty-ground controls in the same four environments. Keep
absolute errors in the raw record. The original 2cm / .04rad / 5deg limits
now constrain **additional paired displacement**, not common loaded settling.
Do not subtract scalar error norms: compare displacement/joint vectors and
normalized relative quaternion angles.

A reference is usable only if every frame is finite and geometry/clearance
safe, its last five frames have the specified grounded/unloaded wheel support,
and the last-five ranges are <=1mm root, .005rad joints and .005rad orientation.
It must also stay within existing recovery envelopes (root height .08m,
joints .15rad) and 2cm horizontal drift / 5deg orientation. These are rejection
guards on diagnostic controls, not new PPO recovery criteria. A rotating,
unsupported, colliding, mismatched or malformed control never certifies a
candidate. All early collision/clearance evidence remains; no transient is
discarded to obtain a pass.

Final outcomes distinguish incomplete samples, invalid fixture, candidate
placement failure and verified placement. A controls-only run always has
`accepted=false`. Full acceptance requires 96 recovery and 120 fold cases;
empty arrays cannot pass. Neither this diagnostic nor static placements
produce PPO data or demonstrate policy crossing.

## TDD / independent review

Selected regression command: CUDA hidden, OMP/OPENBLAS1,
`PYTHONPATH=Go2Pvcnn:Go2Pvcnn/rsl_rl`, remote Isaac Python, pytest `-q --tb=short`:

- `test_m1_lift_roll_probe_checks.py`, `test_m1_lift_roll_authoring.py`,
  `test_m1_fill_roles.py`, `test_m1_lift_roll_layout.py`, `test_m1_course_registry.py`,
  `test_m1_flat_first_terrain.py`, `test_m1_required_crossing.py`,
  `test_m1_strict_crossing.py`, `test_m1_dynamic_crossing.py`,
  `test_m1_persistent_crossing_reward.py`, `test_m1_persistent_route_penalty.py`,
  `test_m1_obstacle_rewards.py`, `test_m1_learning_curriculum.py`,
  `test_m1_recovery_runtime.py`, `test_m1_dense_forward.py`,
  `ame_baseline/test_ame_runner_checkpoint.py`,
  `test_semantic_course_curriculum_layout.py` under `Go2Pvcnn/tests/`.
- Initial paired cases: RED 8 failed / 7 passed; GREEN 15 passed.
- Review found reference angular stationarity omission and non-normalized
  quaternion angle. Both reproduced RED (2 failed / 18 passed), then fixed;
  GREEN 20 passed. Additional invalid finite/sampling controls covered.
- Outcome classification: RED 5 failed / 20 passed, then GREEN.
- Final selected suite **232 passed in 4.00s**; native script `py_compile` passed.
  This is not the full repository suite.
- Independent review confirmed both findings closed; no remaining blocker
  in that diff. Native readiness is a separate result below.

## Native evidence, preserved separately

All probes use the isolated `/tmp/m1-lift-roll-candidate-20261011` source,
production kernel flock and 4env/GPU0. Each launcher checks no training/probe
and GPU<100MiB first; no training overlapped. No historical logs overwritten.

First calibrated full-manifest run: log
`/tmp/m1-lift-roll-native-calibrated-20261011.log`,
SHA `ccc54b7ac6c14fdad217b1cb1e36a8e7edaa554d7deb66d05c765de670d4170a`.
6552 physics ticks across four environments, 225 cases including controls.
All 3 stages x 20 columns matched actual 8 targets +70 fills; scanner fill hits
2078–2079/env; policy shape4x1589; stage0/mixed reset checks reached.
All **96 recovery placements** passed paired pose/geometry/support and existing
runtime recovery readiness. No recovery receipt fabricated. Minimum recovery
XY margin .002197638m, non-wheel force0. This removes the original first-point
nominal-pose blocker; it does not certify dynamic crossing.

The 120 fold placements did not pass: their 8-tick/40ms empty-ground controls
were not stationary/supported for the final five samples. At the first left
control, loaded minimum wheel-top clearances were 25.846 / 30.418 / 26.506mm
for 3/6/10cm heights. These values are measured minus a virtual target top on
empty ground, not evidence of collision with an actual target.
Current-checker CPU re-evaluation of all raw frames is archived in
[calibrated audit](artifacts/2026-10-11-m1-calibrated-native-audit.json).

Single-variable follow-up changed only fold sample duration from 8 to56 ticks
(280ms), retaining identical targets, actuators, dynamics and thresholds.
Log `/tmp/m1-lift-roll-reference56-20261011.log`,
SHA `eba561a195b4c938662e0b8d4bff41a8644245c1259c8c290760d1506e5377e3`.
504 ticks across4env / nine controls, completed. All three loaded recovery
controls valid; all six static fold controls invalid: final-five support all
false, root range5.86–9.70mm, orientation range.01075–.02409rad. A previously
supporting wheel lifts while the selected folded wheel descends; non-wheel
force remains0 and empty-ground XY margin remains >.208m. Thus merely waiting
longer does not make this unbalanced static fixture a valid three-wheel rolling
test. Do not alter stiffness, initial stance or success thresholds to force it.
[Control audit](artifacts/2026-10-11-m1-reference56-audit.json).

Reproduction / reclassification script:
[paired-probe-audit.py](artifacts/2026-10-11-m1-paired-probe-audit.py).
Use `CUDA_VISIBLE_DEVICES= PYTHONPATH=Go2Pvcnn python <script> <raw-log>`;
it records raw and checker hashes and does not start simulation.

## Remaining gate / continuation

Final full-manifest rerun, completed by 2026-10-11 05:09 UTC:
`/tmp/m1-lift-roll-native-final-20261011.log`,
SHA `d18d57379c31bd1db0247b17a429d5552accadb11c68d85b21b447502aa6688c`.
Final checker SHA `8a0408c0999252b7acdf65417c394ae00de9fe5f3f2b0245d3add23934a694b8`.
225 cases, 12600 measured physics ticks / 50400 environment-frame samples.
All96 recovery cases again verified/runtime_ready; max paired root difference
.000590072m, joint difference .001677196rad, minXYmargin .002197638m,
non-wheel force0. All120 fold cases remain unverified with invalid controls.
Do not hide candidate measurements: as the unsupported fixture tilts, its
minimum support-circle XY margin becomes -.011535272m and measured target
clearance reaches -.060361437m. These failures require valid dynamic/support
investigation, not subtraction or a successful-layout claim. Final result
`assessment=inconclusive_fixture, accepted=false`, followed by the explicit
incomplete-acceptance assertion, not an unexpected simulator crash.
[Final CPU-rechecked native audit](artifacts/2026-10-11-m1-final-native-audit.json).
Launcher4486 and its native child exited; GPU0 returned to1MiB. No train was
started. Independent final code review found no new Critical/Important.

Diagnostic common-mode-pose and outcome-classification bugs are repaired.
OPEN child `native-readiness/three-wheel-fixture`: need valid supported dynamic
evidence for the approved lift-and-roll action. An unbalanced manually placed
static pose on empty ground does **not** prove the layout or action impossible;
nor can invalid controls certify the new layout. Native acceptance and2048
capacity remain incomplete, so production is not selected or training resumed.

Selected continuation remains [fresh-lineage model300](2026-10-11-m1-model300-restart-selection.md),
next301 +9699 to exclusive10000,2048env/save100/optimizer/std/course preserved.
model1400 remains an untouched backup. No need to reapprove count/action or
the selected model. No swing/controller/IK/teacher/servo was added.

Key files: `m1_lift_roll_probe_checks.py`, `probe_m1_lift_roll_layout.py`,
`test_m1_lift_roll_probe_checks.py`, README and paired execution-gate notes.
