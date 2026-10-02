# M1 live source owner and raw body-pose capture — 2026-09-19

## Scope and current state

Parent: T306.6h.6a.1a.2c.1, live provider / conservative pose projection. This verification implements the live ownership and raw-pose half only. It does not project world/frame extents or authorize CLEAR, change the reference controller, or claim strict behavior/PPO/10000 completion.

Baseline isolated worktree `f3ae4a3b8efaab3161be32b39c793cea8d7acd7f`, branch `codex/m1-encounter-lifecycle`. Main source tree remains untouched. Root partition was already expanded by the administrator; fresh root944G/free495G and /data6.4T free. No partitioning, migration, or deletion was repeated.

## Implementation

- `collision_provider.py`: one explicitly owned source lease, complete synchronous query and cooked evidence, existing conservative local builder, 23-array guard, sticky invalidity, detached float32 poses plus source/step/episode identity, bounded retryable close.
- `collision_provider_live.py`: lazy installed-SDK binding; temporary no-physics callback; same-step/pre-reset 17-body pose snapshot; current stage, body names and articulation paths checked before and after the getter; exact physics tick increments; post-reset episode counters.
- `runtime.py` / `run.py`: default-off `--collision-live-provider`, limited 8×32 and exclusive old diagnostic flags; pose fields in existing NPZ chunks; close source/callback resources before environment destruction. Default controller and strict raw cooked probe stay unchanged.
- Persistent pending handles or unavailable cleanup diagnostics cause a nonzero terminal failure and explicit owner-chain quarantine; this adapter does not unload the environment/app or emit POST_CLEANUP in that state. This is not a promise about interpreter/OS final destruction order. Prior errors with confirmed-closed resources remain failures while allowing teardown.

## TDD and review evidence

Remote evidence prefix `/data/hexinkun-m1-acceptance-20260918/`:

- `live-provider-impl-red-20260919.log`, `red2`, `red3`: missing provider, report-publication source mutation, diagnostic failure during invalidation, each before its corresponding fix.
- `live-provider-impl-green-20260919.log`: final provider55 + existing geometry/lease/probe =454 passed39.91s. No full suite or GPU was delegated to implementer.
- `live-runtime-red-20260919.log`: initial targeted collection failed because the adapter import path was absent; not counted as a behavioral RED.
- `live-runtime-red2-20260919.log`: corrected collection,33 expected failures for missing live flag/adapter/wiring.
- `live-runtime-wiring-green-20260919.log`:11 passed.
- `live-default-regression-red-20260919.log`: isolated old test lacked adapter PYTHONPATH; not a behavioral result. `red2`: actual missing optional observer failure. `green`:73 existing tests passed6.86s with default path preserved.
- `live-runtime-green1-20260919.log`:33 passed30.00s; `green2`:36 passed34.54s including persistent publication failure/idempotent close.
- Independent SPEC found two P1 defects: post-getter binding drift and unsafe explicit unload after pending cleanup. `live-drift-red-20260919.log`:3 failed/1passed. `live-pending-red-20260919.log`:3 failed. Both fixed; `live-spec-fix-green-20260919.log`:42 passed36.52s. SPEC rereview independently ran10 passed7.64s and returned PASS.
- Main `live-provider-main-full-20260919.log`: **2026 passed226.43s/exit0/0skip**. Main `git diff --check` and `bash -n tools/m1_reference_validation/run.sh` pass.
- QUALITY PASS: independent97 new tests passed45.14s. No Critical/Important. Optional Minor: replace source-string sink-wiring assertions with a future CPU observer→actual sink→NPZ behavioral test; this package also requires independent real NPZ verification.
- Reviewed implementation and plan frozen as **47167e8c6a5664d8959d1f022f5231f7bae853b6**. No main source promotion, no SDK/reference changes.

## Actual runtime verification

Unique run `live-provider-20260919-1830`, native PID4142213, amp/GPU7,8×32. Console `live-provider-20260919-1830.console.log`; started18:30CST from frozen47167e8 with OMP/OpenBLAS1, existing /data TMPDIR, core dumps disabled. The verified original GPU7 reservation PID351307/15744MiB remains untouched. Results below were read only after the native wrapper exited; startup was not inferred from a running PID.

Actual outcome: full32 steps/8 environments,32 original prepare and32 original IK calls,128 physical sensor updates, no resets. Log order `M1_COLLISION_LIVE_CLOSED` → `M1_REFERENCE_ENV_CLOSED` → owner release → `M1_REFERENCE_APP_CLOSED` → `POST_CLEANUP` → native0 → wrapper0. Runtime startup_passed=true, strict passed=false as required for a32-step run. Native PID4142213 is gone; only original GPU7 reservation remains. No restart or reservation suspension occurred.

Main independent script `verify_live_provider_20260919.py` asserts actual raw files; JSON report `live-provider-independent-replay-20260919.json`, exit0:

