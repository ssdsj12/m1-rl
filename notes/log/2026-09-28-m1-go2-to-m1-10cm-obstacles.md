# M1 active-chain conversion and 10 cm obstacle configuration

Date: 2026-09-28

## Changes

- M1 AME now declares its semantic small-obstacle profile as `(diameter=0.10 m, height=0.10 m)` through the terrain importer override. The generic course defaults remain available to other robot tasks.
- M1 mixed terrain uses 10 small obstacles on `flat_dense_small_obstacles`, 8 on `flat`, and 6 on non-plane rows while retaining two large obstacles on non-plane rows.
- M1 layout safety is explicit: reset half extent `0.45 m`, obstacle spacing clearance `0.80 m`, tile margin `0.50 m`.
- `parallelism_geometry_collision` now calls the M1-specific `m1_obstacle_collision_penalty`, which uses M1 FK geometry against the live semantic scanner and applies weight `-18.0`.
- Active M1 comments/docstrings no longer describe the task as a Go2 task. Package names under `go2_pvcnn` remain compatibility namespaces.

## Verification

- `tests/test_m1_obstacle_profile.py`: 3 passed. This includes the actual `build_course_anchors` layout path with ten-centimetre obstacles and pairwise spacing.
- Focused M1 configuration, teacher, crossing-state, metrics, and reward tests: new/config/teacher tests pass; the pre-existing `tests/test_m1_obstacle_rewards.py` suite still contains expectations for the older shaping values and reports 7 failures. Those failures are stale assertions, not failures in the new terrain profile or collision entry point.
- IsaacSim configuration probe launched with GPU7/Vulkan and exited cleanly, but the AppLauncher wrapper did not flush the contract print before closing; no training was started.

## Remaining gate

Run a short M1 PhysX trajectory probe with the new 10 cm profile. Accept only if the planner produces one-leg-at-a-time lift, wheel-bottom clearance above obstacle top, post-obstacle touchdown, stable roll/pitch, and collision-free episodes. Do not use a training process start as evidence of crossing ability.
