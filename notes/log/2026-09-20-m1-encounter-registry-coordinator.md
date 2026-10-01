# M1 registry / encounter coordinator implementation verification

## Scope and current state

- Date: 2026-09-20; stage G0 registry and lifecycle core; node T306.6h.6a.1a.2c.2.
- Baseline: isolated `codex/m1-encounter-lifecycle`, HEAD `8e60686`.
- Candidate: registry `394ea67`; coordinator `d27e26c`, both isolated. Four new code/test files only; no existing runtime controller file changed.
- Approved design: [encounter lifecycle](../../docs/superpowers/specs/2026-09-19-m1-encounter-lifecycle-design.md).
- Plan: [integration](../../docs/superpowers/plans/2026-09-19-m1-encounter-integration.md).
- Input: real static geometry metadata and typed raw samples; pure CPU core only, not simulator input acquisition or learned control.
- Output: object association evidence, immutable identity snapshots, ordered crossing history, explicit pre-prepare boundary decisions.
- Downstream still open: vendor instance hook, row cache reset, sync release/begin, lossless raw sidecars and independent replay; then new physical G1/G2 gates and training.

## Main-agent TDD and additional regression

Commands run in `/data/hexinkun-m1-acceptance-20260918/encounter-worktree`, using `/home/hexinkun/miniconda3/envs/amp/bin/python`, `CUDA_VISIBLE_DEVICES=` and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.

`python -m pytest -q tools/m1_reference_validation/tests/test_encounter_coordinator.py`

- Initial RED: 26 failures at explicit missing-module assertion. Log: `/data/hexinkun-m1-acceptance-20260918/coordinator-red.log`.
- Initial implementation: 25 passed / 1 failed. The boundary fixture used decimal `.035`, while the exact predicate is `.03 + .005`; test corrected to that computed boundary without changing the strict predicate or physical margin.
- First GREEN: 26 passed.
- Added actual second-object lifecycle, persistent visibility, ongoing phase mixed rows, malformed packet/reset and tie tests: 47 passed. A fixture initially expected a redundant extra waiting sample for the second object; corrected because its own earlier physical front evidence already exists. No timer was added.
- Raw typed-input and explicit wrong-corridor outcome RED: 3 failed / 49 passed. Fix: reject sequences before NumPy promotion, and return `UNSUPPORTED` for a wrong required-wheel corridor rather than an unexplained wait. GREEN: 52 passed.
- Mixed `on_reset([False, 1])` RED reproduced loss of boolean identity from NumPy promotion. Validate each original row ID before conversion; GREEN: 53 passed / 0 skipped.
- Further RED→GREEN: empty classified hits cannot give bootstrap permission; raw_gate=false cannot report START without a boundary. Added explicit source/coordinator hashes to boundary credentials after SPEC feedback.
- SPEC reproduced unkeyed initial phase0/5/10/11 and uncredentialed phase0 during departure. All five RED; now reject these malformed phase/identity combinations before state mutation. Existing CROSSING phase0..10 gate inputs remain untouched. Coordinator after this fix: 60 passed.
- All CPU traces are constructed test inputs, **not** physical return, crossing, route or policy acceptance.

## Registry oracle corrections and CPU scale evidence

- Existing production registry initially had 116 passed / 2 failed: two tests had already applied `np.asarray` to mixed bool/float or large-int/float input before the API, irreversibly erasing the type being tested. Corrected only the fixtures to typed bool/int64 negative arrays; raw production float32/float64 inputs remain unchanged.
- Full1 also exposed a process-global import guard polluted by earlier legitimate USD tests. Moved the guard to a fresh subprocess; this fixes test isolation, not SDK behavior. Original logs retained.
- Main CPU benchmark on constructed 1024-row input, one classified ray/row: prepare+observe 12.514516 seconds; 8 rows 0.003413 seconds. The exhaustive Python loop visited every scene box for every row.
- Added a 1024-row association CPU budget test: RED at 11.875 CPU seconds against a generous 4-second ceiling. Added float32/float64 all-ray comparisons against an independent exhaustive oracle, covering overlap, ownership, mixed classes, missing and invalid hits.
- Fix is a conservative all-owner/all-class finite-hit-cloud AABB broad phase. Any box containing a hit must intersect that cloud AABB. The original per-hit class, bounds, ownership, count and precedence checks still run on every potentially matching box. No scanner/physical threshold changes.
- After fix: registry 121 passed; coordinator + registry 181 passed in 1.41 seconds. Same CPU benchmark: 1024 rows 0.360779 seconds, 8 rows 0.002978 seconds. This is a CPU association diagnostic, not 1024 Isaac capacity or behavior acceptance.
- Registry independent SPEC then QUALITY PASS on the latest broad-phase source. QUALITY also ran 121 tests successfully in 1.30 seconds.

