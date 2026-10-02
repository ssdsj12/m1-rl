# 2026-09-29 M1 10 cm crossing contract and Go2-to-M1 runtime audit

## Scope

- Keep the compatibility package namespace go2_pvcnn only where the IsaacLab
  base config is imported; the active AME scene, action order, kinematics,
  planner, rewards, and teacher are M1-specific.
- Use 10 cm M1 semantic-small obstacles, multiple separated placements, a
  protected center/reset region, and explicit geometry collision punishment.
- Ensure a corridor probe can trigger pre-lift without fabricating a wheel
  clearance or crossing success.

## Code changes

- ame_baseline/m1_obstacle_rewards.py
  - Forward corridor probes now report obstacle presence only.
  - Per-wheel lift/clearance/success stays local to each wheel patch.
  - Invalid/out-of-range wheel patches disable the reward path.
- ame_baseline/m1_mpc_teacher.py
  - Non-selected M1 legs are held at nominal action zero; measured drift no
    longer appears as four simultaneous swing commands.
- extension/batch_mpc_planner/planner.py
  - M1 crossing keeps a pre-lift phase and sequential single-leg swing.
  - The target wheel-bottom clearance margin is 6.5 cm over the observed top.
- extension/parallelism/collision.py
  - Unknown scanner cells are not collisions.
  - Ground/small support tolerance is limited to the lowest support sample;
    semantic-2 obstacle tops and side contacts remain collision events.
- extension/semantic_course.py
  - Generic callers retain the historical 0.16 m small-obstacle default.
  - M1 overrides remain (diameter,height)=(0.10,0.10).
  - Layout fallback now rechecks center safety and pairwise spacing instead of
    silently violating the 0.80 m spacing contract.
- ame_baseline/m1_ame_env_cfg.py
  - Effective M1 swing height is 0.30 m; collision reward weight is -18.
  - M1 terrain has 8--10 small obstacles per tile, 0--2 large obstacles,
    0.45 m center safety, 0.80 m clearance, and 0.50 m tile margin.

## Verification

Focused suite (AMP Python):

    64 passed, 1 skipped

Additional 10 cm planner reference test:

    1 passed

All modified Python files pass py_compile.

Short PhysX probes were run without starting training:

- M1 nominal 0.30 m, 100 steps: max_swing_legs=1,
  collision_steps=0, teacher_valid_steps=24; the deterministic probe
  did not consistently observe a wheel-bottom clearance >= 0.05 m because the
  generated obstacle/foot patch did not remain aligned in every episode.
- An exploratory 0.32 m arc exceeded the clearance target but reached about
  0.39 rad tilt, so it was rejected as unstable and is not in the config.

Therefore the code/test gate is green, but the physical 10 cm crossing gate is
not claimed complete and no long training was started. The next authorized
step is a deterministic fixed-obstacle PhysX alignment probe, then a short M1
teacher rollout; only after clearance, touchdown, collision-free passage, and
posture stability all pass should a checkpoint training run begin.
