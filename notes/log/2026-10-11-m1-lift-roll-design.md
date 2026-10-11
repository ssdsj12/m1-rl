# M1 alternating lift-and-roll design confirmation

## Purpose / scope

User confirmed the corrected mechanics: one wheel lifted, other three supporting
and rolling, front then rear on the same obstacle, then switch side. Parent:
[T306](../todo/T306-m1-ame-long-train-stability.md), child
`pure-ppo-learning/density-exposure/lift-roll-layout`.
[Written design](../../docs/superpowers/specs/2026-10-11-m1-alternating-lift-roll-design.md).
The earlier connected transverse-barrier illustration is superseded, not deployed.

## Read-only evidence

2026-10-11 03:37UTC: SSH to current host a21472797434572800304964 verified
PID948 exact cwd and2048env/cuda0/keep_std/model1000-resume command; TB1081
still points10-56-34. GPU021862MiB. Current run now contains model_1100.pt;
existence alone is not CPU checkpoint validation. Subsequent stdout read reached
iteration1160. No signal was sent, source deployed, training restarted or probe run.
Latest sampled log has stable_landings0 and strict success0; no mastery claim.

Source reading confirmed progressive terrain still4/6/8 and dynamic tracker
checks all four wheel XY envelopes against all landing obstacles. Therefore
blind background filling could permanently invalidate landing_free, even when
the lifted wheel itself clears its target. This is an explicit design/test gate.

## Result / follow-up / refs

Design records the already approved behavior, constrained terrain scope,
anti-bypass search limitations, unchanged strict thresholds, checkpoint-safe
deployment and retained current-policy continuation. No production contract has
changed. Written-spec review precedes implementation planning under brainstorming.
No new behavioral approval is implied by the current healthy training process.
Baseline/Candidate Work Ref:260b3a1; Last Feature/Verified Feature5a366ff unchanged.
Key files:m1_mixed_course.py,m1_dynamic_crossing.py,m1_required_crossing.py,
written spec above. Next: review the written constraints, then TDD implementation.
