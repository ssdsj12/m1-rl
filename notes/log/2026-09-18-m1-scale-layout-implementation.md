# M1 reference 1024 compact layout — Task 1 implementation

Date: 2026-09-18. Parent: T306.6h.6a.1. Scope: delegated Task 1 only, using the approved `m1-reference-1024-scale-design` contract and explicit TDD authorization. No commit, deployment to formal adapter, GPU workload, dependency installation, controller/verifier change, or signals to existing user processes. The unchanged CPU regression suite includes its own disposable fatal-signal subprocess tests.

## Boundaries and preflight

- Local scale candidate: `C:/Users/xk/Documents/project/m1_reference_validation_stage/scale1024/adapter`.
- Remote scale candidate: `/home/hexinkun/m1_debug_tools/scale1024_20260918/adapter`, host `4090`.
- Frozen candidate: `/home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter`; local equivalent is `m1_reference_validation_stage/post_cross_sync/adapter`.
- Formal adapter: `/home/hexinkun/m1_rl/tools/m1_reference_validation`, promoted at `646f486`; repository HEAD subsequently includes design/plan `5553e84`.

Before edits, all 16 files in local scale, local frozen, remote scale and formal matched byte-for-byte/SHA256. `git diff --exit-code 646f486 -- tools/m1_reference_validation` and remote scale-versus-formal recursive diff were empty. Read-only SDK/reference checks confirmed `SemanticCourseTerrainImporter.__init__` calls SDK initialization before spawning bars; SDK initialization invokes `configure_env_origins` and the overridden `_compute_env_origins_curriculum` before this spawn. The source flat generator contains only `MeshPlaneTerrainCfg(proportion=1.0)`; inherited play configuration disables both terrain and linear-velocity curricula.

## Implemented contract

`scale_layout.py` imports NumPy and standard-library modules only. Its positive-integer `tile_indices` returns int64 `(rows, cols)`, using `env_id % 32` and `env_id // 32` for 1024 and the legacy `1 x N` mapping otherwise. The runtime factory accepts only the actual loaded reference parent identity, then imports Torch and creates an adapter-owned subclass. The override validates 1024 and `32 x 32 x 3`, calls its original parent exactly once to preserve RNG/API setup, assigns long levels/types and max level 32, and returns the explicit gather before static-course spawning or initial reset.

`adapt_cfg` installs that subclass only at 1024, retains max initial level 0, and uses `32 x 32` tiles of `8 x 8 m`. It rejects unknown importer identity, non-generator/non-flat terrain, modified plane function/proportion, missing curriculum state or enabled terrain/linear-velocity curriculum. `scene.terrain.class_type` is the only added allowlist entry. Eight-environment configuration continues through its original importer and layout.

`own_bar_indices` uses the same numeric mapping, supports shuffled paths and legacy column 100, and rejects missing, duplicate, extra, out-of-range row/column, nonzero slot, negative or suffixed paths. A strict `\Z` ending also rejects a trailing newline.

`layout_evidence` snapshots the actual levels/types, full terrain-origin grid, terrain environment origins and scene origins. It requires the complete deterministic map, exact 8 m flat grid extending to ±124 m, correct expected gathers, ordered named robot paths, actual subclass and original-parent identities, and records both source hashes. It separately checks and records actual `terrain.cfg.num_envs`, `scene.num_envs` and `scene.cfg.num_envs` as 1024. The pre-construction config dump remains untouched: its terrain count may still be 1 until InteractiveScene configures the importer.

At 1024, `validate_scene` writes `scale_layout.json` and embeds the same evidence in `scene_manifest.json`; `run.py` also attaches it to runtime metadata. `RuntimeSink` freezes a fresh validated layout snapshot during construction and rereads all live fields at every sample, validating the expected gather and exact initial-evidence equality before measurements. An error follows the existing cleanup path. Eight-environment samples add no terrain/scene ownership access. Existing bounding-box, position, schema, contact and scanner thresholds are unchanged. Existing declared collision-group evidence and its inability to prove dynamic per-bar filtering without contact opportunities are unchanged.

## Actual TDD and regression results

All test commands ran from the remote scale adapter directory under the supplied amp CPU environment. No old test file was edited.

