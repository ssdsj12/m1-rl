# Independent active lift intent, atomic reference commit

## Authority and objective

User authorizes direct scoped correction and isolated native tests, without repeated approvals. Preserve actual 10 cm crossing plus recovery as success; no production training. This design repairs one demonstrated coupling, not a claim that yaw drift or complete crossing is solved. Existing linked worktree/evidence remain intact; no Git identity changes or forced commits.

## Evidence

v29 env1 frame125 requests wheel-center Z .097853608m. Shared physical-reference beta .01416015625 reduces it to .097710997m before the independent execution solver sees it. CPU full-active-request counterfactual reaches .097815275m under unchanged execution gates; baseline .097674042m. A separate solve of the full physical active target is valid under original nominal IK tolerance. Frames120/122/125/128 show the same feasibility;129+ remain frozen by yaw readiness.134 remains invalid on support execution residual. These are frozen CPU comparisons, not dynamic success or an audited replacement transaction.

## Alternatives

1. Increase lift rate: rejected, because the shared beta still attenuates intent and rate increases lack causal evidence.
2. Replace execution goal only: rejected, because committed physical reference would disagree with commanded intent and next-frame progress.
3. Separate active intent interpolation from support interpolation, validate and commit atomically: selected. Retains existing support transaction as a safe baseline and isolates the proven coupling.

## Transaction

Only valid crossing mode1 rows are eligible; preparation, legacy and restore retain exact behavior. First retain current accepted support transaction, including its body pose, support wheel reference positions, feedback output/integral, support command joints, support height/heave/load history and support beta.

Search active physical reference between that baseline active position and original requested active position, bounded to the original request. No extrapolation, increased lift rate or new measured state. For each candidate, build a matching physical and command reference. Re-run original nominal IK with original branch/limits. Build active execution target from measured body transform and the candidate world position. Assemble active joint solution with exact baseline support joint commands and require unchanged execution residual, branch, joint limits, slew, finite checks and caller validator. Rejected candidates leave baseline completely unchanged. Never repair an already invalid support transaction through active-only changes.

Use bounded coarse/refinement search, with explicit active intent fraction separate from support beta and existing active execution fraction. The physical active reference, command reference, nominal result, execution geometry/result and intent fraction must be selected as one unit. If execution cannot reach all candidate intent, the existing bounded execution-progress semantics remain explicit; do not label actual lift from reference acceptance.

## Evidence and independent verification

Add an explicit active intent fraction to diagnostics and fingerprint. Independent verification reconstructs active world reference from accepted-before/requested and that fraction, while body/support references use support beta. Check command world target agrees with selected physical intent; then independently reconstruct measured-frame execution interpolation. Tampering with any fraction or world target must fail. Do not teach the verifier to accept arbitrary producer output.

## Validation

RED fixture reproduces v29 frame125 loss of feasible intent; GREEN must improve accepted intent and preserve exact support commands/history and original safety gates. Cover mixed batches, invalid rows, mode0/restore, zero active request, nonfinite inputs, branch/slew/residual rejection and rollback. Real frames129/133 remain unchanged when requested equals accepted;134 must stay invalid. Full relevant CPU regression and one final independent review precede deployment. Native deployment only after current381180 exits and immutable v29 archive is verified. New isolated run has a unique prefix and lock; no concurrent native or production training.

## Remaining physical problem

Yaw readiness freezes at frame129 (error .158689rad>.15) despite valid support/COM. Differential commands saturate but measured wheel speeds do not track. Current force buffer XY is zero, so it cannot prove yaw torque cause. Do not relax yaw gate or claim this intent repair fixes yaw; evaluate the next native trajectory and use its evidence for further support/heading work.

## Self-review

Scope is limited to demonstrated intent/commit coupling. Success criterion unchanged. No approval prompt required under explicit direct-execution authority. Implementation plan must specify dataclass compatibility, audit formulas and exact rollback tests before runtime edits.
