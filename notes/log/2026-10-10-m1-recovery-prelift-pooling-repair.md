# T306 / recovery, incremental prelift and real-hit pooling repair

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
`pure-ppo-learning/required-crossing/diagnostic-wiring`.
Baseline Ref: bb57e7d. Candidate Ref: preserved current worktree + approved repair.
Publication target: m1-10-10 (existing parent2989eab; preserve history, no force).

## Scope / contracts

User approved the three diagnosis-derived repairs and upload with update notes.
[Diagnosis](2026-10-10-m1-perception-reward-diagnosis.md),
[Chinese update list](../../docs/updates/2026-10-10-m1-ppo-repair.md).
Pure PPO2048, strict3cm per-overlap wheel-bottom clearance and stable recovery
unchanged. No MPC, action forcing, WBC, IK, servo or display modifications.

Recovery binds robot in the normal step block and raises contextual errors.
Prelift reward receives tracker high-water delta, not only the2cm event; .3
budget per encounter, world-bottom maximum + cumulative cap prevent recontact
reference changes/bobbing farming. Loaded climbing is not airborne lift.
Map obstacle bins gather XYZ of highest valid world-Z hit of winning class;
terrain-only finite average and6x16x16 dimensions retained; unknown is all-zero
semantic. Temporary observation work chunks128env, not a reduced training count.

## CPU verification

- Recovery reproduction:2failed/6passed, then8passed after binding/error fix.
- Real wrapper reward-block execution:1failed/8passed when delta kwarg missing,
  then9passed after wiring; .003m rise earns .045 with no2cm telemetry event.
- Prelift RED7failed/19passed; lower recontact reference additional RED1failed;
  final required/dynamic/strict69passed.
- Map RED26failed/4passed; final33passed. Includes3/6/10cm x7 offsets,
  classpriority, world-vs-local height order, coherent XYZ, invalid source/pose,
  chunk boundaries. CPU2048x151x151 verified5.406s, RSS increment363.16MiB;
  this is not GPU memory/performance evidence.
- Main integrated staged suite195passed2.74s. First integrated staging lacked
  scripts/go2_pvcnn source paths (4FileNotFound/assert failures); adding read-only
  source links resolved these, without changing production behavior.

Command: OMP_NUM_THREADS=1, python -m pytest -q --tb=short on
test_m1_required_crossing, test_m1_dynamic_crossing, test_m1_strict_crossing,
test_ame_observations, test_m1_recovery_runtime, test_m1_flat_first_terrain,
test_m1_obstacle_rewards, test_m1_mixed_course, test_m1_mixed_metrics,
test_m1_learning_curriculum under Go2Pvcnn/tests. Staging /tmp/m1-repair-integrated.

## Deployment / native / full suite

Independent review found no blocking new defect. Reviewer ran110passed/1deselected;
its first run110passed/1failed was the same missing staging source-path test,
which main subsequently resolved with195/195passing. Seven core/test file hashes
matched the reviewed candidate.

Bare full-repository pytest on the deployed candidate was attempted and remains
blocked by10historical collection errors (4.00s; /tmp/m1-repair-full-suite.log):

- Go2Pvcnn/tests/test_m1_sdf_probe.py: missing pxr in standalone CPU Python.
- Go2Pvcnn/tests/test_m1_teacher_obstacle_hold.py: duplicate module basename.
- tests/evaluation/test_benchmark_suites.py: missing evaluation package.
- tests/evaluation/test_manifest.py: missing evaluation package.
- tests/evaluation/test_metrics.py: missing evaluation package.
- tests/evaluation/test_model_adapters.py: missing evaluation package.
- tests/evaluation/test_protocols.py: missing evaluation package.
- tests/evaluation/test_result_writer.py: missing evaluation package.
- tests/evaluation/test_trajectory_alignment.py: missing evaluation package.
- tools/m1_reference_validation/tests/test_clone_evidence.py: missing pxr.

These match the prior required-crossing baseline; do not claim full-suite green.

PID10311 reached atomic model_500.pt; CPU weights/iter500/next501/stage1 verified.
TERM stalled in shutdown; after30s and a second exact cmdline/cwd verification,
SIGKILL stopped only10311. Checkpoint preserved, process absent and training lock
released before deployment. Backup: /tmp/m1-repair-backup.AvoxTR. No production
source was hot-patched; no concurrent GPU native probe.
The existing new-fresh run is2026-10-10_18-49-19/bb57e7d, not old8573 lineage.
Final deployed expanded regression212passed3.87s, including purePPO, dense-layout
andcheckpoint tests; /tmp/m1-repair-affected-suite.log.

Native4env /tmp/m1-repair-native.log passed100settling steps, course/reset and24
near-block reward steps; process12554 exited and GPU released before resume.
Actual PPO observation shape4x1589; actual USD heights.03/.06/.10 andcounts2/4/8.
All four environments recovery-ready for all last20settled frames with debug off.
Real raw/encoded scanner world-top respectively:
.03000259/.03000262, .06000137/.06000140, .10000229/.10000232m.
All three stages passed<=1e-4m height preservation; obstacle zone1.0, positive
reward removed, zero-action eventbonus0, no done/nonfinite. This is physical
scene/recovery/observation wiring, NOT a learned crossing/video acceptance.

Resuming from this run's model_500 with optimizer/std/curriculum preserved,
next501 plus9499iterations to10000,2048env/GPU0/save100. New log:
/tmp/m1-ppo-repaired-20261010.log. Actual PID/run verification follows startup.

Verified live PID12707, run2026-10-10_20-54-20/bb57e7d. Actual2048x1589/1592,
16actions, controllerPPO/teacherdisabled/imitation0; resume source model500,
keep_std and optimizer restore enabled. Iterations501/502 completed, GPU0
21900/24564MiB, noCUDA/OOM/traceback. Recovery-ready fraction501=.0098,
502=0; do not confuse passing nominal4env recovery with all learned-policy
poses being stable. Progressdelta printed0.0000 initially; strict rateNaN
with no completed attempts is not success. Monitor actual learning next.

Publication verified with git ls-remote:
cd638f454e65ffe3ea07256ef0eb1862d0d618c6 on ssdsj12/m1-rl:m1-10-10.
Existing2989eab history preserved; no force push. Server remains dirty worktree
HEADbb57e7d, hence run folder retains that suffix; deployed repair files are
the reviewed/published candidate. No reset of unrelated remote working changes.
No checkpoint/PT or temporary one-shot process-control scripts published.

Key Files: ame_env_wrapper.py, m1_dynamic_crossing.py, m1_required_crossing.py,
ame_observations.py, corresponding regressions, probe_m1_flat_first.py.
Result: CPU contracts and native step/map wiring verified; learned crossing remains OPEN.
Follow-up:2048 resumed process, strict outcomes/video.
