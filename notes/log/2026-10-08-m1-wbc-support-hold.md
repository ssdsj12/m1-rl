# 2026-10-08 M1 WBC support hold and rolling-constraint diagnosis

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md). Scope: flat support only; no obstacle crossing.

## Evidence

- Added a regression-tested damping-target helper that uses the dynamics adapter's root-COM velocity coordinates rather than the actor/root-origin velocity. The targeted execution-adapter and contact-diagnostic suites pass: **31 passed**.
- Re-ran the GPU7 flat WBC handoff/support probe with a 60-step bound. It stopped at step 48 under the existing speed safety gate: linear speed `0.08098 m/s` versus `0.08 m/s` limit; four measured wheel loads remained `94.30–119.84 N`, roll/pitch stayed below `0.001 rad`, and angular speed was `0.0457 rad/s`.
- The target x acceleration at failure was `-0.1584 m/s^2`, while the rolling-contact QP selected `+1.1708 m/s^2`. At the initial same-state counterfactual, the full rolling model selected `+1.3936 m/s^2` with 20 Nm/s slew and `+1.2917 m/s^2` with 200 Nm/s slew; removing the effort-slew bound still selected `+1.4175 m/s^2`. The normal-only ablation reached the requested `-0.0440 m/s^2`, but it omits the required rolling tangent constraints and is **not** an acceptable controller.
- The COM-coordinate correction did not materially change the result. The current blocker is the rolling-contact acceleration/equality model or its interaction with the dynamics/contact Jacobians; do not relax contact constraints or torque bounds to hide it.
- GPU7 placeholder was restored after the bounded probe. No training was started; GPUs 3–6 were untouched.

## Crossing-first recheck (2026-10-08)

- The user's acceptance order is explicit: strict wheel-envelope crossing and
  far-side touchdown first; rapid return to the previous balance is measured
  only after that. Do not let a fast-recovery objective trade away clearance or
  touchdown.
- Revalidated the current isolated worktree and focused CPU suite:
  `pytest -q tests/test_m1_wbc_*.py tests/test_m1_teacher_clearance.py
  tests/test_m1_teacher_finite_remote.py tests/test_m1_teacher_obstacle_hold.py
  tests/test_m1_teacher_stance_hold.py` -> **202 passed**. These are unit and
  source-contract tests, not a physical crossing pass.
- Existing same-state flat-support trace shows a high-priority blocker before
  any obstacle trial: requested forward acceleration was about `-0.049 m/s²`,
  while the WBC solution selected about `+1.38 m/s²`; PhysX measured about
  `+1.35 m/s²` on the next tick. Therefore the unsafe forward acceleration is
  actually applied, not merely a reporting mismatch. The rolling-contact
  acceleration comparison also had up to `2.70 m/s²` model error in one sample.
- Current remote state: training is stopped; GPU7's exact `/home/hexinkun/sleep.py`
  placeholder is running (about 13.9 GiB reported, 100% utilization). No probe
  was started in this recheck; do not reset or terminate other GPU clients.

### Required next gate

Trace the first WBC tick from measured contact geometry/velocity through
transported contact acceleration, QP forces and generalized acceleration to
native finite-difference response. Resolve the sign/frame/rolling migration
discrepancy or prove the requested deceleration infeasible under safe support.
Do not integrate obstacle swing or start training until flat support and
controlled slow rolling are physically consistent. After that, test one wheel
against one aligned obstacle and prioritize clearance plus far-edge touchdown;
only then tune balance recovery.

## Next

Added a same-state, **not-applied** local-frame ablation. The contact-row projection regression passes, and the combined focused contact/execution/force-diagnostic suite reports **41 passed**. Removing either local tangent axis by itself still gives forward acceleration `+1.3275` or `+1.3767 m/s^2`; only removing both tangents (the invalid normal-only ablation) lets x acceleration follow the target. Therefore neither tangent axis alone explains the conflict. This narrows the cause to their joint interaction with wheel kinematics/effort bounds or a shared Jacobian/frame convention; it does not justify using a one-tangent controller.

The diagnostic shadow set was extended to compare hard x-target feasibility under native joint-effort capacity (still not applied). The focused suite now reports **47 passed**. GPU7 same-state results show:

- Hard-forcing the desired x deceleration with native effort limits is mathematically feasible (`effort_limit_ratio_max≈0.117`), but only by driving lateral base acceleration to the hard upper bound (`+2.0 m/s^2`) and vertical acceleration to about `-1.05 m/s^2`. This is not safe and is not a controller candidate.
- Increasing the effort slew alone did not fix the full rolling QP. Duplicate PhysX contact rows were confirmed and deduplicated (8 raw → 4 unique), but the physical output was essentially unchanged. Deduplication is hygiene, not the root-cause fix.
- Therefore the current divergence is in the coupled task/contact allocation and/or rolling Jacobian convention, not simply actuator torque capacity. Do not apply the forced-x shadow, drop both tangential rows, loosen contact constraints, or begin long training.

Next: audit the rolling-contact rows against measured wheel material-point velocity/Jacobian and native one-step response; resolve whether safe lateral/vertical support can be preserved while reducing forward velocity. Then rerun the bounded flat-support probe. Only after that, run a one-obstacle, single-leg crossing test with explicit early lift, top clearance, no collision, and stable touchdown. Strict crossing success is the first acceptance; quick balance recovery is optimized only after crossing passes.

## Serial crossing priority and teacher execution findings

The user clarified the priority: first complete obstacle crossing; only after crossing passes, optimize rapid return to the nominal balance. No PPO training is authorized until this physical gate passes.

