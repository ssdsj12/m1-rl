# Wheel angle versus instantaneous velocity

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), effective-rolling-progress.
Baseline Ref: 5027237. Candidate Ref: containing commit.
Key file: Go2Pvcnn/scripts/probe_m1_contact_prepare.py.

## Procedure

Added read-only joint-position and wheel-center samples to the unchanged
180-step four-support control (gain0, damping5, flat8, physical GPU7).
Command matches [sustained rolling](2026-10-07-m1-sustained-rolling.md).
21 focused CPU tests passed in1.55s. Runtime exit0,180samples,stopped=null.
Raw: `/tmp/m1_wheel_rotation_20261007.log`.

## Evidence

Row0 wheel angle changes, sample160 minus60, rad:
[0.00110334,0.00106603,0.000891805,0.000859886].
Row0 wheel-center world-X changes, mm:
[0.00229478,0.00110269,0.00137091,0.000923872].
Angles increase slightly during drive and return near their earlier values.
Sample60 instantaneous joint speeds are already0.132..0.178rad/s before drive;
sample120 speeds0.132..0.178rad/s despite approximately stationary angles.
This is not evidence of continuous wheel rotation or a conventional spinning
wheel slip. Coarse sample velocities are inconsistent with accumulated angle;
substep/contact/solver response needs investigation before interpreting them.

## Follow-up

Inspect contact constraints and substep state/solver velocity consistency.
Asset uses4position/0velocity solver iterations; this is a candidate comparison,
not a proven cause and not changed here. Preserve physical geometry and gains.
No crossing acceptance or training. Exact placeholder2060766 stopped and
2076869 restored and verified. Original checkout and display settings untouched.
