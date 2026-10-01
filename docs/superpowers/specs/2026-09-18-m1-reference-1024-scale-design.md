# M1 reference-controller 1024 scale adaptation

Date:2026-09-18. Parent:T306.6h.6a.1. Execution authorization: user requests continuous work until acceptance; this is the previously approved reference design's8→1024 stage, with explicit layout changes allowed. It does not authorize SDK/driver changes, other jobs, relaxed gates or a teacher-as-policy claim.

## Entry evidence and scope

Runs14/15/16 are independent processes, each exact8×1600,6400substeps,strict8/8,zeroreset,native/wrapper/verifier0. All2700non-timing recorded arrays in each repeat are bitwise identical to run14. The candidate is being promoted byte-for-byte before scale work. Preserve the immutable diagnostic candidate and all old run artifacts so old8-env verification remains reproducible with its original SHA256-bound verifier.

Only adapt layout, explicit baseline selection and CPU evidence-budget handling. Preserve reference source/assets, floating robot, seed20260711 and real randomization, zero policy residuals, original prepare/IK calls, controller parameters, sync equations, action units, contact diagnostics, scalar gates and normal native shutdown. No reward/AME/student/planner changes in this stage.

## Alternatives and selection

1. **Compact deterministic32×32 terrain plus explicit budget-aware verifier (selected).** All1024 origins remain unique and spaced8m. Generalize the existing independent NumPy verifier with explicit immutable budget arguments, keeping8×1600 defaults and tests. Archive old verifier/source unchanged for old hash-bound runs.
2. Keep1×1024 terrain and relax geometric tolerance: rejected. Deterministic world float32 quantization causes768/1024 local-center errors beyond2e-5m; changing tolerance would hide an avoidable measurement/physics issue.
3. Copy the entire old verifier into a second independently maintained500-line implementation: rejected for drift risk. A new layout helper is warranted; duplicated equations are not. The updated verifier must still import no controller,torch or simulator, and no mutable module-global budget patching is allowed.

## Layout contract

Create `scale_layout.py`, importing no Isaac/torch until its runtime factory is called after AppLauncher. Eight environments retain exactly1×8 layout and original importer. For1024 use32×32 tiles of8×8m, `row=env_id%32`, `col=env_id//32`, unique full-grid coverage. Expected terrain origins lie at±124m in each planar axis. Keep max_init level0, but install an adapter-owned subclass of the original `SemanticCourseTerrainImporter` via cfg.class_type. Override origin calculation at terrain construction, not robot state after reset. The factory may call the parent origin method first to preserve its random draw/API setup, then explicitly assign levels/types/max level and returned origins to the bijection. No global monkey patch and no modification of reference or SDK files.

Original terrain curriculum updates are disabled by the reference play configuration. Verify this before running and reject any origin-map change during samples; a reset must never silently migrate an environment to another tile. Preserve original startup mass/friction randomization and record actual1024 values, without assuming the first8 equal small-run randomization.

Use one pure mapping function for importer levels/types and own-bar path ownership. Parse actual numeric row/col/slot0 names, never lexical path order; reject missing, duplicate, extra or malformed tiles. All1024 bars retain local(.85,-.20),dimensions(.06,.16,.06),same grounding. Existing2e-5m geometry threshold remains. Verify actual terrain levels/types/env_origins,scene.env_origins,robot paths and observed roots against the map. Record mapping, class identity, source hashes, origins and32×32 layout in `scale_layout.json` and scene manifest. Existing actual sensor/filter path checks and scanner own-bbox checks remain.

Normal cloning and the declared collision graph stay unchanged. Explicitly retain the existing limitation: group-graph evidence plus zero foreign forces does not prove dynamic per-bar filtering in the absence of contact opportunities. Do not change collision groups or substitute inferred contact evidence.

## Runtime modes and provenance

Extend the existing adapter only in an isolated scale candidate directory. The default mode remains `post-cross-sync`. A clearly named `--controller-mode reference` is permitted only for1024×1600 baseline collection; it invokes the same original instrumented wrapper but skips the sync wrapper. It never reports synchronization acceptance or policy-only success. No other control mode or free parameter tuning is exposed.

Both1024 modes share the same entry/runtime/layout/verifier files and metadata hashes. Persist a scale-validation identity in configuration/provenance for run.py,runtime.py,scale_layout.py,sync_verdict.py plus the frozen core/bridge hashes. Distinguish baseline/candidate control modes explicitly; their only permitted metadata differences are that mode label and the candidate's existing diagnostic_candidate section. The same scene/physics configuration, bindings and actual initial randomization must match exactly. Configuration class_type is the only new layout-related allowlisted setting;8-env default configuration otherwise remains unchanged. Record the actual adapted importer code identity, not a fabricated reference module name.

Verify metadata mode values and configuration/provenance internal consistency before removing only the named top-level mode field and fully validated candidate diagnostic_candidate. Baseline must not carry diagnostic_candidate; never recursively ignore arbitrary same-named keys. Reference mode must explicitly call frozen `validate_live_contract()` and record its evidence despite skippingSyncBridge. Both live contracts must match. Per-sample origin guards must read current terrain_levels,terrain_types,terrain.env_origins and scene.env_origins, not merely compare a previously frozen sink copy.

Keep post_cross_sync.py and sync_bridge.py byte-identical to accepted runs. They already support arbitraryN. Adding a verifier version or runtime scale identity must not mutate their formulas, gate parameters or telemetry.

## Independent verification

