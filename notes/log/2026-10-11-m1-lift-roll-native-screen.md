# Dense lift-roll: isolated native screening

## User amendment: identical counts/layout, height only

User explicitly corrected the candidate to identical obstacle counts, changing
only height. All three stages now use8targets atX=-1.2+1.1i/Yalternating±.215,
same horizontal shapes and70fills; only3/6/10cm heights differ. Stage0/mixed4+
unchanged. New equality test observedRED([4,6,8]!=[8,8,8]), then full17-file
regression **214passed4.31s**. Only isolated candidate was synced, not production.
New bounded CPU/native checks use this manifest; earlier4/6/8 evidence below
is historical, not deployment authorization for the amended layout.

![Current equal-count candidate](artifacts/2026-10-11-m1-lift-roll-layout-equal8.png)

## Scope / method

T306 `lift-roll-layout/native-readiness`, following the approved
[spec](../../docs/superpowers/specs/2026-10-11-m1-alternating-lift-roll-design.md)
and [whole-body evidence](2026-10-11-m1-fullbody-candidate-search.md).
Inline current-mirror implementation. No swing/controller/teacher or PPO data
from diagnostic placements. Explicit `m1_lift_roll` authoring uses20cm gaps,
70physical fills plus4/6/8 targets. Stage0/mixed4+ stay legacy; production
still selects `m1_progressive`. Candidate files only in the local mirror and
remote `/tmp/m1-lift-roll-candidate-20261011`.

![Exact candidate central corridor](artifacts/2026-10-11-m1-lift-roll-layout-candidate.png)

Figure generated from `candidate_blocks(row,fill_gap=.20)` by the archived
figure script; central corridor zoom only. Physical fill spans the full tile.

## Tests / review

Authoring RED4→GREEN: exact shapes/roles/centers, unique paths, semantic-small,
registry counts and legacy rows. Review found two Important measurement
issues: early transient collision/pose drift omitted; side-force counted as
ground support. Seven diagnostic counterexamples RED→GREEN. Combined17-file
regression **213 passed4.24s**, not full-repository tests.

Every physics tick now records requested/measured root/joints, source-mesh
wheel bottoms, force vectors and all-geometry clearance. Support requires
upward force>10N, bottom within4mm of floor and horizontal free space; lifted
wheel unloaded. All-tick geometry/pose evidence cannot be erased by settling;
last5ticks must support. Diagnostic2cm/5degree/.04rad drift bounds classify
sample validity, not runtime crossing thresholds. Static fixture failure is
not proof that the approved three-wheel rolling action is impossible.

## Live checkpoint preparation

04:24UTC PID948 cmdline/cwd matched original2048env run10-56-34/bb57e7d,
stdout1343, GPU21862MiB. CPUmodel1300: iter1300/next1301,39finite weights,
33finite optimizer states,16positive std,stage1,actor1589/critic1592/actions16,
CUDA uninitialized. SHA256
`daf2ed704972a3e469dfbfa33c583fd914c56368f2428220d177c6bad253252a`.
PT.last2059completedepisodes/pass.1219038368/1730strictattempts/0success.

Bounded one-shot helper PID2750 waits for model1400 CPU validation before
SIGINT only to PID948, checking starttime224786776/cwd/cmd.30min timeout,
no restart behavior. Avoid discarding updates1301 onward. Native not started.
Raw TB through1351: recurringprelift(max6/rollout),stable/strict0,stage1,
finite losses; old-layout evidence, not candidate efficacy.

## Acceptance / follow-up

Wait for model1400/process exit/GPU release, then isolated4env native under
the existing kernel lock. No failing/unverified candidate may replace
production.2048env capacity and actual continuous policy crossing remain
separate gates. No all-pose anti-bypass/no-slip/balance or learned10cm claim.
VerifiedProduction5a366ff; Task2f7a12d1. Relevant sources: semantic_course.py,
m1_lift_roll_probe_checks.py,probe_m1_lift_roll_layout.py and their tests.
