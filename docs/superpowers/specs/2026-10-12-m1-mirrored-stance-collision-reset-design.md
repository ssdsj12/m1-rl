# M1 mirrored stance, obstacle termination and fresh training

User approved on 2026-10-12: use the reference image for the initial/recovery
stance, leave PPO free to move the legs, terminate the affected episode on
obstacle collision, and train a NEW model rather than continuing any checkpoint.

## Contract

- Front knees fold toward the rear; rear knees fold toward the front. Named
  HIP/KNEE defaults are mirrored, with wheels below the hip mounts. Keep the
  source-mesh total standing height at 585 mm; verify independent mesh FK.
- Default joint observation offsets, action offsets and recovery comparisons
  use the same reference. This is not a trajectory or an actuator override.
- Obstacle intersection terminates only the affected environment, is not a
  timeout, and keeps the failure penalty. Normal semantic-0 ground contact
  never triggers this term. Small-obstacle wheel support is NOT exempt.
- Use current live geometry, not previous reward buffers. Collision detection
  is a sampled geometry/semantic-scanner detector, not an exact contact-pair
  oracle. Native contact/reset cases must be checked before deployment.
- User amendment: no extra 3 cm top clearance. Measured nonpenetrating passage,
  no obstacle collision, three-wheel support and stable far-side landing remain.
  Both runtime trackers and perception proxy use zero EXTRA margin. Perception
  informs PPO; prediction alone never certifies passage. No fixed swing/fold
  trajectory: retracting or swinging a leg are both allowed. Reward high-water
  budget ends at the obstacle top, without rewarding repeated height cycles.
  Stage layouts and heights unchanged; standalone legacy APIs keep defaults.
- Fresh network, optimizer and curriculum; no resume, checkpoint or migrated
  model. Flat-first starts at stage 0. Four wheels stay at 0.30 m/s targets,
  PPO has 12 leg actions, 2048 environments, save100, 10000 iterations.
- Preserve all existing PT/logs. No teacher, IK, swing, MPC, WBC or manual std
  change. Record the new training contract in checkpoints and reject old
  stance/reset contracts on ordinary loading.

## Verification

CPU regression: named knee directions, wheel placement, ground/no-contact/
small-wheel/body collision distinctions, per-environment terminal mask,
configuration wiring and checkpoint mismatch rejection. Independent source
mesh height audit. Isolated 4-environment native stance and reset/reward tests;
then fresh 2048-environment launch with evidence of no checkpoint loading.
Training execution is not evidence of learned crossing.
