# M1 post-cross-only wheel synchronization implementation

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child T306.6h.6a.

## Scope and identity

- User explicitly approved the [written design](../../docs/superpowers/specs/2026-09-18-m1-post-cross-wheel-sync-design.md) with “确认，开始实现”.
- [Implementation plan](../../docs/superpowers/plans/2026-09-18-m1-post-cross-wheel-sync.md) permits one isolated amp / physical GPU7 / 8env ×1600-step physical test after CPU and review gates. No sweep, retry, promotion,1024 or10000 launch.
- Baseline Ref: formal adapter a86cbf5; design6c53e32. Formal adapter diff againsta86cbf5 remains empty.
- Candidate Ref: isolated `/home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter`; hash-identified diagnostic, not a promoted feature commit.
- Key Files: candidate `post_cross_sync.py`, `sync_bridge.py`, `sync_verdict.py`, `run.py`, `runtime.py`, and corresponding new CPU tests. Formal `metrics.py`, source guard, scene adaptation, native finalizer and `run.sh` remain unchanged.
- Last Feature Commit / Last Verified Commit for formal reference adapter remain a86cbf5. Do not replace these refs with an unrelated notes commit.

## Implementation and pre-physical evidence

The original prepare/IK is still called once. An independent ordered-event observer waits for both FAR/RAR crossing/landing events, phase11 history and five stable samples. Only the following prepare can replace wheel columns12:16. Current wave/leg activity, drive disallowance or root re-entry rejects the candidate before action override.

Fixed parameters remain dt.02, τ.20, Ki.5, bias bound1, slew1rad/s², feedforward[1,1,1.4,1.4]. The first new output holds the prior physical actual action. Integration is paused per environment when prior hold/limit or current support requires it. Explicit recorder reset generations invalidate old samples; wrapper done/reset fallback does not count callback-confirmed reset twice.

Live checks validate wheel joint names/order, velocity action scale1 and actual offset0, default wheel velocity0, implicit actuator20/30/0 velocity/damping/stiffness. Raw policy residual must be zero. Sidecars contain owned CPU snapshots of original/final/actual/processed targets plus state/identity. Parameters/reason bits/source hashes are recorded in both configuration and provenance.

Actual TDD evidence:

- Frozen baseline:212passed in23.91s.
- Core initial RED missing implementation; later RED for cross-generation packet and CPU/intermediate-overflow cases. Core GREEN100passed in30.34s.
- Bridge initial RED13failures; separate actuator-type and gate-reason REDs. Integrated bridge GREEN20passed in1.82s.
- Independent verdict initial RED29missing-file failures; review RED6forged finite state cases and one excess-ULP case; final GREEN41passed in19.77s. Actual core-generated CPU1600×8 variable velocities, projection saturation, slew and one-environment support pause match independent NumPy replay, final float32 targets bitwise equal.
- Final whole candidate regression:373passed in74.64s; bash syntax exit0. The earlier360/372test runs are superseded.
- run12 replay: first activation actions[249,253,248,251,245,248,248,247]; run13 first-episode env1/2/5 never activate. Both1600-step independent event timelines match frozen strict metrics. CPU no-delay/one-step-delay unit plants converge; this does not prove Isaac physical stability.

## Review checkpoint

Independent SPEC review found no control/core/bridge/native-cleanup issue, but reproduced a fail-open offline evidence gap: contradictory filtered velocity/error and hold integration flags could pass. Repaired verifier independently reconstructs events, stable gate and numerical state from physical samples. Adjacent float32 output rounding allowance is half-ULP per endpoint plus1e-12 double arithmetic, not a relaxed physical threshold. SPEC re-review PASS with an independent in-memory variable-velocity/support interruption cross-check. Subsequent independent code-quality review PASS, no Critical/Important issues; actual SDK API, reset order and absence of post-override clipping verified read-only.

Frozen candidate source SHA256:

| File | SHA256 |
| --- | --- |
| post_cross_sync.py | 18aeb0c711344af06dff41c49254048ea5f37cea94adc605c989e1f1057bc87c |
| sync_bridge.py | 817ed0358dda874e020661862d9019ba1bbe5abee4a99858f5b64fdb36390254 |
| sync_verdict.py | 1e93707e2f959b7ae2226438300a734ed3dd0911ffa782a589b98aa6986324bf |
| run.py | ba2b27001d864b9f4b6ebcfa2f2907c93d0c1e511c861151f4e06f5a47734d80 |
| runtime.py | 1825d1259759cb7950147de36263d932ec0e9f0372cd8a3a3dac61b66ff8ffbc |