- 23 raw before/after arrays byte-identical; every dtype/shape/SHA matches both metadata sets; initialization physics0/pump0 and temporary callback removed.
- 136 colliders and8 complete body inventories,32×8×17×7 raw float32 pose array, contiguous0..31, exact+4 physics/+1 environment tick, all episode IDs0, source hash/generation/stage bound on every frame. Pose quaternion norm² range0.999999650100963..1.0000003531076134, retained without normalization.
- Source lease remains COMPLETE through last/final source poll, then CLOSED/no pending subscriptions before environment close; cleanup errors empty.
- Original raw containment failure40 remains; new conservative geometry hash `aa88041dde277ad1ec78232b7033045ae4f43dd99d18224761bf0cf37978f517`. Old negative JSON SHA still `003aaae8f10a3f0500d1ba06bc7a64711f259b555e04c0200eb0f11a915d5597`.
- All28 common non-timing NPZ fields are bitwise identical to prior query-init startup `query-init-live-20260919-1618`, including actual/prepared/raw actions, IK, joint state, root/wheels, phase, scanner/contact and termination fields. Timing is explicitly excluded; new collision fields are independently validated rather than compared to missing old fields.
- Samples SHA `341652414ca4b2aee58f3636a066a3e4241da034d4956b8e9312167de1ad7b13`; initialization JSON `32430a06add2b74ba701f0e4140d65779940f5915c90ab0aeda9fdbc8aba0d3e`; cleanup JSON `62f215c059eeb94545df29f43e624efaccd7bfa3028ababd366b225f9335c2a5`; final report `59fa607f15bc3508cc882a711862cf7ecb70e7291793ef07b78696f04912e455`.

This closes only the online raw-capture startup gate. PPO updates=0; no world/frame extent/CLEAR or learned behavior claim.

Independent second artifact review PASS without using the main verifier: re-read all JSON/NPZ/console and reconstruct hashes and containment. Confirmed guard payload23018bytes, poses121856bytes,104Mesh/32Cylinder/104hulls/3664vertices, raw40 failures at3.725290298461914e-9..7.450580596923828e-9m. Stage9223001, physics indices6..130 by4, env counters[4,1]..[128,32], episode_length1..32, episode/generation0. Exactly one START/COMPLETE and no Traceback/restart. Console source-close480→env481→app484→POST_CLEANUP485→native486→COMPLETE487; POST_CLEANUP candidate SHA `5ce8b9d312c09ee722c9a3887e06105c49066a8f22c98e676db81dd1036ec612` matches. The reviewer was read-only and made no SDK/GPU calls.

Plan and exact CPU USD environment: [implementation plan](../../docs/superpowers/plans/2026-09-19-m1-live-provider.md).

## Native pose consumption boundary

Read-only audit: installed `omni.physics.tensors/omni/physics/tensors/impl/api.py:1185–1212` exposes `(count,max_links,7)` float32 raw link poses without Python normalization. Installed extension version is106.5.7. Getter documentation warns poses may be stale immediately after setting joints without updating articulation kinematics; this capture occurs only after the next completed physics step, not after manually setting joints.

Official fixed source commit `32ae713f6cb35f1df2544ffa499fc98a39639a62`:

- [PxQuat.rotate](https://github.com/NVIDIA-Omniverse/PhysX/blob/32ae713f6cb35f1df2544ffa499fc98a39639a62/physx/include/foundation/PxQuat.h#L286)
- [PxTransform.transform](https://github.com/NVIDIA-Omniverse/PhysX/blob/32ae713f6cb35f1df2544ffa499fc98a39639a62/physx/include/foundation/PxTransform.h#L128)
- [PxMat33 quaternion constructor](https://github.com/NVIDIA-Omniverse/PhysX/blob/32ae713f6cb35f1df2544ffa499fc98a39639a62/physx/include/foundation/PxMat33.h#L136)

For norm²=n and exact normalized rotation N, the raw real-polynomial maps differ: PxMat33 M=nN−(n−1)I, PxQuat.rotate C=nN+(n−1)I. Thus silently normalizing the recorded quaternion is not a proof of the native map. A subsequent versioned conservative public-pose envelope must cover the declared public maps and per-operation rounding. No installed-kernel internal equivalence is asserted and no further native-pointer audit is needed.

## Next gate

The live ownership/raw-pose package has passed quality/full CPU and unique actual amp/GPU7 8×32 with raw guard/hash/32×8×17 evidence and CLOSED-before-env/native exit0. Keep both old negative and new positive artifacts immutable. Next implement bounded outward public-pose projection with exact numerical tests and actual-pose replay, then registry/coordinator and independent replay; proceed to three new strict8×1600,1024×32/1600,G2 real re-encounter, AME/named actions/policy crossing+avoidance/single-process10000 actual updates. Do not repeat the old raw getter/probe investigation or pretend unprojected body poses prove departure. Full goal stays ACTIVE.
