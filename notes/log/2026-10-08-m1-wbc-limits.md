# 2026-10-08 diagnostic speed policy and explicit-effort history contract

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:359c5d3. Candidate/Verified Ref:this diagnostic limits commit.
Key files:[limits](../../Go2Pvcnn/ame_baseline/m1_wbc_limits.py),
[probe](../../Go2Pvcnn/scripts/probe_m1_contact_prepare.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-limits.md).

## Changes and verification

Explicit name-resolved actual-speed diagnostic caps: legs.5rad/s, wheels
existing M1_WHEEL_SPEED_LIMIT_RAD_S, intersect native bounds. This is an
experimental conservative policy, NOT a discovered manufacturer leg rating.
Reference generation limits and baseline training actuators unchanged.

Pure effort interval helper intersects physical limits and previous total
explicit command +/-rate*dt. Policy plan uses20Nm/s, preserving/conservatively
extending prior feedforward rate; helper requires explicit supplied rates.
Previous tick/same episode and explicit_total ownership required. Missing,
implicit-estimate, stale/reset, nonfinite/out-of-limit history rejected.
No implicit zero initialization. Metadata is not proof of physical ownership;
caller must verify native gains/command/readback before using this helper.
Not connected to an actuator writer or a fabricated previous command.

Eight new tests RED; additional missing speedconstant import caught by AST RED
before native execution. Full124tests passed in2.48s. No GPU repair needed.

## Native source evidence

Raw:/tmp/m1_wbc_limits_native_20261008.log;
local artifacts/wbc_limits_native.log. Bounded read-only probe exited0.
Measured warmup state is still implicit-PD driven:
- Native stiffness legs800/wheels0; damping legs40/wheels5.
- get_dof_actuation_forces returns ALL ZERO while robot is supported.
- get_dof_projected_joint_forces nonzero, maxabs15.941Nm.
- cached applied_torque nonzero, maxabs27.790Nm; differs from projected.
Installed API docs describe projected force as incoming-link force projected
onto motion direction, not a promise that it equals controllable motor output.
Thus none of these reads can currently be relabeled verified explicit-total
history. In particular zero direct actuation is NOT zero total drive effort.

The live shadow remains feasible under explicit speed caps: rearrelease
maxresidual7.80e-7, predicted leg speed<=.13613rad/s, effortmax12.518Nm.
Opposite release also feasible for stop objective; allattached still rejected.
These solves do NOT include a fabricated slew history and are NOT actuation
acceptance. Next build/verify fresh-environment explicit-total initialization
and bounded continuity, rather than hot-switching the existing PD warmup.

## Resource boundary

GPU7 exactsole placeholder943133 stopped, restored982669 verified exactsleep.py
and10624MiB solecompute. No unrelatedGPU/process/driver/display/sourceUSD edits.
No WBC force applied, no training, no stance/crossing claim. Physical control
initialization, substep ownership/continuity and full crossing remain open.