1. New tests deployed before any implementation: **41 failed, 9 passed in 1.91 s**, exit 1. Failures included missing `scale_layout.py`, old row-0-only ownership, old `1 x 1024` config, absent configuration guards and missing metadata wiring.
2. Minimal implementation: **50 passed in 1.92 s**, exit 0.
3. Additional actual-runtime-count requirements: **4 failed, 52 passed in 3.88 s**, exit 1, due to absent count metadata and failure to reject mismatched actual counts. Added the checks after observing RED.
4. First full suite: **4 failed, 425 passed in 80.23 s**. Four unchanged fatal-diagnostic regressions import `runtime.py` directly from a temporary working directory, so a new top-level sibling import failed. Moved the layout imports into the functions that need them; no diagnostic implementation or old tests changed.
5. Full suite after lazy-import correction: **429 passed in 76.21 s**, exit 0; `bash -n run.sh` also exit 0.
6. Final path-boundary regression: **1 failed, 56 deselected in 0.17 s**, exit 1. Python regex `$` accepted a final newline. Changed only the own-bar end anchor to `\Z` after this RED.
7. Final full suite: **430 passed in 76.73 s**, exit 0. This is all 373 unchanged legacy tests plus 57 new scale tests. `bash -n run.sh` produced no output and exited 0 in the same successful command.

Test coverage includes the 0/31/32/1023 boundaries and all 1024 unique tiles; all compact float32 local centers within unchanged 2e-5 m and a long-strip negative control with exactly 768 failures; numeric path permutations/malformed paths; real Torch CPU parent draw/RNG state and assignment before fake parent's spawn; 8-versus-1024 config; source identity; every live origin/mapping field drift; duplicate origins; actual counts; initial sink snapshot versus later samples; no added 8-env scene access; and a real in-memory USD scene with 1024 bars verifying JSON/manifest output and rejection of a 0.001 m displaced bar using the original geometry threshold. The construction fake mirrors the observed SDK parent method semantics; pure layout/float32 arithmetic and Torch RNG are real. The USD integration test isolates unrelated graph/ground measurements, which remain covered by unchanged legacy tests.

Exact command used for full regression:

```bash
cd /home/hexinkun/m1_debug_tools/scale1024_20260918/adapter
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 \
LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin \
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short -p no:cacheprovider tests && bash -n run.sh
```

## Change scope and hashes

Local/remote candidate SHA256 agrees for all four changed/new files:

| File | SHA256 |
| --- | --- |
| `scale_layout.py` | `11cea40eea64d9182e5ae5d23e249018d3246486bbd438077512d4317f4b8633` |
| `runtime.py` | `408ec9884c831b0e5a1ac7a2ee404a22f41371f6134563535223d1e91c065f8e` |
| `run.py` | `4427611013f1e7ecf73c7124e8c9da503d84fafed2cffe5b688646f1257ab02a` |
| `tests/test_scale_layout.py` | `0019b44c26c638f89f2f8e2a824cf4af0597861f91931da49f3d8cd4c7f2818b` |

Directory diff is exactly these four files: 530 insertions and 8 deletions. Existing-file changes are only `runtime.py` and `run.py`; `scale_layout.py` and `tests/test_scale_layout.py` are new. AST comparison of existing runtime functions/classes shows changes only in `adapt_cfg`, `own_bar_indices`, `validate_scene` and `RuntimeSink`; `layout_evidence` is new. `cleanup_run`, `finalize`, PhysX contact code and all other existing runtime nodes are identical. All other 14 original adapter files, including core, bridge, verifier, shell and old tests, remain byte-identical to the frozen source.

Formal `git diff 646f486 -- tools/m1_reference_validation` remains empty, and formal versus frozen candidate recursive diff remains empty. `git -c core.autocrlf=false diff --no-index --check` reports no whitespace diagnostics (its exit 1 denotes the directory differences). SDK and reference were read only. Implementer did not edit root notes. Main independently reran focused57tests: **57passed in4.06s,exit0**, and recheckedall4hashes above. IndependentSPEC/quality review is in progress. NoGPUcapacity/1024behavioralclaim; explicitmode/budget/verifier belong to later tasks.

## SPEC P1 review finding and corrective TDD

The first independent SPEC review **failed with P1**, despite the historical 430-test GREEN recorded above. `adapt_cfg` compared `plane.function` with `MeshPlaneTerrainCfg.function`. Actual SDK `@configclass` converts inherited fields to dataclass `default_factory` fields, and Python removes the class attribute. The valid instance has `function`, but `MeshPlaneTerrainCfg.function` raises `AttributeError`. The original `NS`/`staticmethod` test substitute masked this API behavior. The earlier 430-pass result and initial hashes are retained as historical evidence; they did not establish this SDK compatibility.

