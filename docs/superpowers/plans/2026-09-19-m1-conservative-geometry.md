# M1 Conservative Collision Geometry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Supply a source-bound immutable conservative collider-local representation from the complete live cooked capture, preserving the existing exact-query FAIL.

**Architecture:** Revalidate the source/query manifest and independently replay the pure collector from detached complete hull records. Union actual hull extrema and original query bounds; represent native cylinders analytically with source and float32 parameter coverage. A separate live owner, not a closed diagnostic report, is required before per-step geometry may be consumed by the encounter coordinator.

**Tech Stack:** Python 3.10 / NumPy / pytest; remote amp CPU tests, existing isolated branch `codex/m1-encounter-lifecycle`.

## Scope and baseline

- Approved spec: `../specs/2026-09-19-m1-encounter-lifecycle-design.md`, especially sections 4.2, 5 and 8.
- Baseline/last verified: `36bec9240bf90dc8d30e6999679a535bdf56e972`; 1785 CPU tests passed on its unchanged code ancestor `c02bde0`.
- Existing negative capture stays immutable: `/data/hexinkun-m1-acceptance-20260918/cooked-live-20260919-1703/collision_query_initialization.json`.
- 104 complete Mesh hulls / 3664 vertices, 32 native Cylinders; 40 raw-box containment failures, max 7.450580596923828e-9 m. This package does not modify the raw diagnostic, physical `.005 m`, `_ROUNDING_ATOL`, controller, SDK, leases, or training budgets.
- Stage/source frame v1: meter/Z-up, exact unit body scale, identity collider-to-body matrix. Reject other transforms explicitly; a general cooked-scale contract is not inferred from an identity-only live scene.
- Local bounds are not world extents, source freshness, G1 success, PPO updates or 10000-iteration completion.

## Task 1: Immutable local geometry builder

**Files**

- Create `tools/m1_reference_validation/collision_geometry.py`.
- Create `tools/m1_reference_validation/tests/test_collision_geometry.py`.
- Read, do not change `collision_cooked_evidence.py`, `collision_query.py`, `encounter_geometry.py` and their fixture helpers.

- [x] Write tests first, using actual existing source/query fixture builders and the real pure collector.

```python
import copy
import numpy as np
from test_collision_cooked_evidence import artifact, collect, VERTICES
from collision_geometry import build_collision_geometry

def test_raw_containment_failure_is_preserved_but_complete_union_is_built(artifact):
    vertices = VERTICES.copy()
    vertices[0, 0] = np.nextafter(1., np.inf)
    cooked, _ = collect(artifact, payload={'num_vertices': 6, 'vertices': vertices})
    before = copy.deepcopy((artifact, cooked))
    geometry = build_collision_geometry(artifact, cooked)
    assert geometry['raw_query_containment_status'] == 'failed'
    assert geometry['geometry_status'] == 'constructed'
    assert (artifact, cooked) == before
    mesh = next(r for r in geometry['records'] if r['type'] == 'Mesh')
    assert mesh['bounds_local'][1][0] == vertices[0, 0] > 1.
```

The existing `artifact` pytest fixture supplies the actual USD/source/query contract. Additional tests must prove: complete multi-hull union, larger original query retained, X/Y/Z native cylinders (float32 rounded upward/downward), no manufactured cylinder vertices, zero/unavailable/failed/partial getter results rejected, exact input identity/hash/count/record/hull coverage and derived diagnostic consistency, numeric boolean/string/nonfinite/overflow/float32-zero rejection, unit/frame restrictions, detached output, original FAIL unchanged.

- [x] Run the new test before creating production code; record expected missing-builder failure. Use `getattr(importlib.import_module(...), ..., None)` with an explicit callable assertion if needed to avoid collection-error-only evidence.
- [x] Implement `build_collision_geometry(artifact, cooked)` with this complete algorithm:

