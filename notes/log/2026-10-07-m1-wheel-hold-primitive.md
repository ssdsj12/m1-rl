# Bounded longitudinal wheel-hold primitive

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), stationary-anchor child.
Baseline Ref: faaba5f. Candidate Ref: containing commit.
Key files: `Go2Pvcnn/ame_baseline/m1_rolling_speed.py`, `Go2Pvcnn/tests/test_m1_wheel_hold.py`.

## Purpose and scope

Implement the bounded stopped-wheel part of the approved contact-crossing design.
Previous physical evidence remains UNLOAD0 rejection after 24..39mm backward
wheel drift. This change supplies a pure command primitive only; no runtime
caller, physics parameters, training or default behavior changes in this commit.

## Contract

Input fixed entry wheel anchors, measured wheel positions, current body yaw,
previous wheel command and control dt. Project position error onto longitudinal
heading; proportional gain 2/s, speed cap 0.04m/s, slew 0.2m/s2. Return four
named-order linear wheel speeds per environment, not angular joint velocities.
Never relatch anchors to measured drift. No lateral holonomic command. Reject
nonfinite, mismatched shapes/devices/dtypes and out-of-range previous commands.
Runtime must separately validate wheel effort/contact and phase transitions.

## Verification

CPU amp Python, `PYTHONPATH=. python -m pytest -q tests/test_m1_wheel_hold.py
tests/test_m1_rolling_speed.py`: RED five AttributeErrors for missing helper;
GREEN 16 passed in 1.46s. New tests cover backward-error sign, yaw projection,
speed cap, acceleration/braking, environment/wheel isolation and invalid input.
35mm backward error initially produces +4mm/s at20ms, bounded at40mm/s.
This is a command calculation test, not a simulated or physical stability result.

## Next physical gate

Integrate opt-in PREPARE holding in the existing diagnostic only, checking
predicted native wheel PD effort against unchanged limits and logging actual
anchors/commands. First compare 100PREPARE steps on the same SDF128,1mmrest/
2mmcontact,8envseed2 candidate. Keep25mm frame bound. Before fullcycle, implement
continuous braking/selected-wheel unloading, release duringROLL and transported
anchor retention afterROLL; do not abruptly zero a nonzero holding command.
Preserve four-leg coverage, all contact/pose/slew gates and original envelope.
Obstacle, landing, avoidance, video and policy-only acceptance remain open.

## Resource and delivery

Verified placeholder3190750 still live; no training/probe live at entry. No GPU
job stopped or launched. Original dirty checkout untouched. Notes synchronized.
Local commit only; not uploaded. Compared with faaba5f: a tested bounded
correction primitive now exists, but physical drift is not yet fixed.