Verified the actual SDK source read-only: `utils/configclass.py` `_process_mutable_types`, `terrains/sub_terrain_cfg.py` and `terrains/trimesh/mesh_terrains_cfg.py`. Replaced the old plane substitute with a CPU test loader executing the original SDK `configclass` decorator implementation and original AST declarations of `FlatPatchSamplingCfg`, `SubTerrainBaseCfg`, `MeshPlaneTerrainCfg`, and `flat_terrain`. Only the unused relative dictionary-helper import is removed to avoid importing runtime dependencies; decorator/dataclass behavior and configuration declarations execute unchanged. Test configuration serialization reads the actual dataclass instance fields directly. The terrain generation function is not called, and no simulator or GPU workload starts.

Added `test_scale_config_accepts_sdk_instance_function_without_class_attribute`, which explicitly asserts the instance is a dataclass, the class does **not** expose `function`, and the instance points to the SDK module's actual extracted `flat_terrain` function object before exercising `adapt_cfg`. The SDK source path exists on `4090`; these tests have **no skip condition** and the SDK-backed fixture executes for every configuration case.

Actual RED, before the production fix, from the scale adapter cwd and the same amp CPU environment:

```text
python -m pytest -q --tb=short -p no:cacheprovider tests/test_scale_layout.py -k instance_function
AttributeError: type object 'MeshPlaneTerrainCfg' has no attribute 'function'
1 failed, 57 deselected in 1.43s
exit_code=1
```

Minimal production fix: import `flat_terrain` from `isaaclab.terrains.trimesh.mesh_terrains` inside the existing 1024-only branch and compare `sub_terrains["flat"].function is flat_terrain`. The exact original `MeshPlaneTerrainCfg` instance-type check and rejection of a replaced function remain in force; eight-environment behavior is unchanged.

Focused GREEN after the fix:

```text
python -m pytest -q --tb=short -p no:cacheprovider tests/test_scale_layout.py
58 passed in 4.24s
exit_code=0
```

There were **zero skips**. Full regression then completed using the exact full command already recorded above:

```text
431 passed in 78.20s (0:01:18)
exit_code=0
```

This is all 373 unchanged legacy tests plus 58 scale tests, including the executed actual-SDK regression; no tests skipped. `bash -n run.sh` in the same successful command produced no output and exited 0.

Updated local/remote SHA256 agrees:

| File | SHA256 after SPEC P1 correction |
| --- | --- |
| `scale_layout.py` (unchanged) | `11cea40eea64d9182e5ae5d23e249018d3246486bbd438077512d4317f4b8633` |
| `runtime.py` | `ebd8fc2e5377005ead28fc7a023f88478121054a4aca4ed26a087185eff53063` |
| `run.py` (unchanged) | `4427611013f1e7ecf73c7124e8c9da503d84fafed2cffe5b688646f1257ab02a` |
| `tests/test_scale_layout.py` | `05ded321779cc15eff0b5993c89034c916e099b18e750264aecc452d3cfb8660` |

The candidate still differs from the frozen source in only the same four files, now 573 insertions and 8 deletions. This corrective pass changes only runtime's function identity comparison/import, the new test file and this evidence log. Formal adapter versus `646f486` and formal versus frozen candidate remain byte-identical. No Task 2 work, formal/SDK edits, commit, GPU workload or signals to user processes were performed.

## Final independent acceptance of Task1 (CPU only)

SPEC re-review PASS: reviewer independently reran58 tests4.99s and restored the old expression only in memory, reproducing the same AttributeError with the actual SDK decorator fixture. Quality review PASS with no Critical/Important issues; independent58 tests4.04s. Minor static runtime-metadata assertion weakness is nonblocking because wiring is correct by inspection; Task2 executable orchestration coverage will check its actual write/payload.

Main independently ran58 tests4.11s and **full431 tests77.79s**, both exit0/no skips, plus bash syntax0. Four local/remote hashes match the corrected table above. Task1 is frozen byte-for-byte in local `m1_reference_validation_stage/scale1024/task1_accepted/adapter` and remote `/home/hexinkun/m1_debug_tools/scale1024_20260918/task1_accepted/adapter`; fresh directory prechecks and remote diff-qr succeeded. These are evidence snapshots, not formal promotion. Task2 now owns changes to the working scale candidate; no1024GPU or10000training has begun.