## Physical result

Run14 launched once after all gates, childPID3813875, runIDd28c4da0-a2d0-4cd2-9027-90578430ca98. Physical GPU7UUID `GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e`, amp Python3.10.21, reservationPID2795762 preserved;8328MiB free at pre-check. Other users' GPU jobs are not touched.

**PASS for this single diagnostic candidate:** exact8×1600 in one process,1600original prepare/IK calls,6400physical sensor updates,50original sample chunks and50sync chunks. All normal cleanup markers observed, native0/wrapper0, no restart or reset. Original strict8/8 (run12 was4/8); independent `accepted=true`, `sync_checks_passed=true`, `errors=[]`, CLIexit0. Runtime before cleanup91.65s. ChildPID no longer exists; GPU7 returned to reservation-only15754MiB used/8328MiB free/0%utilization.

Evidence: [original strict report](../../run_logs/m1_reference_validation/20260918_gpu7_8x1600_14_post_cross_sync/report.json), [independent verdict](../../run_logs/m1_reference_validation/20260918_gpu7_8x1600_14_post_cross_sync/sync_verdict.json), [raw native log](../../run_logs/m1_reference_validation/20260918_gpu7_8x1600_14_post_cross_sync.log).

All8 completed the FAR/RAR ordered prelift→overbar→passed→touchdown events. Wheel/nonwheel own-bar force peaks0, reference collisionfalse, no termination or timeout. Every preactivation physical/action field matches run12 bitwise; source bindings, scene and initial randomization match exactly. Inactive16columns and every leg output remain bitwise original, actual action-manager actions and processed targets equal final outputs. Independent NumPy replay matches all recorded state and outputs.

| Env | Activation action | Old full-episode speed spread | New spread rad/s | Tail target Δ RMS | Tail actual velocity Δ RMS | Final forward m |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 249 | .096050 | .032240 | .000217262 | .150603 | 4.613205 |
| 1 | 253 | .096657 | .027289 | .000079132 | .008686 | 4.649669 |
| 2 | 248 | .078586 | .023408 | .000339108 | .067101 | 4.598792 |
| 3 | 251 | .050552 | .021954 | .000178195 | .153635 | 4.663281 |
| 4 | 245 | .096206 | .027390 | .000159903 | .015390 | 4.581465 |
| 5 | 248 | .074886 | .026808 | .000459680 | .357869 | 4.616969 |
| 6 | 248 | .075063 | .031310 | .000172276 | .097504 | 4.636905 |
| 7 | 247 | .086523 | .019662 | .000151956 | .011825 | 4.632346 |

Each tail metric uses exactly steps800..1599 and799 within-window differences over4wheels, never pools environments. All full-episode spread values<.08 and each target RMS<.05. Maximum actual float32 target step .020000100135803223 is within the explicitly recorded half-ULP representation bound. No environment reached bias projection saturation. Full four-wheel time means (FAR/FBL/RAR/RBL, rad/s):

| Env | FAR | FBL | RAR | RBL |
| --- | --- | --- | --- | --- |
| 0 | 1.532438 | 1.536187 | 1.564678 | 1.551340 |
| 1 | 1.553327 | 1.543660 | 1.526038 | 1.545496 |
| 2 | 1.532120 | 1.511413 | 1.521071 | 1.534821 |
| 3 | 1.572129 | 1.579821 | 1.557867 | 1.568273 |
| 4 | 1.502457 | 1.513696 | 1.518285 | 1.529847 |
| 5 | 1.563903 | 1.569566 | 1.560417 | 1.542758 |
| 6 | 1.560269 | 1.544696 | 1.576006 | 1.573681 |
| 7 | 1.551077 | 1.535158 | 1.541541 | 1.531415 |

Smooth requested targets do not eliminate every instantaneous physical fluctuation (env5 actual tailΔRMS.357869). This is not a failed frozen gate, but must remain visible during repeats and scale-up. Keep the distinction between actual-wheel time-mean synchronization and perfect instantaneous speed matching.

This concludes the one authorized physical candidate. No parameter change/rerun, no promotion into the formal adapter or AME. The fixed bar has ~45mm exposed height; this is not learned100mm/full-width obstacle crossing or large-obstacle avoidance.

Remaining broader work is unchanged: strict repeated reference gates,1024capacity/behavior, independent AME lifecycle/action bridge, learned small crossing and large-obstacle avoidance. No claim of10000 updates or policy-only success.
