# Bounded Crossing Attitude Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Inline implementation, one final fresh reviewer, no repeated user approval.

**Goal:** Make bounded crossing attitude participate consistently in support search and actual teacher requests, then verify actual10cm crossing/recovery.
**Architecture:** Opt-in nine-angle candidate pool, full selected-pose request, independent raw evidence, original transaction and restoration.
**Tech Stack:** Python/PyTorch/pytest/IsaacLab.
**Spec:** ../specs/2026-10-15-m1-bounded-crossing-attitude-design.md

## Global constraints and interfaces
W existing codex/m1-dual-support-recovery; no production/BC/PPO or Git commits/push/identity changes, no deletion of evidence. Preserve v34 archive. CPUoverlay `/tmp/m1-v30-audit-fixed`, candidate remainsv34 until finalgreen. Runtime paths below relative to Go2Pvcnn. SSH key/proxy/host unchanged. Test command prefix:
`cd /tmp/m1-v30-audit-fixed && PYTHONPATH=.:/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn /opt/conda/envs/env_issacsim/bin/python -m pytest -q`
Record task baselineSHAs instead of commits. Never overwrite a live testoverlay/candidate. Explicitly bounded1126 search cost, no environmentcount reduction.

### Task1 — Pure candidate pool
Files: ame_baseline/m1_teacher_pose.py; tests/test_m1_teacher_bounded_attitude.py; tests/fixtures/m1_v34_attitude130.json.
Produces optional `choose_support_pose(..., bounded_attitude=False)` and `_bounded_attitude_quaternions(yaw)` [B,9,4]. Default remains exactlegacy126; mode1126.
- [ ] Extract original dynamic pre/input frame130 with SHAprovenance into JSONfixture; no rewritten source trace.
- [ ] Write RED tests: helper nineunique/level-first/unit/fixedyaw/nettilt<.15, candidatepool1126, strictboolflag, unchangedlegacy, out-of-bound acceptedorientation excluded, all4activelegs and NaNfailclosed. Frozen130 asserts legacyinvalid and opt-in valid with both predictedloads>30N, realIK.
```python
assert choose_support_pose(*args, **kw).valid.item() is False
tilted=choose_support_pose(*args, **kw, bounded_attitude=True)
assert tilted.valid.item()
assert tilted.reference.body.quat_w[0,1:3].abs().max()>0
```
- [ ] Run newfile; Expected missingfeature RED, not importerror.
- [ ] Implement fixed ninepair grid, repeat125 positions perorientation plus accepted once; replace126-specific tensor sizes inside search with computedsize. Tilt/yaw-check accepted candidate, original envelopes and safety remain. Add normalized quaternion distance cost only for opt-in mode, use original rankload/knee/tieorder.
```python
orientations=_bounded_attitude_quaternions(yaw)
grid=grid.repeat(9,1)
size=grid.shape[0]+1
quats=torch.cat((orientations.repeat_interleave(125,dim=1), accepted.quat_w[:,None]),1)
```
- [ ] Run newfile+test_m1_teacher_pose.py+test_m1_teacher_tripod_selection.py+test_m1_teacher_support_knee_reserve.py. Expected allpass; recordruntimeSHA. No native.

### Task2 — Teacher request and recovery integration
Files: ame_baseline/m1_reference_teacher.py; scripts/probe_m1_teacher.py; tests/test_m1_teacher_bounded_attitude_transaction.py.
Consumes Task1 `bounded_attitude`; produces TeacherConfig bool `bounded_crossing_attitude=False`, property dynamic_candidate_limit1126/126, fingerprintv35 and CLI `--bounded-crossing-attitude`. Requires slowrolling+loadfeedback. Keep existing base candidate_limit126 metadata explicitly basepool; add true dynamiclimit fingerprint/contract.
- [ ] RED frozen130: opt-in config accepted; selectedquat equals requestedquat, nonlevel, real fulltransactionvalid with encoded maxdq<=.05 and residual<=.0001. Tests reject bool-as-number flag and impossiblemode, verify legacyflagfalse, retry/duplicate/rowreset/encodefailure atomicity, RESTORE originallevel baseline.
- [ ] Forward opt-in only to dynamicLIFT/PASS search; BALANCE unchanged. Replace dynamicgoal with complete choice.body. In opt-in dynamic branch use goal quaternion in requested instead of old tracking-gated interpolation; all feedback/backtracking/finalencode and currentphysical/selectedreserve constraints remain.
```python
goal=PoseReference(choice.reference.body,preserved_wheels) if cfg.bounded_crossing_attitude else legacy_goal
if dynamic and cfg.bounded_crossing_attitude:
    quat=quat_goal
```
- [ ] CLI opt-in flows through configfactory once, rejects use outside slowrolling/loadfeedback; serializedcfg/fingerprint roundtrip tests. Do not enable existingarchived probes by stealth.
- [ ] Run transaction/newpure plus original dynamic/load/height/xy/restore suites. Expected allpass; recordSHA. No native before Task3.

### Task3 — Independent orientation evidence and integration review
Files: scripts/probe_m1_teacher.py; tests/test_m1_teacher_bounded_attitude_evidence.py.
Consumes rawpre/input/post and existing feedback_context/teacherdiagnostics. Produces independent orientation errors integrated with outerverification.
- [ ] RED tests: validquat sign-equivalence, wrongcapturedyaw, overtilt, selected/request mismatch, sharedproducer/replay wrongrequest withcorrectselection, wrong1126count, staleconfig, restoredposebaseline. Existing XYhistory audit stays active.
- [ ] Independently reconstruct allowed fixedorientation set from capturedyaw and verify dynamic requestedquat matches selected fullpose; validate predictedCOM using same orientation and rawgeometry. Bind actual command/attempted/accepted through existing transaction checks, not claim request==actual movement. Freeze affects wheelprogress only. Missing owned evidence rejects rather than skips.
```python
same_rotation=abs(sum(a*b for a,b in zip(selected_q,requested_q)))
assert abs(same_rotation-1.)<=2e-6
```
- [ ] Run prior985+allnewtests with durable log/exit; run barepytest collection and retain known missingdependency names. Expected relevantgreen; no fullsuiteclaim if bareerrors remain.
- [ ] Single fresh finalreview focuses rawquat/source/actualrequest consistency, acceptedcandidate bound bypass, batchisolation, RESTORE no newtiltbaseline, payloadbudget/fingerprint. Fix Important with newRED→GREEN and whole relevant suite, no duplicate reviewers.

### Task4 — Isolated native
- [ ] Verify v34archiveSHA and no train/native/testprocess, GPUidle; deploy only reviewedruntime with SHAmanifest.
- [ ] Launch unique evidence-first-obstacle-bounded-attitude-v1 under existingkernel flock with `--slow-rolling --load-feedback --bounded-crossing-attitude --teacher-scope first-obstacle --diagnostic-steps 1000`, actual10cm fourenv; keep samecamera/evidencepathsettings.
- [ ] Inspect samePID untilterminal; trace/video/actualwheelbottom/supportloads/collision/overlap/recovery/independentaudit. Exit0 notsuccess. Archive originals with local/remotesameSHA; no successfulgoal unless complete actualpass+recovery evidence.

## Self-review
Task1 boolean keyword consumed by Task2; Task2 serializedflag consumed by Task3; mode-specific limit property avoids misleading legacybasebudget. Tests explicitly address reference/execution mismatch seen in frozenexperiment. Recovery and safety remain unchanged; review tests must cover no accidentalopt-in inlegacy. No unresolved design choice requires another userapproval underdirect-run authorization.
