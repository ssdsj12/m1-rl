# Attitude-only feedback: better posture, unchanged support rejection

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), anticipatory-support /
anchor-drift child. Baseline Ref: eceb9db. Candidate Ref: this commit.
Previous goal turn was progress: code integration and physical evidence changed next action.

## Root-cause refinement

Rigid translation of BOTH COM and wheel support points does not change barycentric
support loads. Thus previous18.15mm anchor drift is a symptom/correlate, not by itself
a causal explanation. Extended read-only `audit_m1_anticipatory_run.py` reconstructs
actual measured joints at nominal entry attitude and actual measured attitude.
Row0 baseline: nominal36.446N; actual29.99065N; measured joints reset to entry
attitude35.10683N. Actual-pose reconstruction29.98680N (0.00385N error).
Other rows reconstruct within0.041N. Approximate counterfactual suggests posture
contributes~5.12N, but commanding posture is not the same as freezing joints and
rotating the measured robot. The physical comparison below explicitly tests this.

## Implementation

Default-off `attitude_feedback` in bounded `lift_target`: unit proportional
roll/pitch error about unchanged entry rpy, wrapped angular errors and previous
correction norm<=.08rad, absolute proposed RP<=.15rad, unchanged .5rad/s joint
slew/IK/backtracking/contact/collision guards. No translation or yaw correction.
Stance world anchors stay fixed; selected world-height correction retains its
own ownership. Whole-body pose-feedback combination is rejected.
Probe flag `--lift_attitude_feedback` requires isolated anticipatory world-height
cycle, remains active continuously through LIFT/ROLL/LAND/SETTLE if reached.

## Verification

RED: new argument unsupported (3 failures), then missing explicit CLI flag.
GREEN: feedback direction, unchanged root/yaw/stance anchors, joint slew,
row-local rejection and ownership separation; real probe AST checks opt-in wiring.
Full selected regression set:103 passed (previous74 plus single-lift,
attitude-feedback and probe-lift-gate tests), amp Python OMP/MKL2 and USDlibs.
`git diff --check` clean.

GPU7 comparison uses the exact preceding eight-env flat SDF cycle plus ONLY
`--lift_attitude_feedback`. PREPARE200/UNLOAD100/LIFT90/ROLL20/LAND90/SETTLE100
budgets, force/clearance/speed limits unchanged. Log `/tmp/m1_attitude_prepare_20261008.log`.
SHA256: `8852c306dd907a4ee3d91029e00ad036a81cca9f733396fcb2976718631c2996`.
Session15107 exits0. Actual PREPARE200 and UNLOAD66 exactly as baseline;
LIFT37 samples, stopped `lift_effort_rejected` at36, no ROLL/LAND.

Row0 at rejection:
- RP baseline[-.0128501,.00858076]rad -> candidate[-.00724450,.00513371]rad.
- Actual static support29.99065N ->29.99024N (no improvement).
- Actual selected rise53.827mm ->55.273mm, not target160mm or obstacle clearance.
- Joint tracking errors essentially unchanged; largest~1.95deg.
- Measured normal force35.51N does not override invalid static allocation.
- Reconstructed actual support29.98941N; at entry attitude32.53745N.
The commanded configuration changed, cancelling the counterfactual force gain.
This refutes posture-only correction as the support solution; no gain sweep.

## State / next

103 tests do not mean dynamic crossing passes. Keep both paths experimental/defaultoff.
No training or upload. Verified own placeholder3872161 before stopping; restored
3976474 and verified sole GPU7 compute process after probe exit. No other GPU jobs,
display services, driver/reset operations touched.

Open child refined: direct measured support-relative COM placement/control,
not world-anchor displacement alone or a larger attitude gain. Evaluate bounded
feasibility using actual support geometry and articulated COM, maintaining entry80mm
reference and all accepted pose/effort limits; do not bypass the allocation guard.
Full lift/rolling/obstacle envelope/landing/bypass/policy-only remain unverified.
