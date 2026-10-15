# IK active-knee tangent candidate

## Scope and authority

Continue actual10cm first-obstacle teacher crossing and recovery; no production training. User explicitly chose direct execution/self-permit, so no repeated approval/handoff prompt. Preserve all historical evidence and safety criteria. This is a local solver direction correction, not a new controller or looser objective.

## Evidence

v26 actualenv1–3 locked137 after passing old127 failure, no physical lift. LR execution residual about.1085mm at preservedknee.10rad. Frozen repeated solver chunks stagnate. Same-target32-budget diagnostic using a reduced ABAD/HIP Jacobian when the knee proposal crosses the boundary succeeds onframes133/134/137, LRresidual.06067/.06156/.06428mm; maxqdelta<=.001098rad. Normal118/122 cases do not select tangentcandidate. Frozen CPU evidence does not prove dynamics or complete crossing.

## Alternatives

Recommend constrained tangent candidate: when a finite raw kneeproposal crosses the existing branch halfspace, hold knee at the legal boundary and solve the remaining Cartesian error with ABAD/HIP Jacobian. Compare its realFK residual against the projected fullDLS candidate; retain the better legal strictlyimproving result. This avoids imposing extra physical targets.

Increasing32 budget fails frozen repeated-solve check. Relaxing.1mm execution tolerance or moving supporttarget would change requirements rather than fix a proven legal same-target solution; neither is selected.

## Algorithm and invariants

Inside each existingiteration, compute fullJ/fullDLS once. Save preprojection finite mask. Compute ordinary projectedcandidate unchanged. For boundarycrossing legs only, delta_knee=projected_knee-current_knee; remaining_error=error-J_knee*delta_knee. Reduced3x2 DLS uses same.05 damping and.25 component clamp. Candidate starts from currentq, adds reducedABAD/HIPstep and uses projectedknee. Preserve originalcandidatefiniteness as eligibility for BOTH paths; nonfinite values cannot be sanitized into acceptance.

Both candidates require unchanged finite/joint/branch/nearstraight checks and strict actualFK residual decrease. Tangent wins only if better than the normal admissiblecandidate; ties keepnormal. Unaffectedlegs remainnormal. Maximum32iterations, same workspace/seed/finalvalidity, outer.05rad/controlstep slew and encodedexecutionaudit. No finalresult clipping. Public API unchanged, teacherfingerprintv27.

## Tests and physical acceptance

Exact provenance fixture fromv26 frames133/134/137 (plus normal118/122), float32/64, fourleg positive/negativebranch and configured.1/.3 boundaries. Verify invalidseed/nonfinite/unreachable remaininvalid, tangentnonfinite cannot replacelegalnormal, monotonicFKresidual, componentbounds, no new budget. Existing full759 plus new regressions required. One fresh finalreview; fixCritical/Important in one RED/GREEN pass, no reviewloop.

Only afterv26terminalaudit/archive and candidateSHA/preflight: one uniquelynamed4env10cm native, no concurrenttrain/native, kernel flock. Read all4denominatoraudits/rawsameenvattempt/video. Physical success requires actual lift, passage and recovery; frozenvalidity is not success. Failures drive evidence-based next action, not relaxation.

Self-review: singlemodulebehavior/fingerprint, no target/controlconfiguration changes. No pending user choice, no ambiguous tolerance. Existingworktree/manualledger/sourcecopies preserved; no gitidentity modification.
