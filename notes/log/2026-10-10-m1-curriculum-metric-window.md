# Curriculum snapshot metrics are not completed-window rates

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
`pure-ppo-learning/curriculum-telemetry-window`.
Baseline/Candidate:3cc82b3; read-only diagnosis, no source or process change.

## Trigger and procedure

At22:47CST PID14800 cmdline/cwd remained correct, iteration743 completed,
GPU21922MiB, no runtime error match. Curriculum sample_count904.9 and
pass_rate.0949 appeared lower than the previous complete window. Read the
raw TensorBoard series, curriculum gate, wrapper and runner; independently
reviewed aggregation and read the installed IsaacLab manager wiring over SSH.
No tests, native probes, stop/restart or live source modification were run.

## Evidence

- Iterations726--731: sample_count2049 and pass_rate.5480722785.
- Iteration733: sample_count9.825 and pass_rate0.
- Iteration743: sample_count904.9 and pass_rate.0948676392.
- Actual gate accumulates integer episode counts and only decides promotion
  when count>=2048. A reset batch may produce2049, which is valid.
- m1_learning_curriculum.py:90--100 reports the current incomplete window
  whenever window_count>0, otherwise the previous completed window.
- IsaacLab ManagerBasedRLEnv:356 computes curriculum, :378--379 merges its
  reset metrics into extras/log. CurriculumManager:139--140 stores term state;
  :106--113 expands it to Curriculum/terrain_levels/*.
- ame_env_wrapper.py:1369--1373 snapshots extras; on_policy_runner.py:453--458
  collects each rollout-step log. At:544--563, non-RequiredCrossing keys are
  averaged across snapshots. This creates fractional sample_count and averages
  pass ratios without episode-count weighting, possibly across window changes.

## Conclusion

The .0949 value is NOT proof of a completed-window performance collapse.
Current-window early failures can precede full timeout episodes; the observed
drop also changes the metric's window population. Actual stage/streak decisions
are made inside LearningCurriculumGate.reset:72--83 before runner logging,
so this presentation issue does not corrupt the promotion gate.

There are still no2cm prelift events or strict stable landings through745;
actual small progress deltas are nonzero. These learning limitations are real,
but must not be diagnosed from a misread incomplete-window pass rate.

## Follow-up

At the next independently necessary code deployment, separate completed-window
and pending-window telemetry and use a window identity/latest-state reduction.
Do not interrupt healthy current training solely to remove fractional logging.
For now use checkpoint curriculum.last for authoritative completed-window
evidence and do not call each plotted snapshot a complete2048-episode result.
Continue current purePPO run; no physical crossing acceptance claimed.
