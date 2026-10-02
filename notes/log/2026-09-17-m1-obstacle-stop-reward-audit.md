# M1 obstacle-stop reward audit

## Purpose / Stage / Related Todo

Locate why both120 and1000-update policies pass flat but stop before fixed small/large obstacles; M1 AME reward semantics, [T306.6c](../todo/T306-m1-ame-long-train-stability.md).

## Evidence

The1000-update process and all three final evaluations completed cleanly with finite state. Small crossing and large avoidance remain0 at x0.7888m/x0.5429m while flat reaches3.9328m, so the obstacle response is reproducible and separate from simulator exit.

Training exposure exists in the active terrain: 5% of columns contain40 small obstacles,5% flat columns contain2 large obstacles, and the remaining non-plane columns contain5 small+2 large at rows0/1. The scene uses max initial terrain level1. Lack of any obstacle exposure is therefore not supported by the static configuration.

The M1 live geometry reward calls the official collision mask over16 M1 shapes. Wheel shapes previously tolerated only their lowest support band. A wheel contacting the vertical/front face of a small obstacle remained a collision bit at reward weight-10.0. The small-obstacle airtime reward weight is+0.1 with inherited threshold0.5s.

RED: a synthetic wheel with flat support plus one leading surface sample against semantic1/semantic2 failed because `ParallelismCfg` had no semantic support-contact contract. GREEN: add `contact_tolerant_support_semantic_ids`; M1 selects semantic1. The collision mask clears semantic1 hits only for named support wheels. Semantic2 wheel contact and all non-wheel geometry retain collision bits. Focused reward tests15 passed; collision/planner regression72 passed; combined M1/AME/collision regression146 passed,1 skipped.

[Physical probe](../../run_logs/m1_small_contact_probe.log): amp/GPU4,8 env x300 steps, fixed0.05m semantic1 box. Mean forward1.224506m, max wheel center z0.146050m,1182 env-steps with a small obstacle in the wheel envelope,0 resets,0 geometry-collision samples and0 undesired-contact samples; complete marker+exit0. This confirms real wheel/obstacle contact is no longer scored as body collision. The inherited airtime reward remained exactly zero during this successful low-obstacle traversal, confirming it does not currently provide the intended wheel-crossing signal.

## Next Verification

Run a fresh1024x120 training A/B with the semantic1 wheel-contact correction, then evaluate flat/small/large. If the fixed0.10m small evaluation remains0, replace or augment the inactive airtime term with a wheel-appropriate progress/climb signal under a new test rather than changing unrelated penalties.

## Git Refs / Key Files

Baseline/Candidate Ref4b5251f plus uncommitted M1 changes. Key files: [policy geometry reward](../../Go2Pvcnn/tracking/mdp/policy_geometry_rewards.py), [collision mask](../../Go2Pvcnn/extension/parallelism/collision.py), [M1 geometry config](../../Go2Pvcnn/extension/parallelism/m1_kinematics.py), [M1 rewards](../../Go2Pvcnn/ame_baseline/m1_ame_rewards.py).
