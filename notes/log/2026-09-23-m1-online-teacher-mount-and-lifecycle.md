# M1 online MPC teacher mount and lifecycle

- Purpose: verify adaptive crossing teacher is actually mounted and long training owns placeholder GPU lifecycle.
- Changes: added `m1_cross_large_complex_ame_teacher` to trajectory-manager allowlist; enabled planner-owned cache in effective M1 post-init; refreshed manager before reading references; adapted M1 uppercase foot links and 12 planner joints; fixed infeasible-low obstacle mode overwrite.
- Verification: adaptive semantic tests `9 passed`; one-environment checkpoint smoke completed one iteration without trajectory-manager, joint-shape, Vulkan, or OOM errors.
- Long run: PID 3793266, GPU7, 256 envs, checkpoint `model_16900.pt`, log `/tmp/m1_adaptive_long_with_placeholder.log`.
- Lifecycle: wrapper `Go2Pvcnn/scripts/run_m1_train_with_placeholder.sh` stops only matching `/home/hexinkun/sleep.py` owned by current user and restores it on exit.
- Remaining: verify physical foot clearance, crossing success, collision-free large-obstacle avoidance after training; current early metrics are not completion evidence.


## 2026-09-24 follow-up
- Remote long run reached iteration 18050+ with 94-98% bad-orientation termination and zero crossing proxy; it was stopped after confirming the behavior was invalid.
- Root cause found in `on_policy_runner.py`: blended teacher actions were executed by the environment, while PPO transition storage retained pre-blend policy actions/log-probs.
- Fixed the rollout path to store the executed blended action and recompute the current-policy log-probability whenever teacher rows are applied. `python3 -m py_compile` passes.
- The old run was not launched through the corrected lifecycle wrapper, so it did not auto-restore the placeholder on exit. The placeholder was restored manually as PID 184877 with `CUDA_VISIBLE_DEVICES=7`; verified alive and using 384 MiB.


## 修复后 lifecycle smoke（2026-09-24）
- 修正包装器：不再用 `exec` 吞掉 `EXIT` trap；退出后恢复占位程序，并固定恢复到 `CUDA_VISIBLE_DEVICES=7`。
- 1 环境/1 迭代 smoke 正常完成：日志包含 `Starting Training`、`Learning iteration 16901/16902`、`Training Complete`，无姿态异常、Traceback、OOM。
- 生命周期证据：`PLACEHOLDER_STOPPED pid=194904` → 训练完成 → `PLACEHOLDER_RESTARTED`；当前占位 PID `205454` 存活。


## PPO transition 对齐复核（2026-09-24）
- 修复后的正式长训在第一次 PPO update 报 `RuntimeError: non-finite AME action mean`；该失败由把 teacher 执行动作直接写回 on-policy transition 引起，不能继续采用。
- 已撤回该 off-policy transition 写回，保留 teacher 仅作为环境执行层混合动作；`python3 -m py_compile` 通过。
- 第二次 1 环境/1 迭代 smoke 成功完成，无 `non-finite AME action mean`、Traceback 或 OOM；同时再次验证 `PLACEHOLDER_STOPPED` → `Training Complete` → `PLACEHOLDER_RESTARTED`。
- 真实长训仍未重新启动，需先设计独立的 teacher imitation/掩码更新链路，不能把 teacher 行为直接伪装成 PPO on-policy 样本。


## 配置重复定义清理（2026-09-24）
- `M1AmeCrossLargeComplexEnvCfg` 原有两个同名 `__post_init__`，前者会被后者完全覆盖；已合并为唯一方法。
- 抬腿高度 `nominal_swing_height_m=0.18` 与净空 `min_clearance_m=0.16` 现在在唯一有效方法开头设置。
- `py_compile` 与 AST 检查通过：`post_init_count=1`。


## Teacher 实际接管监控（2026-09-24）
- 在 PPO rollout 中新增真实计数：`m1_teacher_valid_fraction`、`m1_teacher_applied_fraction`、`m1_teacher_saturated_fraction`。
- 三项同时写入 TensorBoard 和终端；不再把计划 teacher ratio 当作实际控制比例。
- `on_policy_runner.py` `py_compile` 通过；当前没有启动训练，占位程序保持运行。


## 实际 teacher 饱和监控 smoke（2026-09-24）
- 修复后的 1-env smoke 输出：`M1 teacher valid/applied/saturated: 1.000/1.000/1.000`。
- 这证明 teacher 计划比例并不等于可执行动作：当前 MPC 参考全部触及 `[-1,1]` 归一化上限，之前的姿态异常有明确的动作饱和证据。
- 未启动长训；下一步应对照运行时 `default_joint_pos`、MPC `joint_angles` 与 M1 初始姿态，修正参考基准/动作尺度后再训练。