- With event-hold enabled, an 800-step teacher probe still failed. It restarted after falls, reached only sequence legs `[0, 3]`, max tilt `0.798 rad`, and 43 geometry-collision steps. The prior event hold froze the serial phase and the forward command scaled all wheels together to 15%, so it could stall the base during an airborne-leg hold.
- Added serial wheel allocation: three stance wheels receive 50% of commanded forward speed during the swing; only the airborne wheel remains at 15%. The physical probe now preserves the wrapper's finite wheel command on planner-invalid frames while a crossing event is active. Focused suite: **85 passed, 1 skipped**.
- Added a per-swing-knee exception to the global joint-delta cap. It still clamps against M1's physical knee limit `2.801 rad`; stance, hip and ABAD bounds are unchanged. A regression test failed at the prior `1.10 rad` global cap and passes with the selected-knee-only path.
- The 160-step physical smoke reached wheel-bottom height `0.228 m`, but it is **not a crossing**: on episode 1, FBL was at `x=-27.588 m`, while the first block was at `x=[-27.475,-27.425] m`; the wheel had not passed the near edge, and its bottom fell below the block top before crossing. The swing knee target/measured value was `2.60/2.598 rad`, so residual lift is not the blocker. Tilt reached `0.293 rad` while the wheel was still upstream; another episode reached `0.795 rad`. The probe's strict obstacle crossing result remains `null` because it only verifies lift/landing, not edge-to-edge passage.
- A single-variable physical A/B with stance-foot world-coordinate reprojection is in progress. Training remains stopped; GPU7 placeholder is restored after every probe; other GPUs untouched.

Next: verify that stance reprojection lets the body advance while the wheel remains above the block until the wheel's full radius clears the far edge. If not, implement the approved dynamic WBC support allocator; do not tune recovery yet, start training, or count the lift-only smoke as success.

## Crossing-first priority clarification and bounded WBC retest (2026-10-08)

The user confirmed the order: strict crossing success comes first; restoring the old balance quickly is only measured after a wheel has cleared the far edge and landed. Recovery objectives must not pull the foot down early or replace a failed crossing with a good recovery score. Safety/fall limits remain hard.

- Added a test-first, configurable finite time constant for tangential contact-velocity correction. The new regression first failed because the contact helper had no such parameter; after implementation the focused WBC/teacher suite reports **206 passed**.
- This was a diagnostic candidate, not a claimed fix. The GPU7 bounded flat-support rerun (`50` settle steps, `20` applied WBC ticks, tau `0.02 s`) still failed the existing support gate at tick 21: measured speed reached `0.0512 m/s` against a `0.04 m/s` limit. Target base x acceleration was `-0.0943 m/s²`, but QP returned `+1.2728 m/s²`; next-tick PhysX x acceleration was `+1.2581 m/s²`. Thus merely softening tangential residual correction does not resolve the infeasible/poorly prioritized forward task.
- Native-effort same-state shadows show the requested x deceleration can be met only with lateral acceleration at `+2.0 m/s²` and vertical acceleration near `-1.05 m/s²`; support-first priority still gives forward acceleration around `+1.37 m/s²`. These are counterfactuals, not applied safe commands.
- Wrapper restored `/home/hexinkun/sleep.py` after the bounded probe. No training ran, and no other process/GPU was stopped. No obstacle crossing was tested or passed.

Next work should trace why the hard contact/dynamics feasible set forces the task hierarchy to trade away forward motion, then build the single-wheel obstacle closed loop with far-edge clearance and landing as its first success gate. Do not tune post-crossing balance recovery or start training to mask this blocker.

## Strict course gate correction (2026-10-08)

- Found that the prior runtime `strict_crossing_complete` did not check a
  wheel/obstacle pair or the obstacle far edge. A single episode-wide max
  wheel-bottom height plus one all-support-contact frame could be reported as
  strict success after the scan proxy disappeared. This could also release the
  teacher before a physical crossing had finished.
- Replaced that path with `StrictCrossingTracker`: each ordered obstacle latches
  one wheel on its lateral track, requires that same measured wheel to clear the
  configured top by 5 cm while over the obstacle, then put its horizontal
  envelope at least 4 cm beyond the far edge; only after 5 consecutive frames
  with landed-wheel contact, the other three supports each above 30 N, and
  bounded roll/pitch and angular rate does the event advance. Any collision
  latches failure. Episode-level strict success is only
  emitted after all six course events, keeping scan disappearance as a separate
  proxy metric.
- Moved the six obstacle anchors/diameter/default height into one profile used
  by config, teacher and reward code. This fixes the runtime mismatch where
  course obstacles were at y=+/-0.215 m but old teacher/reward fallbacks still
  used +/-0.35 m.
- Regression evidence: strict-gate, course profile, reward, teacher lifecycle,
  and crossing metric tests -> **57 passed**. All M1 tests that do not need the
  AMP runner extension or Isaac `pxr` imported -> **651 passed, 2 skipped, 4
  failed**. Those four failures are stale source assertions in unrelated COM,
  evaluation-layout, support-reserve and probe-wheel tests; none touch the new
  tracker/profile files. Python compilation passed.
- This corrects false-positive reporting; it does **not** prove the robot can
  physically cross. Training remains stopped. The WBC flat-support task still
  drives forward against a deceleration request, so the next action remains to
  resolve that controller mismatch before starting a one-obstacle physical
  trial. The GPU7 placeholder/other-client constraints remain unchanged.
