# M1 wheel equalizer single-variable diagnostic A/B

Status: proposed, awaiting user review. Parent T306.6h.6.

The first full reference run completed8x1600 with native0, but only4/8passed strict wheel mean speed spread≤.08rad/s. All eight physically completed the required FAR/RAR narrow-bar crossing. Offline data proves a saturated period-two flat wheel command: FAR target alternates0/1rad/s and measured speed approximately.13/1.00. Replaying the reference feedback equation from previous-step speed reproduces applied targets within1.3e-7rad/s.

## Alternatives

1. Recommended: one isolated diagnostic config override, `wave_wheel_equalize_gain=0.0` instead of3.0. This removes only the extra outer equalization feedback; implicit actuator damping30/stiffness0 remains active. Retain rear feedforward.4, sequential controller, IK, geometry, randomness, metric windows and every acceptance threshold. It tests whether outer feedback causes the observed command oscillation; it is not predeclared a repair.
2. Add filtered/PI synchronization immediately. This changes state, reset and controller stability contracts before identifying the baseline plant contribution; defer until A/B evidence.
3. Increase the speed-spread threshold or average a selected window. Reject: that changes acceptance rather than correcting behavior.

## Scope and implementation boundary

Create an isolated copy from the frozen formal reference adapter, not an edit to `/home/hexinkun/m1`, SDK or AME. Record the single new controller override and candidate label in configuration and provenance. Default formal adapter stays unchanged. A CPU regression must reject any extra controller/scene/threshold change and verify .0 override, then all existing tests pass. Review the exact diff before one8x1600GPU7 run.

No automatic retries, sweeps, resume, threshold changes or process signals. GPU7 only; stop the known reservation only if needed after exact PID identity verification and restore it only once noGPU7compute task remains. Current8-env fits without stopping it.

## Evaluation

Keep strict report unchanged, including8/8requirement and first-episode denominator. Compare full-run mean spread, after-wave wheel/action variance, alternating/saturated target fraction, contact/clearance/landing/tilt/height, progression and exact native completion. If synchronization improves but another gate degrades, report a failed diagnostic, not a successful fix. If waveform persists, return to diagnosis rather than adding another unexplained gain. This run cannot establish policy-only capability or large-obstacle avoidance.

## User objective boundary

Single-process10000updates, learned crossing of harder/full-width obstacles and true large-obstacle avoidance remain separate unfinished stages. The current experiment neither starts long training nor changes those evaluation definitions.
