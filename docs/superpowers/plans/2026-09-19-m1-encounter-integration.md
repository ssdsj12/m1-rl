# M1 encounter registry, lifecycle and action handoff implementation plan

> **For agentic workers:** Use subagent-driven-development, TDD and independent SPEC then QUALITY checks. The approved design is unchanged; no new user decision is needed for these components. Keep all full-goal gates active.

**Goal:** Prevent same-encounter phase reentry without permanently excluding an obstacle, and implement identity-bound completion/departure/reapproach and pre-prepare ownership handoff.

**Architecture:** Pure static own-object registry associates raw semantic hits unambiguously; lifecycle core consumes ordered physical samples and fixed frame evidence. A versioned vendor snapshot introduces only an instance hook before the reference phase helper. Existing sync receives explicit row-level release/begin notifications, keeping original PI/EMA parameters and first encounter behavior. Raw samples and immutable descriptors are retained separately for independent replay.

**Tech Stack:** amp Python, NumPy/Torch CPU tests; existing full live geometry/pose provider; isolated worktree /data/hexinkun-m1-acceptance-20260918/encounter-worktree HEAD8e60686.

## Task A — static registry and complete semantic association

New `tools/m1_reference_validation/encounter_registry.py`, `tests/test_encounter_registry.py`.

- [x] RED dynamic callable test for `ObstacleRegistry(num_envs, records, geometry_generation, source_sha256)`.
- [x] Records are detached JSON dictionaries: env_id, obstacle_id absolute prim path, semantic_class1/2, bounds_world ordered finite(2,3), frames list of EncounterFrame dictionaries. Frame id/path/gen agree, unique directions and own paths, eachenv has declared records. Static axis-aligned bounds only in this package; unsupported moving source is rejected by existing live lease, never tracked heuristically.
- [x] `manifest()` returns detached JSON with records/generation/source SHA and content registry_sha256. `associate(env_id, semantic, world_hits)` requires one real semantic array(R,) and worldhit array(R,3); all classified1/2 rays inspected, original ray indices retained. Use union of actual bbox and f32-quantized bbox plus existing2e-5 scanner boundary only; not a physical clearance. Each hit must match exactly one same-class own object. Return explicit associated/unknown/foreign/ambiguous/invalid evidence and per-ray indices; never merge objects or rank array order. Non-obstacle legitimate misses may containinf; positive classified hits must befinite. No success claim from class alone.
- [x] Boundaries, two objects continuously visible, duplicates/overlap/unknown/foreign/nonfinite, partialenv, detached inputs/hash, emptyclassifiedhits tests. Run pure amp CPU tests with new /data temp/log; no SDK/GPU.

Task A code `394ea67`: independent SPEC then QUALITY PASS; 121 focused tests. Added conservative finite-hit-cloud AABB prefilter after measured 1024-row Python-loop cost (12.5 seconds); all-owner/class exhaustive semantics unchanged, CPU diagnostic now 0.36 seconds. Not a live 1024 gate.

## Task B — lifecycle and boundary credentials

New `encounter_coordinator.py`, `tests/test_encounter_coordinator.py`.

- [x] RED tests for immutable per-row keys(env,episode,obstacle,seq,generation), AVAILABLE/CROSSING/DEPARTING/CLEAR, sticky failurehistory and strict prepare/observe step order.
- [x] Completion requires currentencounter ordered prelift→overbar→passed→touchdown for requiredwheels, recoveryphase10complete/phase11, no invalid/terminal/contactfail. It must latch before waiting for5syncsamples. No elapsed-time or scanloss unlock.
- [x] Departure uses wholebody low(s)>half_length+.005; newapproach requires prior wholebody max(s)<-half_length-.005, continuousrawroot s increase, headingdot>0, same uniquelyassociated ownobject, frontwheelwindow[-.45,-h-.0959], requiredwheel corridor. Closest eligiblefrontsurface chosen; tieswithin1e-12/multiplevalidfaces/unknownhits ambiguous. Newobject requires its own front evidence and old recovery/CLEAR, not globalrawgate disappearance.
- [ ] `prepare` records descriptor and row-boundary before new legs can occur; only old_phase<0 gate affected. First bootstrap preserves original uniquegate and helper window. Newencounter invalidates only row caches/ready/events, not episode/globalstep/history; sample(t) retains its olddescriptor.
- [ ] Validate duplicate/skippedsteps/generationdrift, noreset/teleport synthetic replacement, incompletefirstcrossing rejection, newencounter after4/5/active ready, rotated/rawcoordinate consistency, resets and allenv independence.

Task B CPU lifecycle core `d27e26c` has 63 focused tests and independent SPEC then QUALITY PASS; main latest production full suite 2317 passed, final focused union184 passed. The last two items remain open for reference/sync integration: no row cache or PostCrossSync state is changed by the pure coordinator. Synthetic traces prove algorithm behavior only. Legitimate CLEAR→new encounter may occur while the old reference phase remains 11; Task C must initialize that selected row to phase -1 before the helper. Requiring a prior raw-gate false interval would violate the continuously visible next-obstacle requirement.

## Task C — source-bound instance hook, sync release and recording

New isolated vendor wrapper snapshot and `encounter_bridge.py`; minimal edits run/runtime/provenance gates; extend PostCrossSync without changing default behavior.

- [ ] RED disabled snapshot/reference parity and singleprepare/singleIK; use actual referenceCPU fixtures. Exact upstreamSHA guard; manifest records vendorSHA and explicitdiff, never claims vendorisoriginal.
- [ ] Hook after phase buffers initialized and before common_kwargs: only previousphase<0 gets rawgate&allowed. Ongoing0..10 unchanged. Enabledmode explicitly supports verified sequential right-track path, rejects unvalidated axle/othermodes.
- [ ] Newencounter recaptures nominal wheel/body height per row before helper-1→0; first-everNone capture staysoriginal; clear enabled integral/wave/smooth/clearance caches perrow, keep topologicalIDs and unrelatedrows.
- [ ] Explicit sync release/begin credentials validate step/key/reason/geometry; clearactive/ready/events/EMA/integral/hold/activation oldpacketeligibility, preserveepisode/step/episode_length continuity and history. Freshwave alone never authorizes release.
- [ ] Compact lossless selectedsemantic ray identities/points and descriptors plus projectedgeometry and boundary/action sidecars allow independent NumPy replay; don't trust runtimecompleted flags. Preserve old collector/negativeevidence and thresholds.

## Task D — gated physical evidence

- [ ] Full regression, bashsyntax, independentSPEC/QUALITY. Freeze candidate before actual GPU work.
- [ ] First8×32 startup underamp/GPU7 withoutrestart; then samecandidate three8×1600 strictG1 with original first-completion-prefix parity and fullencounterreplay. Onlyafterthose1024×32capacity and1024×1600fullbehavior. Do not drop failingfirstcrossingenvironments.
- [ ] G2 real route/return andmultiobjectscene parameters remain a subsequent declaredaction/scenepackage; never labelG1 as G2/policy. AME/namedactions/policycross+avoid/singleprocess10000 remainfullgoal.
- [ ] Eachmeaningfulresult updatespertestlog, dashboard,T306,index; preserveoriginaltree/SDK/oldruns andGPU7reservationunlessauthorizedverifiedpauseisneeded.
