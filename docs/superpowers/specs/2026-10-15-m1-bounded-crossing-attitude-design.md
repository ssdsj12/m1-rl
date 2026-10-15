# Bounded crossing attitude — v35 design

## Goal and authority
Continue actual10cm first-obstacle crossing and post-cross restoration, not isolated unloaded leg motion. Human authorized modest crossing tilt, dynamic support/IK redesign and direct execution without repeated approval. No production/BC/PPO, PT deletion, global configuration or Git identity/commit/push changes. Existing linked worktree retained.

## Evidence and architectural decision
v34 terminal0/FAILED_DIAGNOSTIC,0success; archived SHAba2001283bbc209910d865bdeef8280685ecef290179ffceb2f6d377ce3168db. Atframe130 all126 nominal IK candidates solve, but none has predicted weakest tripod>30N. Level-only best29.26377N. Static measured-orientation variant gives42.53421N but initially still sends a level request: `_step_row` retained old goal quaternion, then tracking-gated interpolation can keep accepted level attitude even after goal replacement.

Frozen diagnostic with fixed roll=-.1,pitch=+.1 at captured yaw, selected quaternion propagated through dynamic goal and request, yields6eligible candidates, best46.75379N, full transactionvalid, executionfraction1, max joint target change.03165758rad<.05. Output `/tmp/m1-v34-fixed-tilt-consistent130.jsonl`, SHA903ea5e3192ce229c9edbff6f5ceabf6d4f95a8b62136dc818f55217c1c08695. This is a single CPU frozen frame, not a trajectory, GPU equivalence or actual physicalsuccess. The prototype first had an indentation error; only corrected run is valid evidence.

Alternatives: (A) keep mandatorylevel: known candidate exhaustion; (B) snap goal to current measuredtilt everyframe: rejected because it can chase a fall and erase attitudeerror; (C) bounded deterministic orientation search, selected orientation actually requested, existing execution transaction limits motion. ChooseC. No30N threshold reduction or body envelope expansion.

## Candidate geometry
Optional isolated `bounded_crossing_attitude` mode, false bydefault for archived compatibility; launch newnative explicitly true. Mode requires slow_rolling+load_feedback and applies only dynamic LIFT/PASS. BALANCE reference and RESTORE goal remain original.

Extend `choose_support_pose` with explicit opt-in bounded attitude candidates. Heading remains captured yaw. Nine fixed body-frame roll/pitch pairs: level first, then remaining Cartesian pairs from[-.1,0,.1]rad in deterministic lexical order. Nettilt<=acos(cos(.1)^2)<.15rad, verify with bodyup/worldup, not only component angles. No measuredquat substitution, no step-to-step drift of yaw/tilt bounds.

For each orientation retain original125 positions in the4/6/8cm heading envelope and original nominal root floor; include accepted reference once only if it satisfies the same position envelope, tiltbound and heading contract. Newpool125*9+1=1126, legacy126. Make count/budget explicit in mode-specific contract; do not leave misleading126 metadata for newmode.

All candidates retain current four-leg IK/branch/knee safety, anchor and measured supporttriangle margins, both tripod predictions>30N. In the new bounded mode, saturate weakest-load ranking at45N then rank support-knee reserve; legacy ranking remains unchanged (it did not saturate). Normalized motioncost breaks ties and must include quaternion angular distance to accepted so level/nearer attitude wins when other benefits tie. Stable index resolves exactties. If no candidate satisfies all constraints, fail transaction; do not reinterpret predictedload as measured support.

## End-to-end reference contract
Dynamic goal uses full selected BodyPose, including quaternion. In opt-in dynamic mode request uses selected bounded quaternion rather than the old tracking-gated levelinterpolation. This is a desired pose, never direct articulation or action takeover: original feedback/backtracking, final encode and .05rad@20ms jointtarget bound remain authoritative and can reject/rollback. Preserve requested/attempted/accepted distinction.

Existing actualsupport, current and selected tripodreserve, collision, physicalfailure, rate and tracking gates remain. The selection's orientation must be used by its predictedCOM and the actual request; no gain in predictedreserve from an orientation omitted downstream. Execution supportheight/attitude feedback uses that same command and its owned history, no recapture to measuredtilt and no silent historyreset. Failure changes no committed reference/anchor/integral beyond existing explicitfailure accounting.

RESTORE continues bounded return to original captured heading/level/nominal joint/root pose and original stable recovery receipt. Do not retain crossingtilt as a new recoverybaseline. No change success/overlap/collision/first-obstacle denominator or0.3s complete recoverycontract.

## Independent evidence and tests
Fingerprint v35 plus configflag and truecandidatecount bind records. Raw-history audit must verify dynamic selected/request quaternion agreement (up to quaternion sign), fixed yaw/allowed boundedorientation, retained supports and unchanged firstLIFT activeXY rules; freeze only wheelprogress, not falsely certify an unused orientation. Existing replay alone is insufficient: add shared producer/replay wrongrequest quaternion mutationtest.

TDD: legacy exactbehavior, nineorientationpool/bounds/quaternion sign, all4 activelegs, nofeasiblefailure, invalid shape/NaN/typeflag; frozen130 level fails while tiltedchoice passes originalconstraints; dynamic selectedquat reaches requested pose; finalencode/IK rejection atomic; duplicate/reset rowisolation; RESTORE originallevel; CPU/GPU audit and immutable originaltrace. Test actual encoded target rate and residual, not onlyvalid flags.

Review full relevant985+new tests, barepytest limitations honestly, one independent final reviewer. Deploy only isolatedcandidate after currentnative absent, GPUidle and SHAmanifest; unique newprefix underkernel flock. Read completevideo/trace/result/audit and archive. Physical success requires actual lift/pass/landing/recovery, not staticchosen pose or greenCPU.

## Self-review and next action
Scope is one coupled reference-selection/execution feature. Clarification already supplied by user: slighttilt acceptable whilecrossing, recoverafter. No visualdesign choice or approvalrepetition needed underdirect-run instruction. Separate newpurecandidate tests, teacherintegration, independentaudit and finalnative tasks in implementationplan. Need measure runtimecost of1126pool; do not reduce environments or silently shrink candidate requirements to satisfy tests. Candidatecode andproduction remainv34 until reviewed implementation; goalnotcomplete.