## Preservation and resources

No existing production controller, SDK, driver, reference source, model, old raw evidence, or main-tree source was edited. No native simulation or training process was started by this package.

Fresh resource inspection found GPU7 UUID `GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e`, only user `hexinkun` process `3919095 python sleep.py`, start `Sun Sep 20 11:00:44 2026`, 15744 MiB. Old recorded PID351307 is gone; do not act on it. This turn did not stop, replace or restart the reservation. Root has 508 GiB available and `/data` 6.2 TiB; no storage operation is required.

## Review / full regression

- Full1: 2304 passed / 3 failed / 259.73 seconds, all three new-registry test-oracle/isolation defects above. Log: `/data/hexinkun-m1-acceptance-20260918/encounter-integration-full1.log`.
- Full2 after those test corrections: 2309 passed / 0 skipped / 258.41 seconds. Log: `/data/hexinkun-m1-acceptance-20260918/encounter-integration-full2.log`. This predates the later broad-phase and phase-identity fixes and does not verify them.
- Full3 latest production: **2317 passed / 0 skipped / 252.31 seconds / exit 0**. Log: `/data/hexinkun-m1-acceptance-20260918/encounter-integration-full3.log`. The stronger continuously visible next-object fixture (old phase11 retained) was added after that suite's test collection; a fresh targeted run passed, and final full focused union **181 passed / 1.46 seconds / exit0** includes it. Log: `/data/hexinkun-m1-acceptance-20260918/encounter-core-final-focused.log`.
- Coordinator SPEC then independent QUALITY both PASS. Source-hash fields and unkeyed/unauthorized phase failures were corrected via RED→GREEN. A proposed `phase<0` restriction was rejected after checking original helper behavior: it would force a global gate gap. The legitimate phase11 boundary instead requires Task C's row initialization before the helper. QUALITY's negative-ID concern was independently reproduced as a false positive: `_int64(..., minimum=0)` already rejects it and five invalid-reset cases pass. No redundant production change was made.
- Source SHA256: registry `2684bdab79745b7fe9587df818e465363737fb1e292208ba92c25eee0a602200`; coordinator `c8305b1e352eb7f6cdf35e2e8faf2f7adc6cf1f4fda3323401b0353d758d8c1c`.
- Test SHA256: registry `c226f9c657a88bd54fbcdd36b7703edd390f54f0af9da5d1f23501e782276d63`; coordinator `cb1eea950050b725748f2294d329c27ba7e5c6e743362896e0aea353f66a6270`.
- Bash files unchanged. No new native handle exists; all CPU test/benchmark sessions ended.
- Final coverage-only addition (production unchanged): explicit rotated-direction and left-wheel-side UNSUPPORTED cases, plus two valid faces of one object AMBIGUOUS even at different distances. Fresh union **184 passed / 1.44 seconds / exit0**, including 63 coordinator + 121 registry tests. Log: `/data/hexinkun-m1-acceptance-20260918/encounter-core-extra-domain.log`. These negative domain tests do not implement G2 action mappings.

## Conclusion and follow-up

Concrete progress is a tested and independently reviewed registry/lifecycle core, not a live behavior fix. Keep the full goal ACTIVE. No claim of G1/G2, 1024 behavior, policy-only cross/avoid or 10000 PPO updates is made. Next is source-bound hook and encounter-aware sync plus raw evidence/replay before new physical validation. Task B's integration items and all Task C/D gates remain open; do not restart the already verified geometry audit.
