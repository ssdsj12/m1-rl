# 2026-10-09 M1 strict-event crossing hold

## Goal and observed failure

The active priority is strict obstacle passage first, with balance recovery only
after the same wheel clears the far edge and lands. No training was running.
The latest 180-step single-environment PhysX probe recorded zero strict
crossings. On the first 10 cm block (top z=0.085 m), at control step 24 the
selected wheel center was z=0.156 m, so its bottom was about 0.060 m, below the
block top; its x center was still before the far edge. A fixed 32-step event
hold could expire before measured far-edge passage. In addition, wheel-speed
scaling ended at phase 0.75 even if the obstacle-lift hold remained active.

## Change

- `serial_crossing_wheel_actions` now keeps the support/swing speed reduction
  active while `obstacle_lift_hold` is true, independent of the nominal phase
  threshold.
- The runtime now uses the strict tracker's measured target wheel as the
  selected swing leg and retains the lift hold while that strict event is
  active. The strict event ends only at far-edge success; post-cross recovery
  remains a separate action/state.
- The fixed timeout remains a stale-predictor safeguard, but cannot release a
  still-active strict geometric crossing.

## Verification and limits

- RED reproduced the missing hold argument on the speed helper.
- Focused teacher/crossing suite: **63 passed**; changed modules compile.
- This is code/CPU evidence only, not physical crossing evidence. GPU7 remains
  shared with a root-owned process at 100% utilization; the user's `sleep.py`
  placeholder remains active. No process was stopped, no GPU experiment and no
  training were started. The next gate is a bounded one-environment PhysX
  re-run once GPU7 is safe to use, then diagnose its strict crossing result.

## Strict obstacle attempt denominator

The approved design requires strict success to be reported per obstacle event,
separately from post-cross recovery. The prior accumulator exposed geometric
crossing and recovery counts, but not the number of strict obstacle attempts;
the episode-level strict rate also waits for the full course/recovery gate.

- Added a one-shot `attempt_started` event when the strict tracker first locks
  a wheel to the next obstacle's approach corridor. It is latched before a
  same-frame collision is marked failed, so collision-at-approach remains a
  failed attempt in the denominator.
- Added `strict_obstacle_attempts` and
  `strict_obstacle_crossing_success_rate = crossings / attempts`. Recovery
  success and mean recovery frames stay separate. The runner logs this rate
  independently of full-course strict success.
- RED reproduced missing attempt APIs in both the metrics accumulator and
  strict tracker. The focused teacher/crossing/profile suite passes:
  **82 passed**; changed runtime/metrics modules compile.
- This is CPU/static evidence only. No Isaac smoke, training, or GPU process
  change was made. GPU0-7 currently show active utilization; GPU7 still has the
  user's placeholder allocation. The WBC execution adapter also remains
  isolated to diagnostic scripts/tests, not wired into the production
  `get_mpc_teacher_action()` path. Physical crossing is still unverified and
  WBC runtime integration remains required by the approved design.

## WBC prerequisite recheck

- The complete `tests/test_m1_wbc*.py` CPU suite passes: **182 passed**.
- This does not close the physical gate. The existing same-state live probe
  `/tmp/m1_wbc_crossing_priority_probe.log` reports a maximum contact
  acceleration prediction error of **5.45 m/s²** and up to **0.0179 m/s**
  difference between the analytic smooth-wheel patch velocity and the finite
  difference of the sampled PhysX contact locations. The latter samples may be
  ground-side manifold points, so they are not automatically a valid wheel
  patch oracle; the mismatch must be resolved before using this model as a
  runtime controller.
- Current GPU telemetry shows GPU7 at 100% utilization with 13,859 MiB used;
  its user placeholder and a separate shared compute process are present.
  No process was stopped and no new PhysX/WBC run was launched.

## Crossing success now waits for touchdown

The approved specification requires the wheel to clear the far edge, land
beyond it, and regain safe four-wheel support before the event is accepted;
nominal-pose recovery is then measured separately. The prior implementation
latched crossing as soon as the wheel envelope passed the far edge, which
could switch the action to post-cross recovery while the target wheel was
still airborne.

- Added a separate `landing_safe` gate to `StrictCrossingTracker`. Geometric
  clearance/far-edge passage alone no longer increments strict crossings or
  starts the recovery action. The target wheel must still be beyond the far
  edge on the safe-touchdown frame; landing back on the obstacle after a brief
  far-edge excursion is rejected. Runtime landing also requires all four
  support wheels loaded, target/support load thresholds, and bounded body
  tilt/tilt rate.
- Nominal-joint-pose restoration and its stable-frame recovery timer remain a
  separate post-cross phase; this preserves the requested priority of crossing
  first and fast balance restoration second.
