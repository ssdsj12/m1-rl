# Active execution progress implementation plan

> **For agentic workers:** use superpowers:executing-plans inline; final fresh review required.

**Goal:** remove support-step throttling of the active wheel without bypassing whole-body gates.

**Architecture:** retain the valid baseline support transaction, independently improve only active IK interpolation, atomically validate assembled action, record both fractions.

**Tech Stack:** Python/PyTorch, existing pure CPU teacher tests and isolated Isaac probe.

Spec: ../specs/2026-10-15-m1-active-execution-progress-design.md

## Task1: regression fixture and RED

- [ ] Export exact v27 frames122/137/150 dynamic input/prestate plus config and original traceSHA to Go2Pvcnn/tests/fixtures/m1_v27_active_progress.json. Keep raw evidence unmodified.
- [ ] Add Go2Pvcnn/tests/test_m1_teacher_active_progress.py: reconstruct ReferenceTeacher from config and _dynamic_unpack snapshot, call _step_row, assert valid and `execution_active_fraction > execution_fraction` using fallback scalar for baseline. Run pytest expecting3assertionfailures, not collection errors.
- [ ] Add tests for preserved support output/history and final encoded residual/slew; exact existing baseline outputs are fixture oracle. Preserve mode0/2 and invalid-baseline behavior.

## Task2: minimal helper/integration

- [ ] Add pure active search helper in Go2Pvcnn/ame_baseline/m1_teacher_active_progress.py. Inputs:existing ExecutionTarget/IKResult, qseed/branch,lastapplied,active,dt,cfg and assembled-candidate validator. Return improved target/IK or original. Coarse8/refine4, merge only active leg fields, no clipping outputs.
- [ ] Extend ExecutionTarget with explicit active_fraction initialized to scalar; integrate helper after original valid selection in m1_teacher_pose.py. Preserve support outputs and old history scalar. Add fingerprintv28 and execution_active_fraction diagnostic in m1_reference_teacher.py.
- [ ] Update probe_m1_teacher.py independent execution geometry verification: use activefraction only at activewheel mode1, require scalar<=active<=1; all other modes equality. Producer replay must authenticate both. Write tamper RED tests before verifier changes.
- [ ] Run targeted tests then all previous772+new tests; inspect failures rather than weakening gates.

## Task3: review and actual crossing

- [ ] Fresh finalreview exact baselinecopies/spec/ledger/tests; one C/I repair pass with RED/GREEN, retain minorfindings.
- [ ] Confirm v27 terminal and archive source/tests/rawvideo/JSONL/log/exit with localremoteSHA before candidate deployment.
- [ ] Copy only reviewed candidate files, verify hashes, check no native/trainingGPU job, acquire existingflock; launch unique v28 first-obstacle4env10cm test once.
- [ ] Inspect raw lift/support/passage/recovery and video; archive result and update notes/T306. Do not call physical success on tests or partiallift alone.

Ruling: no commits until repository identity exists; do not set globalidentity. Preserve baselinecopies/ledgers, no cleanup. Direct userauthorization replaces repetitive approval prompts. Existing linkedworktree reused.
