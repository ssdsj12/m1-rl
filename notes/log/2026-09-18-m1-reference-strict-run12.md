# M1 reference adapter promotion and first strict run

## Purpose / Stage / Todo

T306.6h.5c.3: promote the frozen normal-clone candidate and attempt the first of three strict 8x1600 gates. User reiterated the eventual single-process 10000-update and learned crossing/avoidance objective. This test is controller-oracle validation, not PPO or policy-only evaluation.

## Change and input conditions

The six frozen files from the [isolated normal-clone candidate](2026-09-18-m1-normal-clone-ab.md) were copied byte-for-byte into `tools/m1_reference_validation`: run.py, run.sh, runtime.py, clone_evidence.py and their two changed/new test files. Production adapter was clean against b60ca0f before promotion. No source reference, SDK, AME behavior, metrics, thresholds, assets or randomization changed.

Runtime amp Python3.10.21, physical GPU7; CUDA remap unset, fast_shutdown=False, path-stat cache disabled and checked, replicate_physics=False. Existing15GiB reservation PID2795762 stayed running because 8env fit. User subsequently explicitly authorized stopping only this reservation when needed and restoring it after GPU7 has no compute tasks; no permission to use GPU4 is inferred.

## CPU verification

Formal adapter: `bash -n run.sh` passed; all six SHA256 hashes match the frozen candidate. Full pytest command is in the [promotion plan](../../docs/superpowers/plans/2026-09-18-m1-normal-clone-promotion.md): **212 passed in27.02s**. No additional dependencies installed.

## Physical command and artifacts

```bash
cd /home/hexinkun/m1_rl
ulimit -c 0
bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 1600 \
  --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_12_normal_clone
```

stdout/stderr: same output prefix plus `.log`. PID3490004, run ID179fcc0a-bc38-4f7d-9946-7035706de260. No GDB, restart or signal. All1600 steps,1600prepare/IK calls and6400physical sensor updates were recorded. Each environment had1600first-episode samples, zero reset/termination/timeout, no nonfinite or measurement issue.

Final report: **completed=true, native_exit_code=0, wrapper_return_code=3, passed=false, passed_envs=4**. ENV_CLOSED, RUNTIME_REFS_RELEASED, APP_CLOSED and POST_CLEANUP all precede native exit. Wrapper3 is the strict behavior rejection, not an Isaac crash. The process disappeared naturally. Elapsed sampling91.8133s excludes full shutdown.

| Env | Root progress m | Wheel mean speed spread rad/s | Strict result |
| --- | ---: | ---: | --- |
| 0 | 2.98965 | .0960497 | reject wheel speed spread |
| 1 | 2.86635 | .0966572 | reject wheel speed spread |
| 2 | 2.93183 | .0785864 | pass |
| 3 | 3.11647 | .0505522 | pass |
| 4 | 2.90403 | .0962060 | reject wheel speed spread |
| 5 | 3.02855 | .0748856 | pass |
| 6 | 2.95519 | .0750631 | pass |
| 7 | 2.94426 | .0865233 | reject wheel speed spread |

All eight reached phase11, FAR/RAR prelift/overbar/passed/touchdown, zero measured bar forces, no reference collision, accepted tilt/height/action-continuity flags. This is the original narrow right-track bar (45mm exposed), not100mm full-width or large-obstacle success. All-strict8/8 gate is not met; repeats2/3 and1024 are not run.

Observed one GPU7 process-memory snapshot7074MiB, not a peak; SDK also created roughly384MiB contexts on other physical GPUs despite single selected simulation GPU. After exit GPU7 returned15754used/8328freeMiB and0%, original reservation alive. No foreign tasks changed.

## Offline first-failure diagnosis

The only failed flag is max-minus-min of the four signed1600-sample wheel mean speeds, frozen limit.08rad/s. It has no single first-failure step because it is an aggregate gate; first_failure_step=null does not make it pass.

Named order is FAR,FBL,RAR,RBL; signs all+1. Reference wrapper applies gain3 feedback toward the current slowest wheel, clips correction to±1, then adds rear feedforward.4rad/s. Individual tracking P/I are both0. Actual implicit wheel actuator damping30, stiffness0.

Offline replay uses the previous sample speed to reconstruct flat targets, with maximum errors below1.3e-7rad/s. Env0 steps1000..1011 show FAR target exactly0,1,0,1 repeatedly, with actual speed approximately.13,1.00 alternating. Tail800 FAR zero-target fraction is.5 for all eight environments. After-wave spread is worse than the full-run spread; wave ends around237..246. Phase11 is transient then resets internally to-1, not an environment reset, so phase==11 alone is not a valid tail window.

This proves saturated alternating control in the existing feedback chain, not yet the causal contribution of each gain/feedforward/plant term. A simple .4/(1+3)=.1 steady-state argument is insufficient because observed worst difference is commonly RAR-RBL, on the same axle. Proposed bounded A/B: isolated config with only equalize gain3→0, retaining low-level actuator velocity control, feedforward, controller, scene and all thresholds. User review pending; no sweep or threshold relaxation.

## Independent AME follow-up audit

10000 fresh runner count is correct: iterations0..9999 and final next_iter10000; resume+10000 means10000 additional updates. Formal AME still uses SDK default fast_shutdown and replicate_physics=True, and prints completion before cleanup. Reference promotion does not repair that separate entry. Future M1-only lifecycle integration needs its own owner/normal-exit and scene-capacity tests.

AME/reference action contracts differ: reference[12legs,4wheels] with scales.80/1; AME per-leg interleaved16 with scales.25/1/r. Transfer requires named physical targets, not direct action copying. Actor lacks wheel velocity/action history; reference oracle includes fixed obstacle x and zero leg residual. Current learned small/large success remains0/8. Source Go2 sideways XY planner is not an M1 differential-drive executor. These are subsequent bridge/avoidance work, not results of this test.

## Git / Conclusion / Follow-up

Baseline Ref:b60ca0f; repository HEAD before run4b735f8; promoted commit:a86cbf5; Candidate Ref:six hashes frozen in the linked A/B log. Independent integration spec then quality review passed: six files byte-equal, metrics/provenance untouched, bash syntax/diff check passed, key_physx hash unchanged. No full AME/SDK tree before/after audit is claimed. Strict physical behavior is only4/8, so no PhysicalVerifiedCommit for full strict success and no10000 claim.

New child T306.6h.6: wheel-feedback oscillation diagnosis, blocks strict repeat/1024 expansion. New sibling follow-ups T306.6i normal-close AME integration; T306.6j named physical target bridge and learned-policy contract; T306.6k M1 nonholonomic large avoidance. Keep original reference read-only and every prior artifact. Dashboard/branch/index updated.
