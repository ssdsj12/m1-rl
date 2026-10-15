# Backtrack Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline; one final fresh-context reviewer.

**Goal:** Use safe available joint motion to lift during actual slow 10cm crossing.

**Architecture:** Eight coarse candidates followed by four per-row validated midpoint trials, retaining last safe result. Explicit existing execution fraction drives every commit and audit.

**Tech Stack:** torch, pytest, isolated Isaac probe.

Spec: docs/superpowers/specs/2026-10-15-m1-backtrack-refinement-design.md. User direct execution authority; no production training or deletion. Existing linked worktree reused; missing Git identity means SHA evidence without invented commits.

### Task 1: Bounded safe refinement

Files: Go2Pvcnn/ame_baseline/m1_teacher_pose.py; Go2Pvcnn/tests/test_m1_teacher_backtrack_refinement.py.

- [ ] RED real IK: nominal fixture q, requested active wheel z+=.006m, callback valid only output_x<=.00095 with proposed output_x=.001. Expect coarse_index1 but fraction .9375, output_x .0009375, all dq<=.05. Run CPU pytest newfile; old returns .5, expected FAIL.
- [ ] Implement coarse loop plus4 refinements, beta[B], broadcast beta[:,None] for root/u/quaternion and [:,None,None] wheels. For refinements mask `chosen & index>0 & execution_mode!=0`; lower from saved targetfraction, upper2*lower. Validate unchanged gates; merge only valid eligible rows. Keep coarse_index. Return frozen failure diagnostics for failed rows.
  Algorithm: `mid=(lo+hi)/2; valid=all_existing_gates(mid); use=eligible & valid; lo=where(use,mid,lo); hi=where(eligible & ~valid,mid,hi)`.
- [ ] Add float32/64, mixed batch, fullstep/no feasible, nonmonotoniccallback all accepted points checked, boundedcallcount<=12; run newfile and pose/execution/feedbacktransaction tests. Expected all PASS.

### Task 2: Actual fraction end-to-end

Files: Go2Pvcnn/ame_baseline/m1_reference_teacher.py; Go2Pvcnn/scripts/probe_m1_teacher.py; Go2Pvcnn/tests/test_m1_teacher_load_feedback_transaction.py; new refinement tests.

- [ ] Commit beta `float(solved.execution_target.fraction[0])` when execution_target exists and valid, else prior2**(-index) or0. Both load and height/heave use it. Fingerprint v23.
- [ ] Independent load/height/heave auditor uses `d['execution_fraction']` for accepted execution contexts,0 for rejected. Preserve replay binding and add tamperfraction test. Existing support increment test must assert `old+fraction*(off-old)` (test callback stateful cannot define fixed beta). All current tolerances unchanged.
- [ ] Run prior660 suite plus newfile onCPU, log fullresults. Run frozenv22 replay using newsource separately; compare solvedZ and boundedq, do not claim native result or re-audit old fingerprint as new.

### Task 3: Review and physical evidence

- [ ] Final fresh reviewer checks batch atomics/fraction consistency/nonmonotonic/rollback/antiwindup/callbound; fix Important with RED/GREEN, fullsuite.
- [ ] SHA precisely deployed runtime and audit; confirm no training/native andGPU1MiB; unique v23 directory and kernel flock;4envseed101first10cm. Existing v22 archive never overwritten.
- [ ] Inspect exit, all JSONL and videos; archive with independent matching local/remoteSHA; update notes. Only complete physical crossing+recovery meets goal.

Review Focus: failed rows cannot be replaced during other-row refinement; all enabled state commits share realfraction, no fallback2**index; neither midpoint acceptance nor diagnostic nominal validity proves physical lift. Nonmonotonic validator must never be bypassed.