```text
1. Call existing _preflight(artifact); validate JSON serialization and hash.
2. Require cooked's exact expected schema/representation, all identity metadata,
   record order/coverage from targets, available Mesh with nonempty complete
   ordered hull records, and native_query_only Cylinder with no hulls.
3. Re-run collect_cooked_evidence(artifact, replay_count, replay_mesh), where
   replay_count returns number of supplied hulls and replay_mesh supplies only
   raw num_vertices and vertices. Compare canonical hashes of the entire replay
   and input cooked report. This validates all existing counters, extrema,
   booleans, errors and result without accepting arbitrary failure strings.
   Pre-require all Mesh availability=available so a partial capture cannot pass.
4. Independently validate source/inventory meters/Z-up, each body's exact unit
   scale and collider's exact identity collider_to_body_column_matrix. Verify
   body_index is a strict integer matching the named body order.
5. For Mesh, set bounds=[min(query_low, all vertices min),
   max(query_high, all vertices max)] coordinate-wise. No arithmetic tolerance.
6. For Cylinder, require strict native-mode setting, axis X/Y/Z and positive
   finite source dimensions. Convert dimensions to float32, reject overflow,
   zero or negative conversion. radius=max(source_radius,float32_radius),
   axial_half=max(source_height,float32_height)/2; reject underflow/overflow.
   Set analytic halfwidth on axis and radial widths on other axes; union with
   raw query. Record analytic recipe/parameters, never fake vertices/hulls.
7. Return a detached JSON object: schema m1_collision_geometry_v1,
   geometry_status constructed, representation_status conservative_collider_local,
   coordinate_contract identity_collider_to_body_meters_v1,
   source/query/cooked fingerprints, stage_id/geometry_generation,
   raw_query_containment_status equal to the preserved collector result,
   raw_containment_error_count, environment/body mappings, ordered records
   with original identity, bounds_local and construction recipe.
8. geometry_sha256 hashes the complete output without its own hash field.
   No object returned grants native ownership, source freshness or CLEAR.
```

- [x] Run targeted new and collector tests (CUDA disabled), preserve RED/GREEN logs. Run `git diff --check` and compare input negative JSON SHA before/after.
- [x] Commit exactly the new module/tests after focused GREEN; main performs independent spec review then quality review.

## Task 2: Actual negative-capture replay verification

**Files:** new verification log under `notes/log/2026-09-19-m1-conservative-geometry.md`; update `notes/todo.md`, `notes/todo/T306-m1-ame-long-train-stability.md`, `notes/log/index.md`.

- [x] On amp CPU load the existing immutable negative capture; call the new builder once and separately check every vertex against the emitted local bounds, plus all original query bounds.
- [x] For every Cylinder independently derive all three analytic extrema, including source and float32 dimensions, and compare against emitted bounds. These analytic extrema are tests, not a saved hull.
- [x] Recompute the output hash, record 136 identities, 104 Mesh / 3664 vertices / 32 Cylinder counts, and SHA of original JSON unchanged.
- [x] Run main targeted tests and full suite after review; record exact exit codes/counts. Do not repeat Kit without a live-owner implementation.
- [x] Update notes with completed local representation and next live owner/world-projection integration; leave full encounter/PPO goal open. No claim of coordinator wiring from a JSON-only result.

## Continuing integration boundary

The next coherent implementation package, after this representation's reviews, owns an open CollisionSceneLease, checks unchanged initialization state, captures all 17 native body link poses per step, computes conservative world/frame projections, and closes the lease before env.close. Existing `probe()` still closes its lease and still fails exact raw containment. It must not be repurposed as a long-lived provider by ignoring errors. No user approval is needed to implement this already-approved boundary; mathematical and lifecycle contracts must first pass tests.

## Self-review

- Covers the local-geometry prerequisite in spec sections 4.2/5/8; does not claim to implement state machine, live freshness, route action or policy.
- Exact raw diagnostics, old artifact, physical thresholds and actual denominator preserved.
- No source-bounds fallback, no query-only fallback, no ULP guess, no cylinder fake hull, no SDK/private-pointer addition.
- File responsibility and function names fixed above; input validation uses existing checked manifest/collector rather than a parallel protocol.

## Review correction: lossless numeric ingress

Completed: initial feature `7b6ddd7`, correction `3d97e9b`; final focused222/main1929full tests, SPEC→QUALITY PASS, actual136collider replay unchanged. Full goal remains ACTIVE; this plan completes only the local representation prerequisite.

Independent QUALITY and main reproduction found that JSON integer Cylinder radius/height `2**54+1` silently becomes `2**54` through float64 conversion, yielding an inward bound. Actual live source uses floats, but the public numeric contract must not accept this loss. Add a local builder check; leave the shared collector and `_real_array` unchanged.

- [x] Add RED tests for radius and height with `2**54+1` and for the equivalent raw query AABB ingress if reproduced. Include mixed integer/float array endpoints so NumPy promotion cannot erase the original integer before validation. Preserve exact integer and existing float success cases.
- [x] Reject integers whose original mathematical value is not exactly represented by the resulting float64. Validate original objects, not already-promoted NumPy values. Apply at Cylinder source dimensions and original query bounds; identity matrices/scales retain their existing exact-identity rejection.
- [x] Run focused GREEN, commit only builder/tests, and rerun SPEC→QUALITY limited to the correction, main actual replay and main full suite using a new basetemp. Old RED/GREEN/full/actual evidence stays intact.
