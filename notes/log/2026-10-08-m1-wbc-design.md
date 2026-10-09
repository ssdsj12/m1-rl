# 2026-10-08 M1 dynamic WBC design review

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md).
Stage: contact-controller architecture, documentation only.
Baseline Ref: `6db197a`. Candidate Ref: this documentation commit.
Key Files: [WBC design](../../docs/superpowers/specs/2026-10-08-m1-dynamic-wbc-design.md).

User approved dynamic whole-body control, stable crossing before retraining.
Fresh SSH check: clean independent worktree at baseline; GPU7 compute PID99388
is exact own amp/python sleep.py, 10624MiB. No process stopped or job launched.
Read current support solver and Jacobian utility: vertical-only gravity balance,
no tangential force or acceleration; this confirms architecture boundary.
Prior handoff physical evidence remains failed at ROLL5/21.16N, not rerun here.

Written design specifies complete dynamics, rolling-contact geometry, one owner
of all16 actuator torques, bounded recovery, unchanged safety limits and full
crossing/avoidance/policy-only gates. Self-review checks actuator conflict,
normal-only sensing, rolling kinematics and false-success substitutions.
Verification for this pass: git diff whitespace and linked file existence.
No new controller tests or physical success claimed. Await written-spec review,
then create implementation plan. Human/AI runtime contracts remain unchanged.
