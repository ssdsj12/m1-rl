# 2026-10-08 M1 obstacle-to-wheel-track alignment

This is scene geometry verification, not a crossing demonstration.

## Root cause and correction

The live one-environment USD probe measured wheel-center tracks at
`y=+0.2152 m` and `y=-0.2152 m`. The old course anchors were at `y=+/-0.35 m`.
With a 4.65 cm wheel thickness and 5 cm obstacle width, their lateral center
offset was about 13.5 cm, leaving roughly 8.7 cm between the wheel envelope and
obstacle. The course comment claiming that these blocks were under a wheel
track was wrong; the original layout did not reliably require a wheel to cross.

Changed the six alternating small-obstacle anchors to `y=+/-0.215 m`, retaining
the 0.55 m longitudinal pitch. The red regression test now checks these against
the measured wheel tracks and ensures the opposite track remains clear.

## Physical geometry evidence

- Live single-env stage contains exactly six small obstacles at x=`0.55, 1.10,
  1.65, 2.20, 2.75, 3.30 m` and alternating y=`+/-0.215 m`.
- For each block, the wheel/obstacle lateral envelopes overlap by approximately
  48 mm; the opposite track retains approximately 382 mm lateral clearance.
- The report is strictly `crossing_scene_geometry_only_not_crossing`: no
  actuator commands or movement were applied. Scene geometry is now aligned,
  but early lift, vertical clearance, far-side landing, collision-free contact,
  stability, and recovery are still unverified.
- Measured world bounds show five objects at 10 cm height and one at 5 cm. The
  latter is preserved and must be evaluated using its actual USD bounds rather
  than assumed 10 cm metadata.
- Focused tests: **173 passed** across the M1 WBC and obstacle-profile suites.
  GPU7 placeholder was restored at 10,660 MiB; no training was started.

## Next gate

Use actual USD bounds and the corrected route in a one-wheel physical crossing
probe. First establish the selected wheel Jacobian and three-wheel support;
then apply the swing task and evaluate pre-contact lift, vertical wheel-bottom
clearance, landing beyond the obstacle, and absence of collisions. Only after
strict crossing passes should recovery be tested or PPO resumed.
