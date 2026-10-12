# M1 mirrored stance and collision reset implementation

Spec: ../specs/2026-10-12-m1-mirrored-stance-collision-reset-design.md
Execution: inline in the user-selected dedicated mirror, branch 10-12.
Base: 8a2b550. No unrelated watcher files or existing checkpoints are modified.

## Task 1: Tested runtime contract

Files: ame_baseline/m1_ame_contract.py, m1_ame_terminations.py,
m1_ame_env_cfg.py; tracking/mdp/policy_geometry_rewards.py; runner and evaluation
checkpoint validation; tests/test_m1_mirrored_collision_reset.py.

1. Add real FK/scanner tests for mirrored knees, ordinary ground, small wheel
   contact, high body obstacle, and clearance without contact; add contract
   validation tests. Run remote isolated CPU pytest. Expected: new tests FAIL.
2. Mirror front defaults, add strict zero-margin/no-support-exemption geometry
   query, wire non-timeout termination. Keep legacy query defaults unchanged.
3. Version stance/reset metadata and reject mismatches before loading state.
4. Run focused regressions plus new tests. Expected: PASS. Run independent
   source mesh FK. Expected: 585 mm, grounded meshes and no joint-limit breach.
5. Commit only selected implementation/tests/spec/plan.

Interfaces: named defaults feed action offsets, observations and recovery;
strict raw collision feeds termination before reward; metadata guards playback.

## Task 2: Native verification and fresh launch

Files: scripts/probe_m1_mirrored_collision_reset.py and deployment notes/README.

1. Check actual new host processes/GPU, stage candidate modules separately.
2. Native 4-env test: rolling nominal stance on ground; controlled obstacle
   intersection terminates affected row and carries failure reward, neighbours
   do not reset; clean elevated clearance does not terminate. Expected: PASS.
3. Final fresh-context code review and fix blocking findings with RED/GREEN.
4. Back up exact production files and deploy/hash verify. Launch exactly one
   fresh pure-PPO process: no CHECKPOINT, no resume, no optimizer load. Verify
   12 actions/.30/2048, stage0, fresh initialization and completed updates.
5. Point TensorBoard at new run without altering the user's tunnel. Update
   README, notes/T306/index/dashboard, automation and actual process/run record.

Interfaces: production imports must match tested candidate; fresh run must not
inherit previous stage1, optimizer or any old PT. Training must not overlap probe.

Review focus: stale reward buffers, semantic-ground false resets, small-wheel
support exemption, checkpoint compatibility, per-env reset and terminal reward.
