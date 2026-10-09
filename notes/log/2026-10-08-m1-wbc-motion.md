# 2026-10-08 measured contact motion before WBC actuation

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:0b73832. Candidate/Verified Ref:this live-motion diagnostic commit.
Key files:[motion](../../Go2Pvcnn/ame_baseline/m1_wbc_motion.py),
[probe](../../Go2Pvcnn/scripts/probe_m1_contact_prepare.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-motion.md).

## Purpose and contract

Before moving-state control, inspect native separation and material-point
velocity instead of assuming the warmup snapshot is exactly at rest.
Installed omni.physics.tensors impl/api.py get_contact_data documentation
confirms six buffers including per-contact separation/count/start indices.
Record all returned entries, including zero-force contacts. Existing rest
counterfactual retains its old positive-force point set and explicit scope.
The new measurement is not a contact-mode acceptance policy.

Motion uses vCOM + omega cross (point-COM) minus explicit surface velocity,
then separates normal speed from tangential slip. Fixed terrain surface
velocity is zero in this diagnostic; this is not a moving-ground default.
Nonfinite inputs, invalid owners/dimensions and nonunit normals reject.
No contact identity is inferred across frames; no patch-ID differentiation.

## Tests and execution

Four tests observed RED (missing helper/instrumentation), then full WBC suite
109passed in2.28s. Tests distinguish rolling wheel-center speed from zero
material contact speed, moving surface, slip/separation and invalid inputs.
Native bounded read-only --wbc_snapshot exited0 with completion markers.
Raw:/tmp/m1_wbc_motion_native_20261008.log;
local artifacts/wbc_motion_native.log. No WBC torque applied.

## Measured evidence (env0)

- Ten native entries rather than nine positive-force entries: one zero-force
  FAR entry duplicates the rear material location; no extra distinct location
  in this particular snapshot. Do not generalize that zero-load points never matter.
- Native separation range[-6.594e-6,+6.482e-7]m, retained unmodified.
- FAR rear location normal velocity +.0023737823m/s (separating), front pair
  -.0016524575m/s (approaching). Rear slip .002682355m/s, front .000865795m/s.
- Other wheel normal velocities positive .000392/.000787/.001557m/s.
- Maximum material tangent speed .002682355m/s.

The measured state is not the zero-velocity counterfactual. Merely imposing
zero point acceleration would not remove existing slip or closing velocity.
The next WBC child must explicitly handle velocity convergence and unilateral
impact/transition, including full velocity bias; not silently reset qdot,
expand tolerances or apply static-shadow efforts as if live-valid.

## Resource and acceptance boundary

GPU7 exact sole placeholder867270 verified/stopped by wrapper; restored889301,
verified exact sleep.py and10624MiB sole compute. No otherGPU/process/display,
driver, source USD, actuator configuration or training change.
Physical stance/roll, four single-leg crossing cycles and policy training remain
unverified. This diagnostic closes an evidence gap, not the crossing objective.
