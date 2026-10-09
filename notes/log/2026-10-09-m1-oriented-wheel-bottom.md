# Oriented authored wheel-bottom measurement

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), clearance metric child.
Baseline:0768d96645c86d8bb635a9f76cb110cf17d9ef78; candidate dirty
codex/m1-contact-crossing. Previous [SDK audit](2026-10-09-m1-climb-sdk-and-bottom-clearance.md).
Key files: Go2Pvcnn/ame_baseline/m1_crossing_clearance.py,
m1_strict_crossing.py, ame_env_wrapper.py and tests/test_m1_measured_wheel_bottom.py.

## Cause and change

Strict tracker previously accounted for orientation in lateral overlap but
subtracted a fixed radius for bottom height. That is not the lowest geometry
point for a tilted, laterally offset M1 wheel. Production now passes measured
body pose + authored collision vertices to the bottom calculation. Mesh local
transforms (including lateral offset) are preserved in each body frame; body
pose rather than COM pose transforms them to world space.

Minimum world Z is computed over vertices after quaternion rotation. Missing
colliders, unsupported collider type, invalid quaternion, or nonfinite geometry
raise errors rather than pretending to have measured a fixed-radius bottom.
The existing wrapper error path suppresses that frame's strict result. Legacy
analytic tracker callers retain explicit scalar-radius compatibility.
The cached geometry comes from env0 under the current replicated identical M1
asset contract; recreate the wrapper if geometry changes. This is authored mesh
geometry, NOT a certificate of cooked SDF/contact-offset boundaries. No collider,
joint controller or robot posture changed.

Convex-hull vertex reduction preserves every directional linear extremum;
no jitter, mesh decimation or collision replacement is applied. This prevents
replicating the194634-vertex raw mesh across every training environment per step.

## RED/GREEN and source-mesh verification

- New tests initially4failed: missing bottom function, missing measured-bottom
  tracker input, missing runtime wiring. After implementation31focusedpassed.
- Dense-vertex reduction regression initially1failed, then implemented exact
  hull reduction. Full targeted run52passed in52.57s:
  `OMP_NUM_THREADS=1 /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q tests/test_m1_measured_wheel_bottom.py tests/test_m1_bottom_clearance.py tests/test_m1_strict_crossing.py tests/test_m1_cartesian_teacher_execution.py --tb=short`
- py_compile on all3changed modules and scoped diff whitespace check passed.
- CPU-only original-USD loader/independent full-vertex oracle completed exit0,
  timeout180s budget. Uses installed omni.usd.libs in AMP PYTHONPATH and its
  bin/bin/deps in LD_LIBRARY_PATH; no GPU allocation or package installation.
  Each source wheel194634vertices; cached padded tensor4x2259x3. Roll0,+/-.15,.4
  rad samples agree with full-mesh independent projection exactly (reported
  maxabs0 at float64). At centerZ.235958 and roll+.15, bottoms are
  [.141874673,.139692876,.141874673,.139692876]m; fixed radius would report.14m
  for all wheels. That difference matters at a hard clearance threshold.

## SDK protocol follow-up

Protocol-1.3.0.pdf (SDK1425e65bd04173636e41146442478f35e157145d) now downloaded
and text inspected,21pages. Page6 visually confirms action/climb=爬高台;
page8 high_low is a separate command, page10 climb is state, pages20/21 expose
motion/joint telemetry. No numeric Climb pose obtained. Initial text printing
hit Windows GBK encoding; UTF8 extraction resolved it. No robot connection.

## Limits and next gate

No M1 training/physical probe was started; CPU geometry probes ended. Placeholder
PID1768831 untouched, no display edits. This verifies measurement math and source
asset loading, not live cloned-stage integration, cooked collision geometry,
actual early lift,10cm passage, touchdown or policy-only ability.

Next: obtain vendor Climb pose or settled named joint/IMU recording, validate
joint mapping and live measured-geometry readback, then physical single-wheel
lift/roll/landing. Do not replace Climb with computed extreme extension.
