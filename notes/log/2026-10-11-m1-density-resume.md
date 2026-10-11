# M1 denser progressive terrain / current-policy continuation

## Purpose / authorization / scope

User requested higher obstacle density, explicitly selected retaining the current
policy rather than fresh initialization, then instructed restart and publication
to GitHub `m1-10-11` with README change notes. No repeated approval is needed.
Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
`pure-ppo-learning/density-exposure`; related `terminal-obstacle-space`.
Previous deployment: [persistent route repair](2026-10-11-m1-persistent-route-repair.md).

## Contract / layout

Only progressive stage1--3 geometry changes. Coordinates relative to 16m tile
center; spawn remains X=-2m. Alternating wheel tracks Y=+/- .215m, block
footprint .10 x .18m and height3/6/10cm remain unchanged.

| Stage | Count old -> new | Start X | Pitch | Last X |
| --- | ---: | ---: | ---: | ---: |
| 1,3cm | 2 -> 4 | -.6 | 1.2 | 3.0 |
| 2,6cm | 4 -> 6 | -.6 | 1.2 | 5.4 |
| 3,10cm | 8 -> 8 | -1.2 | 1.1 | 6.5 |

Stages1/2 pitch1.8->1.2 raises along-track density50%. Stage3 is NOT denser:
its old .9m pitch conflicts with nominal all-wheel landing space; moving and
spreading its eight blocks repairs that nominal budget. Stage0 stays empty;
mixed4+ unchanged. No boundary, reward, success, controller, std, initial585mm,
2048training-env or speed-error promotion changes.

585mm actual FK axle .659m, not the legacy .544m claim. Conservative wheel
XY envelope .119208m, block half-length .05m, strict far margin .04m imply
minimum nominal inter-block pitch1.037416m for rear landing with the opposite
front wheel clear of the next block. At .45m/s over five .02s frames, travel
budget .045m leaves .117584/.117584/.017584m for stages1/2/3. Last root
margin to unchanged7.25m boundary is3.711292/1.311292/.211292m before this
travel,3.666292/1.266292/.166292m after. Stage3 remains tight; actual posture,
overspeed and longer recovery can consume it. Nominal geometry is not learned
crossing or proof of dynamic recovery; this acceptance remains OPEN.

## Verification / results

- TDD against live old source, CPU-only:5 failed/3 passed/1 deselected. Failures
  are old counts and old stage3 placement. A first temporary-file run also hit
  an unrelated relative-path test; rerun excluded that source-path-only test.
- Candidate was staged only under `/tmp/m1-density-candidate-20261011`, not
  hot-deployed into PID16830. Initial38 passed/1 deselected; broader145 passed/
  1 deselected in2.50s including FK budget, unchanged mixed, persistent route,
  strict encounter, reward, recovery, curriculum and checkpoint behavior.
- Independent read-only geometry and implementation reviews: no blocking
  findings. Negative localX reaches actual authored registry/strict consumers.
- After the verified stop and production deployment:173 relevant CPU tests
  passed in3.76s (no deselection), including strict crossing, semantic layout,
  and original source-path test. This is not a full-repository passing claim.
- Native4env `probe_m1_flat_first.py --device cuda:0 --headless` exited0 and
  emitted `M1_FLAT_FIRST_RESULT`: actual heights3/6/10cm, counts4/6/8 and
  authored/native positions match; reset counts perenv4/6/8,stage0zero;
  pooled observation retains true top heights,policy shape[4,1589]. Settled
  initial recovery readiness4/4 throughout final20steps. Stage0/mixed4 reward
  unchanged. All three obstacle stages' post-slab off-lane route cost1,
  zero fabricated receipt/bonus, nonpositive final PPO reward. Six placed-pose
  neutral frames perstage had no done; minimum measured root margins
  3.666523/1.266518/.166492m. These are native integration checks, not learned
  crossing. The transient remote arrow_x.usd wait resolved without network or
  display changes. Probe exited and GPU returned below100MiB before restart.

## Deployment / current boundary

At2026-10-11T02:24:11Z model1000 was CPU verified before SIGINT only to exact
PID16830/cwd/model900 command. Process absent and GPU0 returned1MiB, then
deployed source/tests/probe. Last printed iteration1001 is not the saved
boundary; resume uses actual model1000, redoing1001 rather than fabricating a
checkpoint. File SHA256:26df6b4a1382d56c44fb7e365a5f9d8d3f630987445072928a4e22bd623f2c3c.
It contains iter1000/next1001,39finite weights,33optimizer states,16positive
finite std,stage1/streak0/window_count0. PT.last complete2048episodes:
forward pass.09326171875,17strict attempts/0success. Preserve this actual state;
layout change does not manufacture progress or erase curriculum.
Source backup:`/tmp/m1-mixed-course-before-density-20261011.py`.
Deployed geometry SHA256:7cdfff00c1700759f40c6e68ce6fb9e5120e6279c9bf5afc39f71e82baa1da3c.
Native log:`/tmp/m1-density-native-20261011.log`.
At2026-10-11T02:28:11Z checkpoint SHA/state and deployed geometry SHA verified
again. Guard confirmed no train/native/old watcher and released GPU, then
started PID17722 with1001+8999 to total10000,2048envGPU0,save100,
M1_LOAD_OPTIMIZER=1,--keep_std,flat-first. Log:/tmp/m1-ppo-density-20261011.log.
PID17722 /proc cmdline/cwd and live env freshly verified:2048env/cuda:0,
8999updates,flat-first,SAVE_INTERVAL100,M1_LOAD_OPTIMIZER1,--keep_std and exact
model1000. Runtime policy[2048,1589]/critic[2048,1592],controllerppo,
mpc_teacher disabled/imitation0. Actual iteration1001 completed,lossesfinite,
GPU0 21862MiB. Run:2026-10-11_10-28-16/bb57e7d.
TensorBoard16981 identity verified before stopping only that process; new17849
points10-28-16run,remote6006 and existing local127.0.0.1:16006/data/logdir
independently match. No tunnel/display/network/globalGit changes.
One-shot transition script has no polling/autorestart.
No old watchers/restarts and no concurrent native probe during22GB training.

## Publication / refs

Baseline Ref: `ec484c71badf562e42eaaf36ff70903c16aa4249`.
Candidate Ref: working diff, not yet committed/deployed/published.
Last Verified Ref: baseline plus candidate CPU-only geometry diff.
Key Files: `m1_mixed_course.py`, flat-first/required-crossing tests,
`probe_m1_flat_first.py`, root README and linked Go2 README, paired ai/human17.
GitHub branchm1-10-11 freshly fetched at2989eabbe09aae7b30e69eb127c130c4d088e445;
it is an ancestor of localHEAD (11ahead/0behind). Non-force publication is
possible without rewriting remote work. Old pendingm1-10-10 upload instructions
are superseded by the user's explicitm1-10-11 destination.

## Follow-up

Observe real2cm single-wheel prelift, per-overlap measured mesh-bottom clearance
>=3cm, stable far landing and strict recovery, plus video for10cm mastery.
Raw small lift delta and forward progress are not success; no-attempt NaN is
not success. Keep current-policy lineage and honest pending/completed metrics.
