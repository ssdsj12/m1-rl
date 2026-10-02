# M1 teacher control audit — 2026-10-02

Status: strict crossing gate NOT passed; do not start long training.

## Authoritative code observations

- `ame_baseline/ame_env_wrapper.py:139` substitutes teacher age as serial phase.
- `ame_baseline/m1_mpc_teacher.py:114` force-selects leg using phase-slot modulo 4. This selection does not depend on individual foot-to-obstacle distance.
- Lines 236–249 recompute the swing origin from nominal/held joints at the CURRENT root pose each frame. Fixed-height sine lift and linear world-X advance replace the MPC foot path. This is not an obstacle-conditioned landing trajectory; increasing amplitude cannot establish that touchdown is beyond the obstacle.
- Wrapper lines 142–145 supply roll/pitch but leave yaw zero. World-X advance also does not follow body heading.
- Probe line 93 unconditionally sets wheel actions to 0.10, including invalid-teacher rows. A valid teacher fraction does not establish safe executed control.
- Probe does not set a seed; prior runs started at different terrain origins. Collision counts across those runs are not controlled A/B evidence.
- Maximum world-Z wheel bottom is NOT clearance over the obstacle under that foot, nor proof of crossing or stable landing.

## Runtime evidence

Latest advance=0.22, lift=0.25, 240-step run: 239 valid steps, max one commanded leg, 31 geometry-collision steps. Named hits include FBL_knee_box and RBL_wheel. Source: `/tmp/m1_diag_adv22.log`.

Earlier advance=0.08, lift=0.25 run: one FAR_knee_box hit in 240 steps, but different randomized scene. This cannot prove a parameter improvement.

## Required next design (not implemented in this audit)

Replace free-running forced cycles with per-obstacle/per-foot encounter state: approach, lift, traverse, touchdown, verified support. Lock world-space liftoff and safe landing targets for each swing; use actual root quaternion for IK; advance phase only under safe progress/contact conditions. Select the threatened foot from terrain geometry, prevent support wheels from rolling into obstacles, and stop or route around infeasible obstacles.

Before physical comparisons, use reproducible seed/layout and record obstacle identity/bounds, selected foot, executed wheel command, relative clearance, measured contact and touchdown. Preserve separate encounter, crossing, and strict success counts. Do not suppress collision detection to pass the gate.

No training/control defaults changed by this audit. GPU7 placeholder remains running; no XLaunch/Xorg/VNC or unrelated GPU processes changed.

## MPC reference isolation

The live reference contains `foot_pos_w` and `planned_touchdown_w`. The old Cartesian override discarded both. An isolated 320-step run executing planner `foot_pos_w` produced zero geometry collisions and max tilt 0.113 rad, but only 0.056 m maximum wheel-bottom height and therefore did not meet strict clearance. Adding a fixed vertical lift to that path raised clearance but destabilized the body (tilt >0.7 rad). The planner-foot mode is therefore opt-in only; the conservative serial teacher remains the default until the planner contact schedule and M1 IK are reconciled.

The native full-joint MPC pass was also rejected: it commanded up to four legs, reached tilt >0.7 rad, and produced 18 geometry-collision steps. This confirms the current M1 single-leg adapter cannot simply be removed; it needs a per-leg planner target with a support-compatible root/stance update.

Using `foot_pos_root` transformed by the measured current body pose reduced the future-frame mismatch but still produced 11 geometry-collision steps and 0.36 rad peak tilt in 320 steps. It remains opt-in and is not promoted to the training default.

Using only MPC `planned_touchdown_w` XY with the current-root swing arc was also rejected (7 collision steps, 0.76 rad peak tilt). The touchdown reference is tied to the planner's future support/root trajectory, so mixing it with the current-root single-leg adapter is unsafe.

The isolated generic-MPC single-leg mode (planner joint target, stance hold, no Cartesian override) produced zero geometry collisions and high nominal lift, but only 58/320 valid teacher steps and 0.46 rad peak tilt. It is not a usable teacher without a support-compatible root/stance trajectory.

## Follow-up physical probes

- Added an optional forward geometry probe (`M1_TEACHER_COLLISION_LOOKAHEAD_X_M`) separate from collision-shape inflation. With the wrapper defaulted to `0.0`, it remains diagnostic only; a `0.14 m` run still had 15 collision steps and 0.263 rad peak tilt, so it was not promoted.
- Added an optional early backstep (`M1_TEACHER_FOOT_BACKSTEP_M`) so the M1 knee stays behind the obstacle while the wheel rises. One randomized `backstep=0.08 m, lift=0.24 m` run gave 8 collisions/0.312 rad tilt; another `backstep=0.12 m, lift=0.20 m` run gave 0 collisions/0.304 rad tilt, but a repeat with the same settings gave 1 collision/0.722 rad tilt. This variance is not an acceptance result, so the default remains unchanged.
- A phase-boundary refresh of stance targets was tested and reverted: it caused up to four nonzero leg targets and 0.60–0.78 rad tilt because a handoff can capture a leg before touchdown. The original fixed reset-pose stance lock is still active pending an obstacle-conditioned support/root plan.

All probes restored `/home/hexinkun/sleep.py`; no long training was started. The strict gate remains NOT passed.

## Heading/proximity follow-up

- The teacher now receives measured yaw and advances the Cartesian swing along the body heading instead of hard-coded world `+X`. A 160-step smoke reached 160/160 valid steps, one commanded leg, 0.241 rad peak tilt, and one geometry-collision step.
- The probe now gates the diagnostic wheel command on the post-safety `valid` mask; invalid rows no longer keep driving forward. A 320-step random smoke without per-leg proximity had 47 collision steps, so it was not accepted.
- Added per-leg semantic-small obstacle proximity from the scanner (0.24 m forward, 0.09 m lateral corridor) and ORed it with live geometry collision hints. A 320-step run reduced collisions to 17 with one commanded leg and 0.318 rad peak tilt; this is an improvement but still fails the zero-collision/stability gate. Wider/longer corridors and stance measured blending were tested and rejected due to increased tilt or collision counts. The proximity selector remains active at its conservative default for the next deterministic multi-seed evaluation.
