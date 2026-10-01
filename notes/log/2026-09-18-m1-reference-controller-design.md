# M1 reference controller investigation and stage-one design

## Purpose / Stage / Related Todo

Follow the user's supplied reference directory and approved direction: reproduce small crossing first, then adapt avoidance. Stage is source/entrypoint/asset investigation and specification only; related child [T306.6h](../todo/T306-m1-ame-long-train-stability.md). This is not another attempt at the stopped profiling mechanism.

## Procedure / Inputs

Read-only SSH source inspection and two independent audits of the reference M1 tree. Compared M1 task configuration, action wrapper, curriculum/evaluation helpers, semantic MPC and documented accepted reports with the current AME baseline. No Python/Isaac simulation, training, dependency installation or source mutation was performed. File existence checks do not establish USD dependency closure.

## Findings / Metrics

- Reference documentation records fixed60mm crossing three times with8/8, FAR/RAR clearance, no crossbar contact and height recovery. Accepted checkpoint/report directory is absent in the supplied copy; no new physical success is claimed.
- Current reference ContactFree uses sequential control/task-space IK, zero policy leg residual and a right-track-only fixed bar. PolicyPlay retains geometric fallback and does not give full leg control to the learned policy.
- Semantic MPC contains high/large obstacle side selection and path losses, but the M1 config sets planner_backend=none. MPC IK is still Go2-specific. No M1 large-obstacle successful rollout was found in the searched evidence.
- No-checkpoint m1_play bypasses the RSL wrapper. Its string env_cfg_entry_point handling also cannot be assumed correct. A separate explicit cfg+wrapper adapter is required for controller-only testing.
- Original floating USD and its physics sublayer refer to missing legacy machine paths. A candidate M1-only asset bundle exists inside the reference asset tree; its binary dependency closure and equivalence have not been verified. Do not substitute current AME/Panda composite assets silently.
- Play inherits startup mass/friction randomization. Fixed seed does not mean fixed physical parameters; record realized inputs.

## Result / Conclusion / Follow-up

Only the [detailed design](../../docs/superpowers/specs/2026-09-18-m1-reference-controller-validation-design.md) and investigation notes changed. The user approved the direction and subsequently required8env then1024env. The revised spec uses amp/GPU4, source/asset preflight, explicit controller/oracle ownership and CPU tests; no1-envsimulation. Run8×32 startup and three8×1600 strict evaluations; only all-pass permits1024×32 capacity then1024×1600 strict controller validation. No10000run, restart supervisor or monitor was launched.

## User Scale Amendment

The instruction “先8env后1024env” replaces the initial1→8 sequence, not the distinction between controller validation and policy learning. All1024envs remain in the strict success denominator; OOM/stall/early exit must fail visibly, without automatic restart, GPU substitution or reducing the requested scale. Source/asset preflight is unchanged. Updated spec/dashboard/branch/log index are synchronized; this amendment has no new runtime results.

Source/action/observation/reward contracts of production AME are unchanged; no human/AI stage contract update is required until an implementation is approved. There is no new runtime pass count. Next: user review, then detailed implementation plan and isolated execution setup. Missing asset equivalence remains a real preflight risk, not a resolved compatibility fix.

## Git Refs

Baseline Ref:740f07e plus preserved dirty M1 work. Candidate Ref:documentation-only commit for the design; implementation remains unchanged. Key production comparison files: [reward](../../Go2Pvcnn/ame_baseline/m1_obstacle_rewards.py), [current evaluator](../../Go2Pvcnn/scripts/evaluate_m1_ame.py). Reference source itself has no Git metadata and must be identified by file hashes when execution starts.