- TDD: the new safe-landing gate initially failed against the old tracker API;
  a separate regression test also reproduced false success when the wheel
  retreated onto the obstacle after a far-edge excursion. Both gates are now
  enforced; the focused crossing/teacher/WBC CPU suite passes: **155 passed**,
  `py_compile` passes, and scoped `git diff --check` passes.
- This is controller-state/metric evidence only. GPU0–7 are occupied (GPU7
  includes the user placeholder plus another process), so no physical smoke or
  training was started. Physical single-leg crossing and production WBC
  integration remain open; no capability claim is made.

## Existing PD-to-WBC speed-gate root-cause trace

The existing `/tmp/m1_wbc_crossing_priority_probe.log` is dated Oct 8, so this
is a re-analysis of recorded evidence, not a fresh run. The PD baseline has a
zero velocity command and exits its settle loop after only five stable frames
at a permissive `0.04 m/s` threshold. During the WBC support hold, the requested
forward damping acceleration is about `-0.044` to `-0.094 m/s^2`, while the
QP's actual `qdd_x` stays near `+1.27` to `+1.38 m/s^2`; measured speed grows
from `0.0373` to `0.0512 m/s` by tick 21 and fails the final `0.04 m/s` gate.

- A 10x effort-slew counterfactual (`200 Nm/s`) still predicts about
  `+1.355 m/s^2` in x, so the failure is not explained by the `20 Nm/s` slew
  alone.
- The base-only and safety-then-x priority shadows with the current slew bound
  also retain positive x acceleration (~`+1.37 m/s^2`). Forcing the x target in
  a separate non-applied shadow requires y/z acceleration near their bounds
  (`+2.0/-1.05 m/s^2`) and does not preserve the intended safe support task.
- Therefore do not just increase solver weights or relax the speed gate. The
  next physical investigation must establish a safe deceleration/PD-to-WBC
  transfer state (or a feasible support allocation) before the crossing phase;
  preserve the root linear/vertical/angular hard safety limits.
- GPU0–7 remain occupied and no current M1 train/probe process is running. No
  live repro was launched and no process was stopped.

## Crossing success takes priority over restoring nominal balance

- The runtime had coupled the strict crossing event to the tight roll/pitch
  and angular-rate recovery limits. That could leave the crossing phase active
  after the target wheel had cleared the obstacle and all four wheels were
  loaded on the far side, simply because the body had not yet recovered.
- Split the gate: strict crossing now records only after the same target wheel
  has cleared the far edge and the four support contacts meet their load
  thresholds. Tilt/rate and nominal joint-pose checks remain in the separate
  recovery gate; the recovery action then starts on the next observation.
- Added CPU regression coverage for loaded four-wheel touchdown, missing
  support contact, and target-wheel under-load. Recovery remains separately
  measured; passing these tests is not physical crossing evidence.
- Remote focused suite: **48 passed**; changed modules compile. No new probe
  or training was started because GPU0–7 remain occupied (GPU7 still has the
  user's placeholder plus a shared process).

## PhysX trace root cause: knee lift floor ends before the wheel clears

- Re-read `/tmp/m1_teacher_crossing_monotonic_seed0_20261009.log`; this is an
  existing GPU0 probe, not a new run. It records zero strict crossings and
  peak body tilt `0.743 rad`.
- On the first block, the selected wheel bottom was `0.066 m` at step 23,
  when it had just reached the obstacle's front envelope. By step 24 it had
  fallen to `0.013 m`, and step 25 to `-0.004 m`; it never got the 5 cm top
  clearance or the far-edge landing.
- The decisive command trace: knee target was `2.60 rad` at step 22, then
  dropped to `2.09 rad` at step 23 and `1.95 rad` at step 24, even though the
  measured obstacle-lift hold remained active. `m1_mpc_teacher.py` was gating
  its knee floor only by the fixed 72% phase cutoff; it ignored the active
  strict obstacle hold. That caused descent during horizontal overlap.
- Added `m1_knee_lift_gate`: the nominal phase cutoff still permits touchdown
  when no obstacle event is active, but a measured strict hold overrides it
  until the wheel clears. The M1 action converter uses this gate both before
  IK and when reapplying the knee floor after IK.
- TDD regression reproduced the missing helper, then the teacher/crossing
  focused suite passed: **56 passed**; all touched modules and the PhysX probe
  compile. This is a static/control-target correction only; no new PhysX run
  or training was launched because GPU0–7 are occupied by other compute, and
  the user's GPU7 placeholder remains running.
- Current process/checkpoint audit: no M1 train/eval/probe is active; the most
  recently modified M1 `.pt` found under `logs/rsl_rl` is
  `logs/rsl_rl/m1_cross_large_complex_ame/2026-10-05_18-53-03/5f94f14/model_0.pt`.
  No new checkpoint or training progress is being claimed.
