# M1 probe neighbor-obstacle contamination: event trace and isolated A/B

## Purpose / Stage / Related Todo

Resolve72/4800 residual knee-proxy collision events from the0.05m full-traversal diagnostic. Verification-scene isolation, [T306.6f](../todo/T306-m1-ame-long-train-stability.md). No training reward, collider, material or contact threshold is changed.

## Diagnostic Contract / Tests

Add an opt-in `PROBE_EVENT_LIMIT` to the diagnostic script and a CPU-testable event helper. The helper reconstructs actual surface-point hits; shape-level leg bits are not sample indices. Terrain queries retain their environment batch. Robot and sensor body names resolve independently, avoiding the previously noted index-order ambiguity. Capture knee-local/world samples, source map heights/semantics, FK and actual link-origin poses, named raw force history, scene spacing/filtering and stage reporter attributes.

RED: helper import missing; GREEN:14 evaluation/reward/diagnostic tests. A subsequent spacing regression failed because the probe had no explicit isolated spacing override; GREEN after adding `cfg.scene.env_spacing=8.0` as in the evaluator. A four-case CPU LP check was also RED/GREEN: source-hull overlap, boundary, separation and rotated-frame invariance. Final relevant regression:97 passed,1 skipped (see runtime output from this verification pass); the skipped test requires a live Isaac app, which the physical probes exercised separately.

## Same-Config Event Replay

amp,GPU4,8env,600 steps,seed42,0.05m box,unchanged actions/rewards; `PROBE_EVENT_LIMIT=256`. [Runtime log](../../run_logs/m1_knee_event_probe.log) completes+exit0, reproduces all-wheel8/8,0 resets,72 events per FBL/FAR knee proxy, and captures all144 knee records.

- All events occur atsteps574..599, after passing the intended box.
- Hit-point x relative to its environment origin is3.396396..3.572808m; the intended box spans0.9..1.1m. With inherited2.5m env spacing, a neighbor's box spans3.4..3.6m.
- Hit sample indices17/20/23, semantic1, all map queries valid, terrain heights approximately0.05m. Map/sample overlap is19.89..25.66mm.
- Maximum named FK-vs-PhysX knee position difference0.212229mm; maximum rotation-matrix element difference0.000174969. No large frame/index mismatch explains the2.5m displacement.
- Named raw net-force history is0 for these records. Runtime stage confirms front-knee `physxContactReport:threshold=1.0`.

The scanner merges all configured obstacle meshes into one Warp mesh (`semantic_ray_caster.py`), but cloned environments use physical collision filtering (`InteractiveScene` env IDs; filter_collisions defaultTrue). The probe registered every env's ProbeObstacle, while retaining default2.5m spacing. It therefore scanned a neighbor's collision-filtered obstacle near the end of a600-step traversal. This is not evidence that the knees safely penetrate the intended box.

## Source-Hull Cross-Check

[CPU LP output](../../run_logs/m1_knee_event_source_hull_audit.json) uses captured actual knee poses and source-USD convex hulls. Against the intended box all144 records are separated. Against the neighbor's authored box107 source hulls overlap and37 are separated; maximum LP residual7.51e-10m. The common-plane slack is not Euclidean separation/PhysX penetration, and this check does not model cooked hulls/contact offsets. It supports the target-location mismatch; it does not justify disabling any knee penalty.

## Minimal Fix / Physical A/B

Only the probe's `env_spacing` changes to8m, matching the already-isolated evaluator. [Fixed probe](../../run_logs/m1_knee_isolated_probe.log): same8env x600 procedure,0.05m box,all-wheel crossing8/8,mean progress3.100000m,0 resets,0 geometry events,0 undesired-contact reward and0 airtime reward. Complete marker+exit0. The run reports env_spacing8.0 and filter_collisionsTrue. No automatic restart or concurrent Isaac job was used.

This closes the residual72-event diagnostic issue. The training policy's small0/large0 scores remain unchanged and the prior static proxy-volume conservatism remains a separate modeling limitation, not the proven cause of these events. The evaluator already used8m spacing; its results are not invalidated by this probe-only bug.

## Continuation Verification

On the user's subsequent continuation, SSH and the current files were rechecked in amp. Rerun from `Go2Pvcnn/` using amp Python, with PYTHONPATH unset:

```bash
python -m pytest -q tests/ame_baseline tests/test_actor_critic_ame.py tests/test_ame_observations.py tests/test_ame_vec_env_and_cfg.py tests/test_m1_ame_action_contract.py tests/test_m1_ame_config_static.py tests/test_m1_ame_terminations.py tests/test_m1_rl_reward_geometry.py tests/test_m1_parallelism_rl_adapter.py tests/tracking/test_policy_geometry_rewards.py tests/test_usd_mesh_triangulation.py tests/test_m1_evaluation_metrics.py tests/test_m1_exploration_cfg.py tests/test_m1_probe_diagnostics.py tests/test_m1_contact_overlap_audit.py
```

Result:97 passed,1 skipped in10.68s,exit0. Diagnostic scripts compile. An unrestricted `git diff --check` exposed extensive pre-existing CRLF/trailing-whitespace changes in unrelated files; those were not reformatted. Validation of the touched note files is checked separately. No train/probe/evaluate/supervisor process was present; GPU4 used5MiB with0% utilization. Existing tmux session names are not evidence of active training. Reward semantics remain unchanged.

## Follow-up / Git Refs

All bounded jobs have completed. No10000 training is running. Further progress/climb reward semantics still await the user's existing design-confirmation question; pause the heartbeat rather than run identical pilots or repeatedly ask. Resume after that decision.

Baseline/Candidate Ref4b5251f plus existing dirty M1 work. Key files: [probe](../../Go2Pvcnn/scripts/probe_m1_rewards.py), [event helper](../../Go2Pvcnn/scripts/m1_probe_diagnostics.py), [event tests](../../Go2Pvcnn/tests/test_m1_probe_diagnostics.py), [LP helper](../../Go2Pvcnn/scripts/audit_m1_contact_events.py), [LP tests](../../Go2Pvcnn/tests/test_m1_contact_overlap_audit.py).