Generalize helpers with an explicit immutable budget, validated against allowed(8,1600),(1024,32),(1024,1600). Preserve existing evaluate(output,baseline) behavior/default8×1600. Use explicit CLI arguments for scale; never infer a smaller N from incomplete samples. Crosscheck requested budget against all run/config/scene/randomization/chunk/report evidence. Keep ZIP256MiB per-chunk bound and finite numeric checks, exact step ordering, all required fields, env identities and complete denominator.

###1024×32 capacity/startup

No baseline is required because this is not a physical-prefix or crossing claim. Require native0/wrapper0,complete cleanup/exact0..31,all1024 first episodes withoutreset/termination/timeout,32prepare/IK,128physical sensorupdates,valid scene/source/actual action units,finite exact-shape samples. Independently replay event/gate/state; require no activation and full16-column original/final/actual/processed action parity. Reject mixed budget,short lastenv,forgedsidecar or missing artifacts. Report `validation_kind=startup`, startup accepted separately, and behavior/strict=false. Never demand phase11/activation/tail800 at32steps.

###1024×1600 strict

Require same-scale baseline, same scene/seed/all actual randomization and source identities, normal native completion for both runs, and candidate originalstrict1024/1024,zeroreset/ended episodes,exact1600/6400/50chunks. Independent NumPy event+state replay, bitwise actual actions, all existing output bounds/half-endpoint-ULP slew/hold/gates and per-env tail800 with799differences remain unchanged.

For each env compare every non-timing physical/action sample strictly before its first candidate activation, bitwise including dtype. Baseline must have continuous samples and no reset/ended episode in this required prefix. An end/reset strictly after this prefix does not retroactively invalidate an earlier comparison; preserve and disclose all baseline negative results. Baseline itself must still reach its full requested1600 in one process with normalnative0 and complete evidence. Its behavior/wrapper3 may be negative; that is not silently rewritten to0. Candidate activation must be valid and candidate must remain complete/strict for all1024; no failure filtering, smaller denominator, substituted8-env data or acceptance based solely on original/final action parity.

Baseline wrapper3 is acceptable only for behavior failure, never measurement/source/scanner/cleanup errors. Preserve those common guards for both runs. Ending at the final required prefix sample (`activation_step-1`) fails. Scale chunks must be exactly50×32 for1600 or1×32 forstartup; recorded full_jacobian_shape must be[1024,17,6,22] throughout.

Old8×1600 default retains the original stricter full-baseline-first-episode condition for compatibility. Historical runs are reverified with the immutable old candidate. New8envsynthetic regressions test algorithm compatibility of the budget refactor, not falsely rewrite historical source hashes.

## Tests, reviews and physical order

1. Formal promotion must pass373CPUtests and independent spec then quality review before scale work begins.
2. TDD layout tests: all1024 unique tiles, numerical float32 local centers within unchanged2e-5, mapping permutations and col/row lexical traps, reject missing/duplicate/invalid paths; fake parent factory verifies construction-time assignment and original call; live evidence mismatches rejected. Eight default behavior unchanged. Do not mock away the pure arithmetic or actual SDK method semantics.
3. TDD verifier/mode tests: preserve all old tests; explicit1024 shape/budget/lastenv detection,32startup distinct fromstrict, exact full denominator, native/cleanup/metadata/sourcehash failures, baseline prefix and after-prefix end cases, NumPy replay with1024 state, original/default mode wiring. At least one full1024×1600 synthetic artifact fixture/replay on the server, not only8-env shapes, with measured test resources. No mandatory huge repeated fixture per mutation; focused pure tests may use bounded arrays.
4. Spec and quality review of the isolated scale diff. Freeze hashes. Recheck disk>=12GiB free and sufficient RAM; preserve evidence/core dumps disabled. Reserve expected3.47GiB uncompressed arrays plus metadata/logs/temporary verifier memory. No cleanup of user files.
5. Before physical run, identify GPU7 UUID and all its PIDs. User already permits stopping own verified15GiB sleep.py reservation if needed; proactively free it for1024 to avoid a knowingly constrained capacity test, without touching other processes. Capture script/cwd/interpreter/environment/command needed to restore it. Restore reservation only when no taskcompute job remains; never run it alongside a task that needs its memory.
6. One candidate1024×32 capacity run. Capture externaldevice/process memory peaks,step progress,sensor/NPZtime,CPU/RAM/disk andnativeexit. A stalled/OOM/failed run stops escalation; retain artifacts and diagnose, no automaticretry/downscale/switchGPU.
7. Ifstartup passes, one originalcontroller1024×1600 baseline, then one sync candidate1024×1600, same frozen scale code/assets/layout. Native/budget/source/scene failure inbaseline stops candidate launch; baselinebehaviorfailure is preserved and may still permit prefixcomparison. Candidate failures stop promotion and report first violating stage for every failedenv.
8. Only after1024/1024strict and independentverdict pass consider scale promotion. Update dashboard,T306,logindex and individual evidence logs. This still does not complete learnedcrossing,largeavoidance,AME lifecycle/action bridge or10000updates; those remain separate subsequent designs under the continuous goal.

## Self-review

No controller/gate/physics changes, no reset laundering, no global budget mutation, no claim that startup is behavior success. Old runs stay reproducible through frozen source. Layout bijection occurs before initial reset and is audited at runtime. Baseline negative later behavior remains disclosed. GPU reservation authority is explicit and restricted. This document refines the already authorized scale/layout stage rather than asking the user to repeatedly approve ordinary execution.

Independent design review PASS: actual SDK/reference construction chain, class_type wiring, plane terrain and disabled terrain curriculum checked on4090; scanner512 limit is batching, not discarded environments. Reviewer cautions on exact metadata exclusions, baseline live units, live origin guards, wrapper3 and full1024 Jacobian/chunks are incorporated above. Capacity remains unmeasured.
