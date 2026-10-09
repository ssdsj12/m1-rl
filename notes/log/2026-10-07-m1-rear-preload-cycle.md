# Leg-aware preload: stable short cycle, not crossing

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), load-transfer child;
remaining traction child blocks obstacle traversal and long training.
Baseline Ref:56c5518. Candidate Ref:containing commit.
Key files: m1_load_transfer.py, probe_m1_contact_prepare.py, their two tests.

## Improvement relative to previous commit

Transfer support_floor now accepts scalar or validated floating [B] reserve,
30..40N. Opt-in --rear_lift_reserve uses35N for FBL/FAR-selected rows and40N
for RBL/RAR-selected rows in both PREPARE and UNLOAD. Uniform40N previously
exceeded the front-row8cm bound; per-leg allocation preserves that bound.
Actual30N support guard, joint limits, source assets and production defaults
are unchanged. Added vector/scalar equivalence and invalid-vector tests and
AST consumer-wiring coverage. No new reactive COM feedback enabled.

## Verification

Previously observed RED vector cases2 failures and wiring1failure; final focused
suite:74 passed in13.61s, exit0. Command under Go2Pvcnn using amp Python:
`-m pytest -q tests/test_m1_load_transfer.py tests/test_m1_prepare_reserve_wiring.py tests/test_m1_moving_load.py tests/test_m1_com_trajectory.py tests/test_m1_single_lift.py tests/test_m1_settle.py`.
git diff --check clean.

Physical procedure: same GPU7/cuda0,8env seed2, M1_OBSTACLE_STAGE=none,
headless fixed-physics shoulder diagnostic,35N default, .02m/s cap/20step ramp,
90lift/.16m/.12m/s,90land/.005m search,100settle; add only rear_lift_reserve.
Raw evidence:/tmp/m1_rear_preload_20261007.log; local copy rear-preload.log.
Probe process terminal exit0; no running probe at recheck. Runtime reserve
vector[35,35,40,40,35,35,40,40].

- stopped=null; landing_complete=true; finalstep244; all8 landing streak5.
- 20 pre-action rolling samples/20 actions, minimum nonselected force34.97596N.
- Lift measured atstep90:156.408..157.767mm; row3 weak FBL entry41.6519N.
- Final selected loads53.845..65.436N, margins .03194.. .037997m,
  max absolute roll/pitch .004514rad.
- Last rolling root progress is negative .553.. .850mm: no effective traversal.
- Read-only angle audit: loaded-wheel net angles over rolling samples only
  .001286.. .003382rad, despite positive requested .02m/s plateau. This is
  not evidence of normal forward rolling or successful obstacle traversal.

## Conclusion and next action

This resolves the support-floor rejection for this bounded flat short cycle,
not the original crossing objective. Keep the per-leg preload as a diagnostic
baseline; next compare drive/contact response with measured cumulative angle
and displacement, not instantaneous qdot or merely completed phases. Original
collision fidelity, real obstacle clearance/landing/video, safe bypass and
policy-only evaluation remain open. No long training launched.

GPU7 exact own placeholder PID2567503 verified restored. No other processes,
display settings, drivers or dirty original checkout changed. GitHub upload
not claimed; prior authentication failure remains separate from code testing.
