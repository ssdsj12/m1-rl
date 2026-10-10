# Persistent PPO monitoring and publication retry

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md),
`pure-ppo-learning/required-crossing/persistent-reward`.
Baseline/Candidate: implementation0286e95, documentation1e631b6;
server worktree HEADbb57e7d with the deployed verified source diff.
No production source, training settings, process ownership or reward contract
changed during this monitoring pass.

## Runtime and raw metrics

At2026-10-10 22:18CST, SSH verified PID14800 cmdline/cwd against the authorized
2048env GPU0 run2026-10-10_22-09-27/bb57e7d. Iteration630 completed;
GPU21922/24564MiB. Only this training and TensorBoard14933 were found in the
scoped train/probe/TensorBoard process listing. No traceback, CUDA error,
out-of-memory or fatal-Python match in the current log. No new scheduled PT
yet; existing validated model600 remains available, next save700.

TensorBoard raw scalar API on local16006 confirmed37 samples through637:

- stage1 throughout; >=2cm prelift events and stable landings both0.
- prelift_progress_delta is NOT identically zero: maximum
  0.00022180929954629391, latest637 value0.00018790409376379102.
  These are aggregate normalized reward progress, not measured centimeters or
  a successful lift. Four-decimal console output loses this small signal.
- Latest complete curriculum window:2048 episodes, pass0.53466796875,
  strict attempts3049, strict successes0, course-boundary termination0.4668.
  Recovery-ready fraction remains0 in the latest steps.
- Iteration630 sampled minimum bottom clearance=-0.0346m and collision
  frames595; these do not satisfy positive clearance or strict crossing.

The policy has not established successful crossing. This is an early resumed
window, so no repeated restart, forced action, std modification or live source
hot-patch was performed. Continue watching learning trend and new completed
windows; total reward and pre-wrapper Episode_Reward cannot prove acceptance.

## CPU publication recheck

Remote CPU-only command, OMP_NUM_THREADS=1 and PYTHONPATH=.:Go2Pvcnn:Go2Pvcnn/rsl_rl:

```text
python -m pytest -q Go2Pvcnn/tests/test_m1_crossing_receipts.py \
  Go2Pvcnn/tests/test_m1_persistent_crossing_reward.py \
  Go2Pvcnn/tests/test_m1_required_crossing.py
```

Result:78passed in2.24s, exit0. No Isaac/native/GPU probe was started while
training occupied GPU memory. Local diff --check from5af7a29 toHEAD passed;
changed files were scoped Python/notes, not PT or old untracked watcher scripts.
This focused recheck is not full-repository or physical-capability acceptance.

## GitHub retry

Initial ls-remote succeeded and still returned
5af7a293430a6c6a6d6544cc9d76e4f4855027f2 for m1-10-10.
Authorized normal non-force push of localHEAD1e631b6 failed with
`Recv failure: Connection was reset`; post-attempt ls-remote timed out on443.
Publication is therefore still unconfirmed. No persistent Git or network
configuration was changed; a per-command LFS locksverify=false was used as
before. Do not claim the implementation is online until a remote ref read
confirms it. Remote training remains independent of this upload problem.

## Terminal-obstacle-space read-only audit

Independent code audit, checked against the current layout, boundary, FK and
strict-event sources, refines the existing open issue. Tile centers are NOT
the spawn positions shifted back2m. Root must stay atx<=7.25m in the16m tile;
wheel centers atx<=7.830792m. Horizontal wheel envelope r=.119208m.
For a locked +X crossing, the last rear-wheel center must reach
`obstacle_x+.05+r+.04`. At horizontal nominal585mm stance its bodyX offset
is-.3295m (including .272+.0575 mounts, not only .272).

| Stage | Last obstacle centerX | Required rear wheelX | Nominal rootX | Root margin |
| --- | --- | --- | --- | --- |
| 2 | 6.3 | 6.509208 | 6.838708 | +.411292 |
| 3 | 7.2 | 7.409208 | 7.738708 | -.488708 |

This confirms a stage3 nominal straight-recovery layout conflict, NOT that
all possible poses/paths are impossible. Strict landing can occur in a
non-nominal pose and five subsequent recovery frames do not repeat far_now.
Stage2 is not proved blocked. Probe placements last_far_edge+1.1 produced
root7.45/8.35 and directly exceeded the boundary in both stages; that alone
was not a crossing impossibility proof.

Sources: m1_mixed_course.py:104,128; semantic_course.py:749;
m1_kinematics.py:31,119; m1_ame_contract.py:26;
m1_dynamic_crossing.py:160; m1_strict_crossing.py:222,231,237;
ame_env_wrapper.py:1309,1324. No source was modified.

Candidate only: shift stage3's whole row back.6m, retaining8 blocks/.9m pitch,
centers.3..6.6. This leaves nominal root margin.111292m before accounting for
recovery motion. A robust design must also budget >=5 recovery frames, actual
speed, wheel/body pose and margin. Do not relax boundaries. Actual stage2/3
last-block FAR/RAR landing/receipt trajectories and timeout margin still need
native verification at a safe stopped-training boundary. Current stage1 is
unaffected; no terrain hot-patch or training interruption was made.

## Follow-up

Continue current process, verify model700 when saved, and observe actual single
wheel lift/clearance/stable recovery before any success claim. Keep the existing
terminal-obstacle-space follow-up before stage3 whole-course acceptance.
User notification remains quiet for the unchanged learning/publication state.
