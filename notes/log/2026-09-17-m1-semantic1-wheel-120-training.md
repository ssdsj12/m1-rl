# M1 semantic1 wheel-contact training A/B

## Purpose / Stage / Related Todo

Test whether removing the confirmed false geometry penalty lets M1 learn obstacle contact; M1 AME reward behavior, [T306.6c](../todo/T306-m1-ame-long-train-stability.md).

## Input / Procedure

Fresh single process in amp on physical GPU4,1024 env,120 updates,SAVE_INTERVAL20,seed42,init std0.2. No resume or automatic restart. Only behavioral code change from the prior low-noise120 pilot: semantic1 contact is tolerated for the four named M1 wheel collision shapes. Semantic2 wheel contact and all body/leg contacts remain penalized. tmux `m1ame_sem1wheel_1024x120`; [runtime log](../../run_logs/m1ame_sem1wheel_1024x120.log).

Preflight evidence: tensor RED/GREEN and relevant regression146 passed,1 skipped. [Physical8x300 contact probe](../../run_logs/m1_small_contact_probe.log) passed at1.2245m forward,0 resets/collisions, wheel center0.1461m. Airtime reward remained inactive.

## Current Result / Acceptance

COMPLETED in one process, PID3924332, amp Python, physical cuda:4. Exact iterations0..119, one completion marker and exit0;4915200 timesteps,926.97s. [Checkpoint](../../logs/rsl_rl/m1_cross_large_complex_ame/2026-09-17_21-26-16/4b5251f/model_119.pt) has iter119/next_iter120. All138 tensors in the entire checkpoint (39 model tensors) and all35 TensorBoard scalar tags are finite.

Final metrics: mean episode length980.02, bad_orientation0.001953, time_out0.9785, reward-44.9305, std0.342464, geometry reward-2.046533 and airtime-0.000361. Survival improved, but this does not establish obstacle behavior.

Sequential fixed-seed8env x500-step evaluations all completed with exit0: [flat](2026-09-17-m1-sem1wheel-flat120.md) safe success1.0,4.175751m; [small](2026-09-17-m1-sem1wheel-small120.md) crossing0,1.034230m; [large](2026-09-17-m1-sem1wheel-large120.md) avoidance0,0.507398m. Zero invalid-state and collision events in all three. Small approaches farther than the preceding1000-update policy but still stops; no behavior acceptance and no formal10000 launch.

An independent review found a separate success-after-fall evaluation loophole; [RED/GREEN fix](2026-09-17-m1-evaluation-terminal-failure.md) prevents future false-positive acceptance. These original evaluation files predate the new failure-termination metric. Follow-up is a matched0.10m controlled physical probe and wheel-appropriate reward design; the earlier0.05m contact probe did not prove all four wheels cleared the obstacle.

## Git Refs / Key Files

Baseline/Candidate Ref4b5251f plus uncommitted M1 work. Key files: [collision mask](../../Go2Pvcnn/extension/parallelism/collision.py), [M1 collision config](../../Go2Pvcnn/extension/parallelism/m1_kinematics.py), [regression](../../Go2Pvcnn/tests/tracking/test_policy_geometry_rewards.py).
