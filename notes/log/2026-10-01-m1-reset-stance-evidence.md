# 2026-10-01 M1 stance encoding and episode re-arm

## Scope / refs

T306 children: stance-target encoding and auto-reset teacher lifecycle.
Baseline/candidate: HEAD 3cd59cc plus existing uncommitted worktree; no commit promotion.
Files: `Go2Pvcnn/ame_baseline/m1_mpc_teacher.py`, `ame_env_wrapper.py`,
tests `test_m1_teacher_stance_hold.py`, `test_m1_teacher_episode_reset.py`.

## CPU evidence

Actual teacher -> m1_action_targets pipeline mapped a nonselected hip measured
at default+0.20 rad back to default. A zero action is NOT a measured-pose hold.
RED decoded -0.5727 versus measured -0.3727. Minimal fix encodes measured
stance deltas; decoded stance error becomes zero, swing slew remains 0.12 rad.
Old test counted nonzero action columns as leg movement, which was incorrect;
updated it to check decoded named-joint target differences.
This proves an action-contract bug, not the sole physical cause of falling.

Actual wrapper post-step block replay over three rows (done/live/done) failed:
obstacle_event_seen and initial-fallback/short-trigger latches survived done.
Wrapper.reset clears these but Isaac auto-reset does not call wrapper.reset.
Fix clears only done rows including candidate_prev and clearance counters.
RED -> GREEN; 45 focused CPU tests passed in 3.59s.

## Physical experiments (diagnostics, no acceptance)

All GPU7 via placeholder wrapper, amp, headless. No display-service changes.
Source checkpoint for resumed trials: 2026-09-30_07-07-12/3cd59cc/model_602.pt.

| Run/log | Inputs | Observation |
| --- | --- | --- |
| 05-36-12 / m1_long_train_20261001 | 1024 env, intended 10000 | stopped at iteration 615; bad orientation ~0.81, crossing0 |
| 05-49-26 / m1_teacher_hold_smoke | 64 env, 30 updates, stance fix | completed632; bad orientation .676, crossing0 |
| 05-54-26 / m1_lr2e6_smoke | same, LR2e-6 | failed behavior; at628 bad orientation .629 |
| m1_lr0_smoke | 64 env,10 updates,LR0 | bad orientation .328, base contact .672 |
| m1_warmup_smoke | same, speed .05-.15 | bad orientation .352, base contact .648 |
| m1_no_obstacle_smoke | LR0, stage none | bad orientation .346, teacher0; stage also changes reset/commands, not a pure obstacle-only A/B |
| m1_stable_checkpoint_smoke | prior 2026-09-20 model600,LR0,stage none | bad orientation .996 at609; historical stability did not transfer |
| 06-14-25 / m1_fresh_warmup_smoke | fresh,64env,30updates,low noise | terminal bad orientation0/base contact0/collision0,crossing0; model29 exists |
| 06-19-16 / m1_warmup_200 | model29,256env,planned200 | interrupted after persistent teacher0 post-reset and collision~-.95; model100 saved |

Two attempts used a mistaken checkpoint path missing m1_rl and failed before
learning; reruns used the verified path. Do not count those as behavior tests.
No causal claim that LR or checkpoint alone explains failure: trials change
duration/teacher schedule; fresh has different noise and reset randomization.
No claim of strict all-foot success: existing metric remains a proxy.
Earlier claim 'no CUDA/Vulkan errors' for 05-32 smoke was too broad: startup
printed CUDA bad-state/enumeration warnings despite completing two updates.
The speed curriculum raised .15 to .45 in the warmup; low-speed is not fixed.

## Current verification / next step

Stopped warmup PID2339358 by INT, confirmed gone; placeholder restored2376745.
After 45 tests, launched bounded reset probe `/tmp/m1_reset_probe_20261001.sh`:
64env,55 updates, model29,LR0,teacher ratio .5 constant; save interval100.
Purpose: observe teacher re-arm across at least two full episodes, not PPO
learning or crossing acceptance. Log `/tmp/m1_reset_probe_20261001.log`.
Compare valid/applied before and after episode boundary; inspect termination,
collision, actual feet traces before any renewed long training.
Full crossing, stable touchdown, collision-free avoidance and video unresolved.
