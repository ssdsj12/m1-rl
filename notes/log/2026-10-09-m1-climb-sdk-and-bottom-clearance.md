# M1 Climb posture and bottom-clearance audit

Related: [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline0768d96645c86d8bb635a9f76cb110cf17d9ef78; candidate existing dirty
codex/m1-contact-crossing. Stage: posture source and clearance contract.

## User requirement and vendor evidence

Use the existing climbing-high-platform posture, NOT maximum extension.
SDK https://github.com/zsibot/genisom_robot_sdk revision
1425e65bd04173636e41146442478f35e157145d inspected via GitHub/raw:
Chinese API/types/capability docs, sdk_client.hpp/sdk_type.hpp and
example/control.cpp/data.cpp. Climb() corresponds to MOTION_STATUS_CLIMB(8),
distinct from Stair(9) and HighLowStance(1). Inspected files expose commands,
not numeric Climb body height/joint presets/controller implementation.
Repository tree has public headers/examples and compiled libraries.
Protocol PDF web extraction failed; PDF contents remain unverified.

SetJointStateConfig(true)/OnJointStateData provides named positions/velocities/
efforts. SDK fl/fr/bl/br1..4 ordering, axis signs and offsets require validation
against USD before reuse. MotionData.position is odometry, not automatically
ground-relative height. ACK is not completed posture evidence: require Climb
state and settled joint/IMU samples, or a vendor numerical pose specification.
No SDK executable, robot connection or robot motion command was run.

New child T306/climb-posture-source remains OPEN: obtain actual preset/capture,
verify mapping, then apply it to real single-wheel lift. Do not guess a height.

## Geometric diagnostic, not Climb definition

Current CPU M1 FK gives training root Z0.556439916m; straight-leg Z0.635958m.
Keeping four wheel anchors fixed, diagonal body shifts0.04/0.08m reduce the
strict FK-reachable height ceiling to0.626942605/0.614696171m. This explains why
blind height replacement breaks the old transfer, but is not the desired
vendor posture and was NOT deployed. No force/collision/physical claim.

## Fresh clearance verification

Existing new m1_crossing_clearance.py uses obstacle world top + wheel radius +
bottom gap. Default target4cm, allowed target3--5cm; wrapper strict threshold
defaults3cm. UNLOAD is not lift. Tilted-wheel envelope and actual obstacle top
still need independent physical verification.

From Go2Pvcnn:
`OMP_NUM_THREADS=1 /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q tests/test_m1_bottom_clearance.py tests/test_m1_cartesian_teacher_execution.py tests/test_m1_strict_crossing.py --tb=short`

Result47passed in52.84s: conversion/Cartesian execution/strict tracker only,
not physical crossing or vendor posture reproduction.

No M1 train/probe found; GPU7 placeholder1768831 unchanged. No posture runtime
edit, display change or training start. Next resolve Climb pose source, then
physical lift/roll/touchdown with bottom3--5cm above10cm obstacles. Existing
production support/WBC failures and policy-only/avoidance gates remain open.
