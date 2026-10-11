# M1 lift-and-roll candidate: roles pass, terrain readiness withheld

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
`pure-ppo-learning/density-exposure/lift-roll-layout/top-bridge-conflict`.
Spec and target/fill role are approved; user selected current-mirror inline
execution. No further approval of those decisions is needed.

## Scope / refs

Baseline:e8260f7; role implementation:267d882; candidate ref: this log's commit.
Production feature remains5a366ff with routea8923f2, published260b3a1.
Key files: `Go2Pvcnn/ame_baseline/m1_lift_roll_layout.py`,
`Go2Pvcnn/scripts/audit_m1_lift_roll_candidate.py`,
`Go2Pvcnn/tests/test_m1_fill_roles.py`, `test_m1_lift_roll_layout.py`.
CPU source is isolated at `/tmp/m1-lift-roll-candidate-20261011` on
`a21472797434572800304964`, not the production worktree. Source USD is read-only
from production `m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd`.

## Role and geometry TDD

- Role RED9 failures/1pass against old source; GREEN47passed2.03s, repeated
 47passed1.77s via task-done. Explicit false excludes encounter targets only;
 all landing geometry stays, both grounding paths preserve True/False/None,
 non-bool metadata rejected, legacy absent/None unchanged.
- Candidate RED14 assertion failures for missing implementation; GREEN14passed
 1.39s. Then fill-gap diagnostic parameter RED1failure/14pass, GREEN15passed1.40s.
- Combined15-file CPU regression202passed3.99s: fill roles, lift-roll candidate,
 registry, flat-first terrain, required/strict/dynamic crossing, persistent
 crossing/route rewards, obstacle rewards, learning curriculum, recovery runtime,
 dense-forward, AME runner checkpoint and semantic curriculum layout. This is
 the named relevant selection, not the entire repository.
- Stage1/2/3 retain4/6/8 targets at3/6/10cm and existing X/Y. Initial fill96
 blocks per tile, continuous rolling strips Y=+/-.215, halfwidth.13m; spawn
 X[-2.55,-1.45],Y[-.8,.8] empty. Domain[-7.95,7.95], length.5m/gap.02m.
 Clipping seams at spawn also get a gap, so tops do not touch by construction.
 This topology property alone is NOT enough to prevent rolling across tops.

## Reproducible CPU audit

Run `scripts/audit_m1_lift_roll_candidate.py --asset <production USD>` from
the isolated candidate with `CUDA_VISIBLE_DEVICES=`, `OMP_NUM_THREADS=1`, and
`PYTHONPATH=Go2Pvcnn:<isaacsim>/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310`,
`LD_LIBRARY_PATH=<same USD extension>/bin`, using env_issacsim Python.
The USD library import requires those explicit paths, but does not launch Kit.
Repeat with `--fill-gap .20` for the counterfactual. Audit exit2 deliberately
means a negative candidate-readiness result, separate from passing software tests.
Machine-readable outputs: `/tmp/m1-lift-roll-audit.json` and
`/tmp/m1-lift-roll-audit-gap20.json` (first output predates the reporting-key
rename from ready_for_native to candidate_rejected/native_readiness_proven).

### Recovery / mesh evidence

Both gap choices: front/rear recovery starts and0..45mm forward travel sampled
at6 points for every target, all four wheel XY circles checked against EVERY
target/fill block. Stage1/2/3:48/72/96 poses, minimum margin10.792mm;
terminal root margins3.666292/1.266292/.166292m. These are nominal samples, not
dynamic recovery or a certificate between arbitrary policy poses.

17actual collision meshes read from USD with joint-origin FK at the585mm pose
and uniform ABAD offsets0,+/-.05,+/-.10rad. For vertices at0..height+3mm,
minimum inside-strip margins for nominal3/6/10cm:106.451/60.700/60.700mm;
worst bounded offset:19.941mm. This is a source vertex-envelope check, NOT a
swept convex/triangle/native collision or supported-motion proof. The perturbed
poses are diagnostic, never fed as control actions or claimed as stable support.

### Anti-bypass counterexamples and limitations

Full-tile2mm grid (7951x7951), 8-neighbor connectivity, optimistic inscribed-disk
radius23.25mm, seed at all four nominal spawn wheel centers; includes complete
fill geometry and spawn seams. Ground-only results:

| Fill gap | Fill/tile | Ground-disk exit X>=7 | Elevated straight corridor |
|---|---:|---|---|
| .02m | 96 | No in all3 rows | Bridgeable in both wheel lanes at rootY=1.2 |
| .20m | 70 | Yes in all3 rows | This equal-height edge-bridge witness breaks |

At2cm seams a circular tire of radius.095958m drops only
`r-sqrt(r*r-(gap/2)**2)=.000522483739m` while crossing the largest gap.
Thus disjoint equal-height tops still offer an elevated rolling corridor.
This falsifies the intended no-driveable-platform gate; it does not prove a
policy can mount that corridor from spawn, or demonstrate learned bypass.

At20cm seams, the optimistic disk finds ground routes to the tile exit. That is
a possible-bypass witness requiring further whole-vehicle analysis, NOT proof
that all wheels/body can execute it. Maximum clipping seam is30cm. Neither
candidate establishes the requested no-bypass whole-robot layout. A no-path
grid result is likewise not an all-posture/continuous mathematical proof.

## Decision / next step

Task2 implementation is a retained, tested but rejected/unaccepted candidate;
Task3 production integration/native deployment/resume/publication is gated off.
Do not change landing_free, strict thresholds, controller/std or initial posture
to make it pass. The conflict is in this uniform equal-height fill packing,
NOT evidence that the approved single-wheel lift/three-wheel roll action is
impossible. Next design work must break the elevated corridor without opening
a complete ground detour, with whole-vehicle/surface connectivity validation.
Simply choosing an intermediate uniform gap is not a justified solution.

03:54:48UTC live check: PID948 cwd and cmdline still production2048/cuda0/
keep_std, stdout1226, strict rates0; no stop/signal, no GPU probe or production
source changes. Do not replace it with this candidate. Latest saved PT must be
freshly located/CPU validated before any future deployment stop/resume.
New candidate/roles are not published to GitHub as a production layout.
