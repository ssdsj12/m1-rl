# M1 stage1 perception and reward diagnosis (read-only runtime)

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
`pure-ppo-learning/required-crossing/diagnostic-wiring` (OPEN).
Baseline: bb57e7d. Candidate: codex/m1-contact-recovery plus existing dirty edits.
User asked to investigate, not deploy a fix in this turn. No production code,
weights, actions, training process, display configuration or GPU allocation changed.

## Runtime evidence

PID10311 identity/cwd/arguments verified: fresh2048/GPU0/10000/flat-first;
run2026-10-10_18-49-19/bb57e7d. Stage1 began at iteration300. At372,
latest complete2048-episode window had4322attempts,0success; pass1.0,
full1000-step episodes, no boundary/fall/nonfinite termination. Earlier stage1
43-update audit had zero prelift and stable-landing events. Attempts are per
completed window, not to be summed again on every repeated iteration log.
`M1_CONTROL_TRACE` and `M1_STEP_DEBUG` are absent in actual process environment.

## Confirmed recovery wiring defect

In `Go2Pvcnn/ame_baseline/ame_env_wrapper.py`, step-local `robot` is assigned
only by trace (1066), every32nd debug step (1100), or later strict block (1265).
Normal recovery block reads it at1213 before assignment. Broad except1247
silently replaces `recovery_balance_safe` with false.

CPU reproduction: parse actual remote source using ast; extract Try1190;
execute unchanged block with healthy identity quaternion, zero angular velocity,
nominal leg pose/root height and valid touchdown. Catch exceptions with
sys.settrace (the original except remains intact). Results independently verified:

- No prior robot binding: false + UnboundLocalError.
- Only prior binding to scene robot: true + no exception.

Strict tracker consumes this flag only for post-cross stable-frame accumulation.
Separate CPU ideal-trajectory replay: both flag values permit prelift and first
geometric event_complete; false prevents all8recovery frames and keeps the
encounter awaiting recovery. Curriculum counts recovery_complete only.
Thus stable landing reward/course promotion is blocked, but this does NOT by
itself explain observed zero prelift or zero first geometric completions.

Existing CPU dynamic/required/strict tests:50passed (reviewer run). They supply
support_safe directly and do not execute wrapper's no-debug recovery path.
Missing regression: wrapper healthy recovery with trace/debug disabled.

## Perception evidence and limitations

Saved scanner:1.5x1.5m,1cm grid151x151, attach_yaw_only=true,
ray_alignment=base. All2048ids are processed in512-row chunks; it does not skip
the other1536 environments. Map has1536values (6x16x16) before53state values.
Scanner includes ground/small/large meshes. Actual online per-object pixels
were not captured, so complete live coverage is not certified.

CPU production pooling on synthetic10x18cm blocks centered y=.215 and
x=.05..55 at1mm increments gives peak encoded bump heights:
3cm ->16.36..30.00mm;6cm ->32.73..60.00mm;10cm ->54.55..100.00mm.
Small-class labels survive max pooling but XYZ is averaged with ground.
The weakest small-labelled cell represents only0.743mm for a3cm block.
This proves information dilution, not that the actor is blind or that pooling
alone causes failure. Small numerical boundary differences depend on grid sampling.

Legacy yaw-only scanner and AME transform interpret equivalent configs differently:
same yaw-grid hit[.5,.2,-.456],pitch.2rad -> legacy/base full inverse
[.580626,.2,-.347576], modern/yaw [.5,.2,-.456]. This is config-equivalence
inconsistency; full-body coordinates can themselves be valid. Effect on learning
requires a controlled comparison, not an assumed perception failure.

Reviewer CPU checkpoint300 synthetic fixed-state flat/3cm-map A/B changed all
16action means (maxdelta.017445); encoder wiring is not disconnected. Synthetic
observations are NOT live rollout evidence or successful action verification.

## Exploration and sparse reward risk

Checkpoint300 leg action std=.00728..01348; actual action scale1.5rad,
not the obsolete .25 scale mentioned in comments. Thus target-angle std
.01092..02022rad. CPU fixed-root nominal-pose FK Jacobian predicts wheel-center
vertical std3.07..3.28mm. Seed603,100000 independent target samples: zero
samples per leg reach2cm. This is target exploration at nominal pose, NOT a
physical wheel-bottom measurement or actual learned-mean rollout.

Obstacle slabs remove all positive dense reward, retaining negative costs.
Only one-shot prelift>=2cm (.3) and stable recovery (2) give positive events.
Low exploration plus sparse threshold is a plausible learning bottleneck,
not independently proven as the exclusive cause. No noise/entropy/reward change.

## Follow-up

1. First fix wrapper binding with an actual no-debug step-path regression;
   retain strict physical success criteria and expose unexpected measurement errors.
2. If authorized, validate at a saved-PT boundary without concurrent native GPU
   probe; only current fresh lineage may be resumed, never old8573 weights.
3. Capture per-wheel loaded baseline/contact/bottom rise, actual map near object,
   and reward gates to distinguish no physical lift from missed measurement.
4. Then assess incremental lift shaping while retaining no sliding/bypass rewards;
   observation-contract/noise changes require explicit scope agreement.

No claim of repaired runtime or learned3/10cm crossing. Production remains active.
