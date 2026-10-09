# 2026-10-08 joint-state bounds comparison and missing leg speed limit

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:8751554. Candidate/Verified Ref:this diagnostic state-bound commit.
Key files:[bounds](../../Go2Pvcnn/ame_baseline/m1_wbc_joint_bounds.py),
[probe](../../Go2Pvcnn/scripts/probe_m1_contact_prepare.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-joint-bounds.md).

## Contract and tests

Read current joint q/v; intersect native/configured position and speed limits.
Derive acceleration interval from semiimplicit next-step position AND speed,
not arbitrary uniform joint acceleration1rad/s². Reject invalid/out-of-limit
state rather than clip it. Existing negative-control diagnostic box remains.
Only the additional shadow uses derived joint bounds; root acceleration box,
friction, effort, support minima and tasks unchanged. No reference/slew change.

Three tests RED then full116passed in2.62s; endpoint witnesses check both q/v
bounds, malformed state rejected, both shadow paths retained. This is a one-step
prediction, not stopping-distance viability or physical rollout verification.

## Native result

Raw:/tmp/m1_wbc_joint_bounds_native_20261008.log;
local artifacts/wbc_joint_bounds_native.log. Bounded native read-only exit0.
Original diagnostic3candidates remain rejected. Additional state-bound shadow:
- Allattached still fails inconsistent equalities; physical multipoint issue
  not hidden by state-bound change.
- FAR rearrelease valid, maxconstraintviolation7.80e-7; maxeffort12.5182Nm;
  maxlegaccel1.0942rad/s², maxwheelaccel7.5006rad/s². Predicted leg speeds
  remain<=.13613rad/s, wheel<=.64381rad/s. Position/speed excess0 against
  REPORTED backend/configuration limits (see critical caveat below).
- Oppositerelease also feasible in current stop/velocity-convergence objective,
  maxeffort16.4269Nm; this is NOT proof of good forward rolling or best mode.
No WBC efforts applied, no training or physical stance acceptance.

## Critical native-limit caveat / new dependency

Leg speed limits returned5.939047e36rad/s: effectively unset/sentinel, not a
credible physical M1 speed bound. Wheels have explicit20.842451rad/s.
Source inspection: assets/m1.py all_joints ImplicitActuatorCfg has onlyK/D;
m1_ame_env_cfg.py legs replacement setsK/D but no velocity_limit_sim, while
wheels explicitly set M1_WHEEL_SPEED_LIMIT_RAD_S. This explains the asymmetry.
Do NOT interpret zero speed-excess as certified actual actuator safety.
Leg position intervals are meaningful; numerical acceleration bounds derived
from these can be huge. Actual accepted solution is modest, but no extrapolation.

Next dependent child: explicit conservative diagnostic speed policy and total
effort-slew/sole-owner handoff, with provenance distinct from manufacturer limits.
Do not alter source USD/default training actuator configuration to hide missing
limits. Existing reference leg slew.5rad/s and root reference acceleration.05
remain reference constraints, not proof of actual motor capability.

## Resources

Verified own sole GPU7 placeholder913319 stopped; EXIT restored943133 verified
exact sleep.py/10624MiB solecompute. No otherGPU/process/display/driver changes.
Physical stance/roll, four-leg crossing, videos and policy training remain open.