## default joint 顺序错位修复（2026-09-24）
- debug smoke 定位：MPC target 与 default 的取值范围相同，但逐关节 delta 最大 `1.6727 rad`，说明 raw `robot.data.default_joint_pos` 未按 M1 asset joint 名称排列。
- `AmeRslRlEnvWrapper.get_mpc_teacher_action` 已按 `robot.joint_names → M1_ASSET_JOINT_NAMES` 重排 default pose。
- 修复后首次参考 delta 最大/均值均为 `0.0000`，归一化 action range 为 `(0,0)`；1-env smoke 完成且占位自动恢复。后续约 `0.975` 饱和率来自后续规划帧，需单独按 phase 区分正常抬腿与异常饱和。


## 关节顺序回归（2026-09-24）
- 用反转 runtime joint order 的 CPU fixture 验证 `select_named_joint_state` + teacher adapter：`runtime_joint_reorder_teacher_regression=PASS`。
- 对齐后的同名 target 生成全零归一化动作且 valid=true，锁定本次顺序错位修复。


## 可执行 teacher 安全门（2026-09-24）
- 对归一化腿部动作增加 `abs(action).amax < 0.95` 安全门；接近执行饱和的 MPC 帧不再标记为 valid，由策略/避障分支接管。
- 5-iteration/1-env smoke：姿态异常始终 `0.0000`，teacher 饱和始终 `0.000`，实际接管比例随可执行 phase 在 `0.125–0.725` 变化；`Training Complete` 且占位自动恢复。
- `Crossing success proxy` 仍为 0，说明稳定性改善但真实跨越尚未验收。

## 2026-09-24 crossing state/rate hardening
- Added `lifted_before_front` to the crossing state. A crossing cannot complete if front wheels passed the obstacle before the required clearance was achieved.
- Collision frames are excluded from `crossed` accumulation; collision episodes remain failures.
- RED/GREEN: the new no-pre-lift and collision-not-success tests failed before the changes and focused suite now passes (`5 passed`).
- Runtime long-train verification remains open; do not claim physical crossing success from this unit test alone.

## 2026-09-24 runtime crossing gate
- `AmeRslRlEnvWrapper` now latches whether a semantic-small candidate produced positive `small_obstacle_climb` while active.
- Candidate disappearance only emits crossing completion when that lift latch is true; scrub-through trajectories are no longer counted.
- Focused state/metric tests remain green (`5 passed`); full Isaac runtime crossing remains to be physically validated.

### 2026-09-24 crossing lifecycle/rate completion
- Runtime crossing completion remains gated by semantic-small candidate persistence, observed positive small-obstacle climb, candidate disappearance, and collision exclusion.
- Crossing metrics now expose explicit `crossing_rate`, `crossing_success_rate`, and `obstacle_crossing_rate` aliases, all computed as completed candidate episodes divided by candidate episodes; collision completions are excluded.
- Verification: `93 passed, 1 skipped` for `Go2Pvcnn/tests/test_m1_*.py`.

### 2026-09-24 collision transition hardening
- `update_crossing_state` now accepts an explicit collision mask; active crossings transition to `FAILED` immediately and cannot emit completion on the same frame.
- Verification: M1 suite remains green after the new collision regression test.

### 2026-09-24 placeholder lifecycle smoke
- Ran `run_m1_train_with_placeholder.sh true`: observed `PLACEHOLDER_STOPPED` followed by `PLACEHOLDER_RESTARTED`; `/home/hexinkun/sleep.py` was alive afterward on GPU7.

### 2026-09-24 candidate-rate denominator correction
- `semantic_candidate_rate` now uses candidate episodes divided by all finished episodes, instead of returning 1 whenever any candidate was seen.
- Explicit crossing rates remain candidate-conditioned success rates.

### 2026-09-24 placeholder missing-at-start recovery
- Lifecycle wrapper now checks for the exact placeholder command at exit and restarts it even when it was already missing before training; anchored matching avoids `pgrep` self-matches.
- Verified both absent-at-start (`PLACEHOLDER_NOT_FOUND` -> `PLACEHOLDER_RESTARTED`) and nonzero-command (`WRAPPER_RC=1` -> `PLACEHOLDER_RESTARTED`) paths.

### 2026-09-24 placeholder readiness confirmation
- EXIT recovery now waits up to 10 seconds for the exact `sleep.py` process and emits `PLACEHOLDER_READY` or `PLACEHOLDER_RESTART_FAILED`.
- Smoke verification emitted `PLACEHOLDER_READY` and found the process alive afterward.

### 2026-09-24 bounded Isaac evaluation evidence
- With `DISPLAY=:7`, `--headless`, renderer multi-GPU disabled, and no `CUDA_VISIBLE_DEVICES` remapping, Isaac Sim starts successfully on physical `cuda:7`; the placeholder is restored afterward.
- Current checkpoint `model_16900.pt` over 100 small-obstacle steps reports `body_collision_episode_rate=1.0`, `small_crossing_rate=0.0`, `failure_termination_rate=0.0`; therefore crossing capability is not yet validated and the checkpoint is not acceptable as a success baseline.
- The earlier `localhost:10.0` run failed before environment creation with Vulkan present-queue/swapchain initialization; this is a launch-mode issue, separate from crossing behavior.
