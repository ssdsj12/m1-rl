# Dense PPO zero-crossing diagnosis

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md),
pure-ppo-learning/forward-progress-regression, related prelift-repeatability.
User requested diagnosis, not a reward change or training pause.

## Procedure and conditions

Read deployed strict/dynamic trackers, wrapper, metrics and required-crossing
reward gates; compare raw TensorBoard scalars with stdout and the current
model600 complete-window audit. At 06:50:42 UTC PID4921 was still training
2048 environments on GPU0, run2026-10-11_13-17-21/bb57e7d, stdout651,
21868MiB GPU memory. Losses finite; stage1 (3cm obstacles). No native probe.

## Evidence through iteration651

- Raw prelift_events total2281:18/615/1420/228 in ranges301–400,
  401–500,501–600,601–651. These are events, not unique robots or successes.
- Strict obstacle attempts cumulative76373; strict crossings/recoveries and
  stable_landings all0. Do not sum cumulative metric snapshots.
- In those ranges mean selected-target overlap samples per update were
  25715.65/21238.11/10070.29/181.078. Mean normalized route costs were
  .538015/.664224/.798853/.880291; this is not a percentage of detouring robots.
- All updates with overlap samples had minimum bottom-minus-top clearance
  below+.03m. Recent601–651 minima ranged-.035276 to+.004401894m;
  7/51updates had no samples (NaN), not passing clearance. A minimum proves
  some inadequate samples, not that every attempt failed identically.
- Current model600 last completed2048 episodes had forwardpass0,
  3106strict attempts/0success. This means none met the full forward-distance
  criterion, not that every robot was completely stationary. See
  [checkpoint audit](2026-10-11-m1-dense-model600-window.md).

## Gate diagnosis and limits

Prelift needs one unloaded wheel at least2cm above its last loaded bottom
with the other3 loaded. It does not establish continued support, clearance
throughout overlap, or safe far-side landing. Stage1 requires wheel bottom
approximately6cm above flat ground (3cm top plus3cm clearance).

Strict crossing event is counted before nominal-pose recovery: valid measured
clearance plus far-edge passage and safe touchdown must occur first. Five-frame
recovery gates cannot alone explain zero crossing events. Failure can latch
on low overlap clearance, no early lift, lost three-wheel support, collision,
or premature touchdown. Aggregates cannot link the2281 early events to their
individual failure reasons. Proxy crossing_success_rate~.01366 is a separate
scanner/history proxy, not a strict result.

CPU-only deployed tests: test_m1_dynamic_crossing.py, test_m1_strict_crossing.py,
test_m1_mixed_metrics.py, test_m1_crossing_metrics.py:50passed in1.92s.
Synthetic valid crossings can count independently of later nominal recovery.
Dynamic tracker and wrapper byte hashes match local. Strict tracker/metrics
hashes match after CRLF-to-LF normalization; no semantic drift found there.
This validates tested wiring, not physical learned crossing or all possible bugs.

## Result and follow-up

Confirmed incomplete crossing sequence with inadequate-clearance samples and
forward-task regression. Increasing avoidance/low advancement is a hypothesis
supported by reduced overlap exposure and increased route cost, not a proven
per-frame motion cause. Child forward-progress-regression/attempt-failure-trace
OPEN: obtain current-policy per-attempt frame traces to distinguish low entry,
support loss, early touchdown and lateral departure. Native replay requires a
safe checkpoint-boundary pause and must not run beside22GB training. This turn
did not pause training, change reward/controller/std/contracts, or start replay.

Baseline/Candidate Ref:6960a4b deployed feature, no production diff.
Current Work Ref:codex/m1-ppo-repair-upload, localHEAD b244024 plus monitoring notes.
Key Files:Go2Pvcnn/ame_baseline/{m1_dynamic_crossing.py,m1_strict_crossing.py,
m1_crossing_metrics.py,m1_required_crossing.py,ame_env_wrapper.py}.
