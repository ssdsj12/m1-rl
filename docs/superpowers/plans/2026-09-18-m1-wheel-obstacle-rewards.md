# M1 Wheel Obstacle Rewards Implementation Plan

> **For agentic workers:** Use test-driven development and subagent review. User approved the wheel-progress/lift design on2026-09-18; execute without asking again for this same scope.

**Goal:** Replace M1's inactive inherited obstacle airtime terms with actual semantic1-local directed movement and movement-coupled articulated wheel lift, while preserving safety penalties and single-process validation.

**Architecture:** New tensor-only `ame_baseline/m1_obstacle_rewards.py` computes two stateless terms from named link-origin states and the existing scanner terrain. M1 config alone replaces airtime/variance; Go2 valid-data behavior, policy1581/critic1584/action16, PPO/AMP and termination rules remain unchanged. Direct-upstream invalid scanner samples must remain invalid through conversion.

**Tech Stack:** Python3.10, PyTorch, existing ParallelismTerrain queries, IsaacLab45/IsaacSim4.5 in amp, pytest, physical GPU4.

## Frozen scope and formulas

- Body-frame command XY is rotated by root yaw into a world unit direction; requested speed must exceed0.1m/s. Require finite inputs and upright root (world-up cosine>0.5).
- Query15 samples per wheel: longitudinal offsets `[-envelope,0,envelope,envelope+0.15,envelope+0.30]` and lateral `[-envelope,0,envelope]`, oriented along the world command. An active wheel has a fully valid finite patch and at least one semantic1 sample. Any semantic2 sample in any wheel patch vetoes both new terms for that environment.
- Progress: actual root LINK-origin velocity projected onto world command, with0.02m/s deadzone, divided by requested speed and clamped[-1,1]; enable only near semantic1. It never consumes wheel angular speed.
- Articulated lift velocity: `v_rel = v_wheel - v_root - cross(omega_root, p_wheel-p_root)`. Use the positive minimum of world wheel-z speed and relative-z speed, capped at0.2m/s; a falling chassis or rigid-body pitch/heave must not create lift reward.
- Climb: lift speed/0.2 multiplied by positive `min(root_forward,wheel_forward)/requested_speed` capped1, gated below semantic1 top+wheel radius+0.02m, average across all four wheels. At rest/spin-only/stationary lift/rigid-body motion it is zero. This bounds bonus by real forward motion; it is not a proof against every multi-step reward exploit.
- Config: `feet_air_time=None`, `air_time_variance=None`, new `small_obstacle_progress` weight1.0 and `small_obstacle_climb` weight0.5. Existing geometry-10, semantic2 exclusion, undesired contacts, limits, posture, energy and rolling penalties remain intact. These are initial test weights, not proven optimal values.
- No planner reward or reset/terrain curriculum redesign. No checkpoint resume from old reward learning run. No auto-restart. No10000 launch until actual small/large behavior improves versus0 baselines.

## Tasks / ledger

- [x] Tensor RED: add `tests/test_m1_obstacle_rewards.py`; test progress forward/backward/lateral/zero, yaw covariance, stop/spin/lift gates, rigid-body heave/pitch cancellation, small/large/mixed semantics, invalid/NaN, boundary, height cap, four-wheel mean, named body reorder. Observed25 missing-module failures before implementation.
- [x] Tensor GREEN: implement `wheel_obstacle_reward_terms(command_xy_b, root_pos_w, root_quat_w, root_lin_vel_w, root_ang_vel_w, wheel_pos_w, wheel_lin_vel_w, terrain)` and environment wrappers `m1_small_obstacle_progress`/`m1_small_obstacle_climb` in the new module. Return one tensor per environment for each term; no persistent hidden state. Final26 tensor tests pass.
- [x] Upstream validity RED/GREEN (independent agent): explicit true mask must not admit NaN/Inf ray hits or elevation. Change only conversion validity conjunction and focused tests in `tracking/mdp/policy_geometry_rewards.py` and its test file. RED2 failures;GREEN full file10pass.
- [x] Config RED/GREEN: AST test proves both new bindings/weights and both airtime fields disabled, collision binding/weight and terminations unchanged. Add optional fixed forward command to diagnostic probe for signal calibration, without changing default probe trajectory. RED2fail thenGREEN.
- [x] Review and focused regression: independent spec and quality reviews PASS; final full M1/AME/collision union127passed1skipped. Py_compile and touched-file diff checks pass; unrelated existing CRLF changes preserved.
- [x] Real8env gates: one Isaac process at a time; physical0.05m probe8×600 completes+exit0,all-wheel8/8,0reset/geometry,progress/climb nonzero. Fresh8env×2 AME completes+exit0 and correct dimensions;all138ckpt tensors/35TB tags finite.
- [x] Fresh1024env×120 learning pilot: exact0..119,single start,complete+exit0,model119/next_iter120,138tensors/35scalar tags finite,savedbindingscorrect. Final fixed8×500flat/small/large allcomplete+exit0;flat8/8,small/large0/8 withzero collision/failure. This task is complete as an experiment; behavior gate isfailed,not fullM1goal completion.
- [x] Sync dashboard/T306/logs/human/AI and monitoring withactualoutcomes. NewT306.6g.1 isboundedgate/exposure diagnosis,notblindparametersearch. Formal10000 remainsunstarted andunverified.

## Commands

Tensor tests, from `Go2Pvcnn/`:

```bash
env -u PYTHONPATH /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q tests/test_m1_obstacle_rewards.py tests/test_m1_ame_config_static.py tests/tracking/test_policy_geometry_rewards.py
```

Physical probe (new unique log, repo root):

```bash
env NUM_ENVS=8 MAX_ITERATIONS=600 DEVICE=cuda:4 PROBE_SCENARIO=small_contact PROBE_COMMAND_X=0.5 TRAIN_ENTRYPOINT=Go2Pvcnn/scripts/probe_m1_rewards.py VALIDATION_LOG=run_logs/m1_wheel_reward_probe_8x600.log bash Go2Pvcnn/scripts/run_m1_validation.sh
```

Smoke/pilot use unique tmux session and log names; wrapper invokes exactly one Python training process, never a restart loop:

```bash
env -u CHECKPOINT NUM_ENVS=8 MAX_ITERATIONS=2 DEVICE=cuda:4 SAVE_INTERVAL=1 VALIDATION_LOG=run_logs/m1_wheel_reward_smoke_8x2.log bash Go2Pvcnn/scripts/run_m1_validation.sh
env -u CHECKPOINT NUM_ENVS=1024 MAX_ITERATIONS=120 DEVICE=cuda:4 SAVE_INTERVAL=20 VALIDATION_LOG=run_logs/m1_wheel_reward_1024x120.log bash Go2Pvcnn/scripts/run_m1_validation.sh
```

All runtime evidence belongs to T306.6g, a child of T306.6e behavior correction. Baseline4b5251f plus preserved dirty M1 work; work directly in the user-selected m1_rl checkout, not a separate divergent training source. No broad staging/commit of existing user edits.
