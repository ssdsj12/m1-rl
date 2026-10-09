# Measured-support correction: full lift and roll, LAND contact loss remains

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), support-relative COM child.
Baseline Ref:3da996e. Candidate Ref:this commit. Previous turn classified progress:
physical posture-only comparison ruled out that intervention as the support fix.

## Feasibility and implementation

Read-only measured halfplane audit at preceding rejection: row0 needs minimum
78.84455mm entry-relative reference under instantaneous COM translation model
to retain35N and20mm. Within80mm; not a dynamic/whole-trajectory guarantee.
Other rows need13.28..78.73mm. No threshold/bound relaxation.

New explicit `--unload_support_feedback` requires anticipatory PREPARE. Keep
the selected entry forecast in PREPARE; during UNLOAD reuse existing measured
support/COM transfer_target with existing35N front/40N rear reserves. Hold
selected shortening when static reserve insufficient. Normal exit requires
measured unload gate + reserve + reference speed<=1mm/s; final budget check
recomputes fresh support feasibility, not stale readiness.

First physical attempt (`/tmp/m1_unload_support_20261008.log`) timed out at100
UNLOAD samples, no LIFT. Two FBL rows stayed below reserve. Investigation found
double limiting: `transfer_target.root` is already one speed-limited step, then
the acceleration ramp used that tiny step as its destination. New path now sends
`transfer_target.desired_root` to the bounded ramp. Existing speed.04m/s,
acceleration.05m/s2, entry80mm, joint.5rad/s and all phase budgets unchanged.
Legacy/default path unchanged. Later IK/world-frame checks validate actual ramp output.
First log SHA256:`c026953b0f42b4b141abce8a8be61ffa636cb14932ee2b73df96827a74bff866`.

## Tests

Observed RED for missing opt-in, missing exit checks, then incorrect ramp target.
GREEN actual probe wiring; numerical5mm ramp comparison demonstrates old
double limiter lag while maintaining speed/acceleration bounds.
144 tests passed: prior103 plus unload-support-feedback and load-transfer tests.
`git diff --check` clean. CPU tests alone are not physical success.

## Corrected physical run

Same eight-env flat/SDF128/rest1mm fixed-physics cycle as baseline, plus
`--unload_support_feedback`; existing anticipatory and attitude flags retained.
PREPARE200, UNLOAD100 budget, LIFT90/ROLL20/LAND90, SETTLE100; no long training.
Session75662 exited0 (diagnostic termination). Log
`/tmp/m1_unload_support_goal_20261008.log`, SHA256:
`3c0c116225617031f84dbb3b9446f897ff1285c500b65a56e83686f3d30631be`.

- All8 UNLOAD ready at sample84 (85 observations), all reserve flags true,
  all stable streaks>=5 and reference velocity<=.184mm/s.
- All8 complete LIFT90: measured wheel-center rise159.359..159.799mm vs160mm target.
  This is flat lift height, NOT obstacle-envelope clearance.
- All20 ROLL samples executed, then12 LAND samples. Total122 samples.
- Stop `lift_guard_rejected` at global121/LAND11, row5 selectedFAR;
  supporting RBL normal force8.193N<10N. Other rows remain valid.
- Previous sample120 static allocation valid all8; row5 minimum36.440N.
  Dynamic contact loss remains despite feasible static allocation.
- Actual support-center progress22.10..24.50mm; no obstacle present,
  no touchdown/settling success, `landing_complete=false`.
- At roll109 row5 commanded support speeds[.100,.0954,.0982]m/s;
  at LAND120 still[.056,.0514,.0542]m/s while lowering. Braking/descending
  overlap is a concrete next hypothesis, not yet a proven sole cause.

## Resource / continuation

First attempt stopped verified placeholder3976474; restored4017729, checked
before second attempt. Corrected attempt restores4039652; verified sole GPU7
compute process. No unrelated jobs, GPUs, display services or drivers changed.
No long training, no upload, no successful crossing claimed.

Next child: ROLL→LAND braking/contact dynamics; inspect phase/substep evidence
and coordinate bounded braking with lowering. Do not relax support guard or
silently extend single-leg4s budget. Full stable landing, obstacle clearance,
multiple obstacles, bypass and policy-only model remain unverified.
