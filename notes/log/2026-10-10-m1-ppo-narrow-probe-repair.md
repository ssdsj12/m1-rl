# T306/pure-ppo-learning/narrow-probe-repair

- Baseline Ref: bb57e7d with dense-forward2048 working diff.
- Candidate Ref: same worktree, reward longitudinal probe correction only.
- At iteration271, TensorBoard strict_obstacle_attempts5095, crossings0;
  last20 mean climb0.00011719, torque reward-1.18752, velocity reward0.84851.
  These aggregates do not by themselves prove torque suppresses lift; no weight
  changes were made from this correlation.
- Confirmed defect: wheel-local obstacle reward samples ahead at .15m increments,
  while authored obstacles are .05m wide. Synthetic measured single-wheel rise
  with real semantic-map obstacle at .18,.20,.34,.36,.48,.50,.64m yielded zero
  reward in7/7 tests. Forward presence alone cannot activate wheel-local reward.
- Correction: add .02m longitudinal samples within IDENTICAL old probe bounds,
  preserving original sample positions, lateral offsets, weights, stationary
  reward cap, physical-motion checks and strict crossing tracker.
- Key files: Go2Pvcnn/ame_baseline/m1_obstacle_rewards.py;
  Go2Pvcnn/tests/test_m1_obstacle_rewards.py.
- RED7failed; focused GREEN117passed in2.37s, including oldnegative cases.
- Deployment pending next model_300 save boundary. LivePID3886 still has old
  imported reward, despite new source on disk; no hot-reload claim.
- Next: validate checkpoint, stop only currentPID,2048two-update health check,
  then resume remaining iterations. Actual crossing improvement unverified.

## Deployment evidence

model_300.pt independently loaded with iter300,next_iter301 and all finite tensors.
OldPID3886 stopped; no other job touched. A transient SOCKS disconnect stopped the
first waiting shell, so process/checkpoint state was freshly checked before retry.
2048env final smokePID4761 exited, Training Complete,163840steps, iterations301/302,
64.98seconds total, last update15.27seconds, about15.5GiB GPU memory. No runtime/OOM failure.
Checkpoint: logs/rsl_rl/m1_cross_large_complex_ame/2026-10-10_13-08-19/bb57e7d/model_302.pt.
Long continuation uses9699iterations from next303 to total10002,2048envs,save100,
optimizer restored. New log /tmp/m1-pure-ppo-denseprobe-20261010.log.
Reward sourceSHA256 a0e5b3201e8225c054b9a46cd82c75f7b276e7a03e9f17b09e3192cc256eb7a6.
Still no claim of learned crossing; compare post-restart encounters/climb/strict
rates after episodes complete and actual video before accepting capability.
