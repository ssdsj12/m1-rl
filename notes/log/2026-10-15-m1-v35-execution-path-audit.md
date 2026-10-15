# v35 actual execution-path audit (2026-10-15)
## Scope and terminal evidence
Isolated candidate only; no production/BC/PPO, PD or safety threshold changes.
v35 native436074/runner436072 absent; exit0 denotes probe completion, not success.
FAILED_DIAGNOSTIC:4 recorded,3 complete failed/locked,0success,full denominator false.
Original archive SHA1b201cc0fd4193f270f9cb2b72a07214d7274a47b9c0506754251dd3b0558099 verified remote and local.
Evidence ledger/scripts/output: .superpowers/sdd/2026-10-15-m1-bounded-crossing-attitude/.
Previous goal turn classified progress (terminal evidence and immutable archive); this turn adds name-mapped execution audit and frozen counterfactual.

## Observed facts (env1, input vs post-step distinguished)
Frame119-138 requested active wheel center Z .09820959 -> .10136078m: only3.15119mm increase. Physical wheel bottom stayed around .05mm.
Frame139 input supportwheel3 Fz29.38263N triggers30N guard; post-step Fz is not this input.
Frame130 full execution fraction1; frame138 fraction.234375. Request alone is not executed body motion.
Actual input roll/pitch frame138=-.140677/.195635rad; selected target=-.1/+.1. Actual attitude overshoots selected target.
Named post-step leg tracking errors max .10043rad(frame119) -> .15331rad(frame138).
Computed and applied effort identical on recorded final physics substeps119-139. This excludes recorded clipping only, not all substep saturation or actuator compliance.
Weak-wheel load feedback offset moved negative: -.00008663 -> -.00250933m; not simply wrong-sign upward correction.

## Frozen architecture test
audit_attitude_path.py ran on server CPU against unchanged v35 runtime, frame130.
Hold measured state, requested position/wheels, captured support heights and yaw fixed.
Compare selected quaternion [.9975019097,-.0499208234,.0499125905,.0025802113] vs captured-yaw level.
execution_targets body_goal difference exactly0 on all4legs.
This isolates DIRECT attitude-to-execution path, NOT whole-transaction load-feedback effect.
Source explains it: crossing support_reference mode substitutes measured-orientation translation, overwrites support world Z with captured-height baseline; desired roll/pitch can influence centered_support_attitude_error/load feedback but is not directly executed.

## Consequence and next work
v35 candidate support prediction uses selected body orientation while direct execution uses different geometry. Selected-quaternion/request audit passing does NOT certify physical realization or tripodal reserves.
Do not describe v35 as physically connected orientation control. Do not lower30N or call .05mm wheel-bottom lift.
Next design must reconcile executable support geometry with candidate support prediction, including bounded actual load/attitude dynamics. Need failing frozen regression for predicted-versus-executed geometry, then isolated actual10cm crossing/recovery proof. A direct full-rotation substitution is NOT yet justified: previous translation/heading protections exist and must be examined before replacement.
No runtime change this turn; goal remains active, actual crossing unproven.

