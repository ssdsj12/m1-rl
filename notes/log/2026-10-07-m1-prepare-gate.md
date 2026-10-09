# M1 isolated PREPARE gate verification

Stage: AME contact-driven teacher foundation.
Related: [T306.contact-transfer.prepare-gate](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref: `dacfb46`, snapshot of existing dirty source; original checkout preserved.
Candidate Ref: `codex/m1-contact-crossing`, commit containing this evidence.
Key Files: [gate](../../Go2Pvcnn/ame_baseline/m1_prepare_gate.py),
[tests](../../Go2Pvcnn/tests/test_m1_prepare_gate.py),
[component plan](../../docs/superpowers/plans/2026-10-07-m1-prepare-gate-plan.md).

## Provenance and procedure

Worktree created at `.worktrees/m1-contact-crossing` after `.gitignore` exclusion.
Scoped tracked differences and untracked scripts/tests copied and byte-compared
against the original checkout with `cmp`. Baseline committed separately, explicitly
not as newly implemented functionality. Original uncommitted source was not edited.
No dependency installation or simulator invocation.

Baseline command: amp Python `-m pytest -q` with these seven test paths under
`Go2Pvcnn/tests/`: `test_support_geometry.py`, `test_crossing_event.py`,
`test_probe_evidence_contract.py`, `test_m1_foot_frame.py`,
`test_m1_cache_foot_frame.py`, `test_m1_runner_wheel_parity.py`,
`test_m1_unreachable_teacher.py`. Result: 23 passed in 2.12s.

RED: initial 16 gate cases failed on missing implementation. First GREEN attempt
revealed a test helper keyword collision for `step`; fixed helper name, then 16
behavioral cases passed. Added four malformed-input cases: three failed because
shape/type was accepted, one raised wrong error after state mutation. Validation
now runs before any state mutation. Combined command adds `test_m1_prepare_gate.py`
to the exact baseline set: **43 passed in 2.08s**, exit 0.

## Contract checked

Five continuous pre-action stable frames, >10N four-wheel contact in PREPARE,
abs tilt <=.15rad, abs tilt rate <=.20rad/s, supplied three-support planar margin
>=.02m, valid IK, finite evidence. Event/episode/leg changes and sample gaps reset
only their own rows. Repeated samples cannot accumulate readiness. Collision
poison survives a leg handoff within an event. Unknown obstacle IDs fail closed.
Wrong dimensions/types reject before mutation; valid observations remain usable.

## Limits and follow-up

Gate has no runtime consumers yet and makes no physical success claim. It does
not generate support transfer, validate margin provenance, manage stage timeout,
move a wheel, or count crossings. Existing teacher/training behavior unchanged.
Next implement observer and bounded load transfer, then coordinator and independent
event accounting before the approved 8-environment physical smoke.
GPU7 placeholder PID212779 was observed live before work; no GPU task was started
or stopped. No XLaunch/Xorg/VNC changes. Nothing pushed to GitHub this pass.
