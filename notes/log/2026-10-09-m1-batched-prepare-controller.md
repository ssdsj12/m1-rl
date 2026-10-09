# M1 measured PREPARE controller and physical verification

Related: [T306](../todo/T306-m1-ame-long-train-stability.md),
[prior execution repair](2026-10-09-m1-parameter-and-execution-repair.md).
Baseline ref: `0768d96`; candidate: uncommitted `codex/m1-contact-crossing`.
Stage: production-equivalent PD support preparation, NOT crossing or WBC.
Contract pair: [human-17](../human/human-17-m1-execution-gates.md) /
[ai-17](../ai/ai-17-m1-execution-gates.md).

## Control contract and fixes

New `Go2Pvcnn/ame_baseline/m1_prepare_controller.py` reuses actual COM/wheel
positions, measured forces, `transfer_target`, and five-frame `PrepareGate`.
Episode/obstacle/selected-leg identities and failures are per-row. It commands
grounded four-wheel leg positions, never writes root state, never authorizes
lift. Canonical16 action encoding preserves exact leg targets and zero wheel
speed; invalid/out-of-range commands are ineligible, not clipped.

Bounds: .02m/s reference speed, .05m/s2 acceleration, .08m entry displacement.
Ready requires reference speed<=.001m/s plus measured pose/support margin and
hypothetical three-support load reserve. That forecast is NOT measured unload.
This controller is opt-in in the diagnostic, not yet an active training stage.

Review corrections:
- Direct speed-limited start/stop produced1m/s2 atdt=.02. Reuse damped
  `root_step` on `desired_root`, not an already-speed-limited increment.
- Probe closure now consumes fresh post-step evidence and reports explicit
  complete/incomplete masks; timeout is not success.
- Final ordinary update committed an unexecuted future reference. New
  `advance_reference=False` retains exact last executed root/joint/velocity.
  Readiness still consumes fresh measured data and consecutive-frame checks.
- Batched mode allows400steps/8s; legacy mode remains200steps/4s. Moving .08m
  at .02m/s already takes4s before acceleration/braking. No physical readiness
  thresholds changed. An initial400step launch was rejected by the old parser
  before Isaac startup; it supplied no physical evidence.

## Verification

Three new tests failed before finalization/budget fixes and passed afterward.
Fresh focused suite: **92 passed in9.18s**, from `Go2Pvcnn`:
`OMP_NUM_THREADS=1 /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q tests/test_m1_prepare_controller.py tests/test_m1_load_transfer.py tests/test_m1_prepare_gate.py tests/test_m1_support_observer.py tests/test_m1_com_trajectory.py tests/test_m1_unload_support_feedback.py --tb=short`.
Final `py_compile` of controller/COM ramp/probe and scoped
`git -c core.whitespace=cr-at-eol diff --check` passed. Existing unrelated dirty
files were not cleaned up or committed.

Physical conditions: GPU0,8envs, each of4selectedlegs twice, flat ground,
seed2, original production PD/geometry, no effort feedforward or solver
refinement. GPU7 placeholder1768831 untouched. No display/driver changes.

1. Initial direct-speed200step run:
   `/tmp/m1_batched_prepare_pd_20261009_2E7VgP.log`: last8/8ready,
   final margins29.61--32.22mm. Predates ramp/finalization fixes.
2. Ramped200step run `/tmp/m1_prepare_ramp_pd_20261009_WK9Kd6.log`:
   explicit incomplete6/8, rows0/4deadline while references still moving
   6.55/4.24mm/s. All forecast loads ready, no non-wheel contact force,
   max roll/pitch component .009302rad. No lift attempted.
3. Correct finalization400step run:
   `/tmp/m1_prepare_final400_pd_20261009_laz7GQ.log`, PID2205070 ended.
   `batched_prepare_complete`,8/8ready,0failed, all reasons0.
   Fresh final margins31.31--34.40mm; all wheel forces>=63.92N.
   Maximum roll/pitch component over400steps .009302rad (0.533deg);
   maximum non-wheel contact-force magnitude0. This proves PREPARE only.

Run3 invocation: `probe_m1_contact_prepare.py --batched_prepare --num_steps 400 --prepare_load_floor --max_root_shift .08 --transfer_speed .02 --headless --device cuda:0 --kit_args '--/renderer/activeGpu=0 --/renderer/multiGpu/enabled=false --/renderer/multiGpu/autoEnable=false'`.
Standard AMP/IsaacLab45 PYTHONPATH and existing EGL ICD; M1_OBSTACLE_STAGE=none.
SHA256:
- controller `c21a52e083c5024464fc36638a818948e088a884961906dd2dd92f635202f914`
- COM ramp `e39b6dcd52f2cc48a5672607ff61c076e2271ad0ed42075a4d60c3396453a115`
- probe `c9dca033490357829d44014284189fcff03096dc09538ef16ee0f052718d47ed`

## Remaining gate

Measured unload, single-wheel lift/hold/rolling, actual10cm obstacle clearance,
far-edge touchdown and recovery remain unverified in production. Do not feed
fictitious zero effort errors into the effort-owned UNLOAD gate or inherit the
older effort-assisted16cm lift result into this PD controller. Next consume fresh
contact evidence and last executed commands at the UNLOAD handoff. Full physical
acceptance must precede training smoke/long training. No training was started.
