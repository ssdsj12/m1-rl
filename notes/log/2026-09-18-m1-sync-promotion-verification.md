# M1 post-cross sync 正式接入验证

Parent: T306.6h.6a.1。日期：2026-09-18（Asia/Shanghai）。

## 范围与状态

将已冻结的隔离 post_cross_sync 候选按字节原样接入正式 reference adapter。接入验证使用 CPU，没有启动 Isaac 仿真、CUDA workload、训练或评测，没有发送进程信号，也未安装依赖。SDK、参考源码、AME、控制参数和验收阈值均不在本次修改范围。

- 正式目录：`/home/hexinkun/m1_rl/tools/m1_reference_validation`。
- 冻结来源：`/home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter`。
- 本地冻结副本：`C:/Users/xk/Documents/project/m1_reference_validation_stage/post_cross_sync/adapter`。
- Baseline Ref：`a86cbf5`。
- 接入前 HEAD：`6c53e328f631a84cf2c73e735c70382ddb73e99f`。
- Candidate Ref：下列八文件 SHA256；没有暂存或提交。
- 状态：接入与 CPU 全量验证完成，373 passed；随后独立SPEC/quality均PASS，主代理又复验373passed74.37s，正式提交646f486。完整限制及测试CWD问题见[主代理复核](2026-09-18-m1-sync-promotion-recheck.md)。
- 历史物理背景由主代理维护：run14/15/16 已在同一冻结候选下各完成严格 8×1600。此文不把历史候选物理结果冒充本次正式路径仿真。

遵循仓库 AGENTS 的 Subagent Override 和本次具体委派范围；不修改 root notes，由主代理统一维护 dashboard / branch / log index。

## Preflight 与原有 dirty 保护

接入前运行 `git diff --exit-code a86cbf5 -- tools/m1_reference_validation`，无输出、exit 0。新增三个源码与三个测试路径均由 `test ! -e` 确认不存在。正式目录当时只有十个既有文件。

全仓已有大量 unrelated dirty 状态：29 个 tracked 修改，`git status --porcelain=v1 --untracked-files=all` 共 9617 行。以下快照和 SHA256 在复制前取得；在复制后再次检查，adapter 外 status/hash 保持一致。

| 快照内容 | 接入前 SHA256 | 接入后 SHA256 |
| --- | --- | --- |
| `git diff --binary`，接入前整个 tracked worktree | `69468ac64c318c7f9002abcfc24c97ed5f06287c855eff528e88e57b072cadd2` | 本列全仓随后含接入修改，不作为不变合同 |
| `git diff --binary -- . ':(exclude)tools/m1_reference_validation'` | `69468ac64c318c7f9002abcfc24c97ed5f06287c855eff528e88e57b072cadd2` | `69468ac64c318c7f9002abcfc24c97ed5f06287c855eff528e88e57b072cadd2` |
| adapter 外 `git status --porcelain=v1 --untracked-files=all` | `4cafe6c864fa3140b25b7de3191206cd7c2b13f4cc0e19a0d2f0a1c908ea9a49` | `4cafe6c864fa3140b25b7de3191206cd7c2b13f4cc0e19a0d2f0a1c908ea9a49` |
| `git diff --cached --binary` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

完整 `--untracked-files=all` status 的接入前 hash 同为 `4cafe6c864fa3140b25b7de3191206cd7c2b13f4cc0e19a0d2f0a1c908ea9a49`，因为当时 adapter 没有 dirty 文件。下方保留 compact status 原样输出，完整状态由上述 hash/count 标识。

## Tests-first RED

先只通过 `cp` 原样复制三份冻结测试到正式 tests 目录。该时刻 formal status 只有：

```text
?? tests/test_post_cross_sync.py
?? tests/test_sync_bridge.py
?? tests/test_sync_verdict.py
```

没有修改测试，也没有先复制实现。执行：

```bash
cd /home/hexinkun/m1_rl/tools/m1_reference_validation
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 \
LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin \
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short -p no:cacheprovider \
tests/test_post_cross_sync.py tests/test_sync_bridge.py tests/test_sync_verdict.py
```

实际 exit 1，摘要与代表性错误原文：

```text
120 failed, 41 errors in 6.42s
E   AssertionError: Missing post-cross bridge
E   AssertionError: Missing recorder reset hook
E   AssertionError: Missing candidate wrapper installation
E   FileNotFoundError: [Errno 2] No such file or directory: '/home/hexinkun/m1_rl/tools/m1_reference_validation/post_cross_sync.py'
```

100 个 core tests 和 20 个 bridge tests 失败；41 个 verifier fixtures 因读取尚不存在的 core 源文件以生成 source hash 而报错。原因均符合“实现未接入”，不是测试阈值调整或环境依赖问题。由于输出含大量相同栈，此文记录精确摘要和代表性错误，不声称附有未截断完整 RED transcript。

## 原样接入与 SHA256

观察 RED 后才通过 `cp` 复制五份源码。八文件 remote candidate / formal 的 `cmp` 均 exit 0；本地 candidate 的 `Get-FileHash -Algorithm SHA256` 也逐个等于下表。控制数值、参数、阈值和代码内容未做语义修改。

| 文件（formal 相对路径） | remote candidate = formal = local candidate SHA256 |
| --- | --- |
| `post_cross_sync.py` | `18aeb0c711344af06dff41c49254048ea5f37cea94adc605c989e1f1057bc87c` |
| `sync_bridge.py` | `817ed0358dda874e020661862d9019ba1bbe5abee4a99858f5b64fdb36390254` |
| `sync_verdict.py` | `1e93707e2f959b7ae2226438300a734ed3dd0911ffa782a589b98aa6986324bf` |
| `run.py` | `ba2b27001d864b9f4b6ebcfa2f2907c93d0c1e511c861151f4e06f5a47734d80` |
| `runtime.py` | `1825d1259759cb7950147de36263d932ec0e9f0372cd8a3a3dac61b66ff8ffbc` |
| `tests/test_post_cross_sync.py` | `e3a3f50be69f78b9571f160b3233c1f721dd04686dbad2191026956b4f58aad9` |
| `tests/test_sync_bridge.py` | `60c1c7495c0b97f8f15daa09d53fb9dc2ff1603d4c2719cdd284e597cefc7a04` |
| `tests/test_sync_verdict.py` | `0233c16bb15b6d03603960af06cce46289b3a7cc266b3d29edb357885fb6fabd` |

两个被更新既有文件接入前 hash：

| 文件 | 接入前 SHA256 |
| --- | --- |
| `run.py` | `d81b598f74d940b76f64ca5d77390c25c99ad3d8b46d3bdf8515949c8f36771a` |
| `runtime.py` | `b37c98fee20c480fda451d727e8b697187a37a99fd790e9749c3154f5c1da91e` |

其余八个正式既有文件接入前后 SHA256 完全相同：

| 文件 | 前后共同 SHA256 |
| --- | --- |
| `clone_evidence.py` | `eb35f3e110e2d6fc806b05e540707e219e4ef993301be2d043090e7fb011a583` |
| `metrics.py` | `a9487322dc3bda415877786f0d243c0a76b0067669f2ee06953c857845d1b419` |
| `provenance.py` | `e065452fed2340d1be1539ed4849e6fcff680de99ef21ef26c6253ec92929e31` |
| `run.sh` | `9588480e6ad56ac1503026935318450303ffe341c065d9e8b9e0466cfe4d5700` |
| `tests/test_clone_evidence.py` | `34f3e08bf387f032200d31cb17ca3cd0fb14234adf15d06e6f3fd48f13c9d2d2` |
| `tests/test_metrics.py` | `a7bbd97a7b73c2ffedd7123753421bac2e8fef45ea36aeb23097d9b35c7bea13` |
| `tests/test_provenance.py` | `d05fdcebe279dba38ba70b648f473425a701f32e8295dcd209fe47cdef46e3ff` |
| `tests/test_runtime_contract.py` | `8f99cc21d5eee50e684e83f694e24e6b1cc18b05817d0e0b6476edcf2d3f457c` |

## GREEN 与最终范围

在正式目录使用与 RED 相同的 amp CPU 环境变量，测试目标改为全量 `tests`，随后执行 `bash -n run.sh`：

```bash
cd /home/hexinkun/m1_rl/tools/m1_reference_validation
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 \
LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin \
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short -p no:cacheprovider tests && bash -n run.sh
```

实际输出与退出码：

```text
373 passed in 75.02s (0:01:15)
exit_code=0
```

`bash -n run.sh` 无输出且 exit 0。2026-09-18T20:29:55+08:00 的最终只读核对也 exit 0：HEAD 未变，index diff 为空，adapter 外 tracked diff/status 哈希仍与 preflight 一致，formal 仅 16 个文件，八个接入文件逐个 `cmp` 冻结来源相同，其余八个文件分别通过 `git show a86cbf5:tools/m1_reference_validation/<path> | cmp - <path>`。因此全量测试没有产生额外 bytecode/cache 文件，也没有改变非目标既有文件。

接入后的 formal tracked diff 精确只有：

```text
5  0  tools/m1_reference_validation/run.py
13 1  tools/m1_reference_validation/runtime.py
2 files changed, 18 insertions(+), 1 deletion(-)
```

六个新增文件为三份 sync 源码和三份测试，分别 323/190/495/572/246/378 行，共 2204 行。没有 `git add`；因此常规 `git diff --stat` 不含六个 untracked 文件，review 必须同时看 `git ls-files --others --exclude-standard tools/m1_reference_validation`。完整八文件范围：

```text
 M tools/m1_reference_validation/run.py
 M tools/m1_reference_validation/runtime.py
?? tools/m1_reference_validation/post_cross_sync.py
?? tools/m1_reference_validation/sync_bridge.py
?? tools/m1_reference_validation/sync_verdict.py
?? tools/m1_reference_validation/tests/test_post_cross_sync.py
?? tools/m1_reference_validation/tests/test_sync_bridge.py
?? tools/m1_reference_validation/tests/test_sync_verdict.py
```

`git diff --check -- tools/m1_reference_validation` 无输出、exit 0。后续独立 review/commit 由主代理执行；本次未修改根 notes，未验证正式路径物理运行，也未验证 1024 容量/行为、AME 或 10000 训练。

## 接入前 compact status 快照

```text
 M Go2Pvcnn/README.md
 M Go2Pvcnn/ame_baseline/m1_ame_env_cfg.py
 M Go2Pvcnn/ame_baseline/m1_ame_terminations.py
 M Go2Pvcnn/ame_baseline/m1_ame_train_cfg.py
 M Go2Pvcnn/extension/parallelism/collision.py
 M Go2Pvcnn/extension/parallelism/config.py
 M Go2Pvcnn/extension/parallelism/m1_kinematics.py
 M Go2Pvcnn/extension/viz/go2_foostep_planner.py
 M Go2Pvcnn/go2_pvcnn/sensor/semantic_raycaster/semantic_ray_caster.py
 M Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py
 M Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_amp.py
 M Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_amp_headless.sh
 M Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh
 M Go2Pvcnn/tests/test_m1_ame_config_static.py
 M Go2Pvcnn/tests/test_m1_ame_terminations.py
 M Go2Pvcnn/tests/test_m1_parallelism_rl_adapter.py
 M Go2Pvcnn/tests/test_viewer_reset.py
 M Go2Pvcnn/tests/tracking/test_policy_geometry_rewards.py
 M Go2Pvcnn/tracking/mdp/__init__.py
 M Go2Pvcnn/tracking/mdp/policy_geometry_rewards.py
 M docs/superpowers/plans/2026-09-18-m1-reference-runtime.md
 M docs/superpowers/plans/2026-09-18-m1-wheel-obstacle-rewards.md
 M docs/superpowers/specs/2026-09-18-m1-post-cross-wheel-sync-design.md
 M docs/superpowers/specs/2026-09-18-m1-wheel-equalizer-ab-design.md
 M notes/ai/ai-03-environment-and-observations.md
 M notes/human/human-03-environment-and-observations.md
 M notes/log/index.md
 M notes/todo.md
 M notes/todo/T306-m1-ame-long-train-stability.md
?? .agents/
?? .claude/
?? .cursor/
?? .github/
?? .obsidian/
?? Go2Pvcnn/ame_baseline/m1_ame_actions.py
?? Go2Pvcnn/ame_baseline/m1_ame_assets.py
?? Go2Pvcnn/ame_baseline/m1_ame_contract.py
?? Go2Pvcnn/ame_baseline/m1_ame_rewards.py
?? Go2Pvcnn/ame_baseline/m1_evaluation_metrics.py
?? Go2Pvcnn/ame_baseline/m1_obstacle_rewards.py
?? Go2Pvcnn/extension/mesh_triangulation.py
?? Go2Pvcnn/scripts/audit_m1_contact_events.py
?? Go2Pvcnn/scripts/audit_m1_knee_proxy.py
?? Go2Pvcnn/scripts/evaluate_m1_ame.py
?? Go2Pvcnn/scripts/m1_probe_diagnostics.py
?? Go2Pvcnn/scripts/probe_m1_rewards.py
?? Go2Pvcnn/scripts/run_m1_validation.sh
?? Go2Pvcnn/tests/isaac_m1_viewer_smoke.py
?? Go2Pvcnn/tests/test_m1_ame_action_contract.py
?? Go2Pvcnn/tests/test_m1_contact_overlap_audit.py
?? Go2Pvcnn/tests/test_m1_evaluation_metrics.py
?? Go2Pvcnn/tests/test_m1_exploration_cfg.py
?? Go2Pvcnn/tests/test_m1_obstacle_rewards.py
?? Go2Pvcnn/tests/test_m1_probe_diagnostics.py
?? Go2Pvcnn/tests/test_m1_rl_reward_geometry.py
?? Go2Pvcnn/tests/test_m1_viewer_backend_static.py
?? Go2Pvcnn/tests/test_usd_mesh_triangulation.py
?? Go2Pvcnn/tests/tracking/test_m1_viewer_env_cfg_static.py
?? Go2Pvcnn/tracking/m1_parallelism_viewer_env_cfg.py
?? assets/
?? docs/superpowers/plans/2026-08-24-m1-parallelism-robot-backend.md
?? docs/superpowers/plans/2026-09-02-m1-selective-swing-implementation-plan.md
?? docs/superpowers/plans/2026-09-02-m1-trot-stance-lock-implementation-plan.md
?? docs/superpowers/plans/2026-09-17-m1-ame-reward-alignment.md
?? docs/superpowers/plans/2026-09-18-m1-native-exit-owner.md
?? docs/superpowers/plans/2026-09-18-m1-normal-clone-ab.md
?? docs/superpowers/plans/2026-09-18-m1-normal-clone-promotion.md
?? docs/superpowers/plans/2026-09-18-m1-post-cross-wheel-sync.md
?? docs/superpowers/plans/2026-09-18-m1-wheel-equalizer-ab.md
?? eval_output/
?? evaluation/
?? notes/log/2026-09-17-m1-evaluation-terminal-failure.md
?? notes/log/2026-09-17-m1-exploration-budget.md
?? notes/log/2026-09-17-m1-floating-1024-stability.md
?? notes/log/2026-09-17-m1-floating-ame-smoke.md
?? notes/log/2026-09-17-m1-floating-amp-smoke.md
?? notes/log/2026-09-17-m1-floating-drive-gate.md
?? notes/log/2026-09-17-m1-floating-regression.md
?? notes/log/2026-09-17-m1-large-baseline.md
?? notes/log/2026-09-17-m1-noise02-1000-learning-gate.md
?? notes/log/2026-09-17-m1-noise02-1024-training.md
?? notes/log/2026-09-17-m1-noise02-drive-probe.md
?? notes/log/2026-09-17-m1-noise02-flat120.md
?? notes/log/2026-09-17-m1-noise02-large120.md
?? notes/log/2026-09-17-m1-noise02-small120.md
?? notes/log/2026-09-17-m1-obstacle-stop-reward-audit.md
?? notes/log/2026-09-17-m1-sem1wheel-flat120.md
?? notes/log/2026-09-17-m1-sem1wheel-large120.md
?? notes/log/2026-09-17-m1-sem1wheel-small120.md
?? notes/log/2026-09-17-m1-semantic1-wheel-120-training.md
?? notes/log/2026-09-17-m1-small-baseline.md
?? notes/log/2026-09-17-m1-std1-flat120.md
?? notes/log/2026-09-17-m1-std1-large120.md
?? notes/log/2026-09-17-m1-std1-small120.md
?? notes/log/2026-09-17-m1-step-height-matched-probe.md
?? notes/log/2026-09-18-m1-knee-proxy-source-audit.md
?? notes/log/2026-09-18-m1-native-exit-owner-audit.md
?? notes/log/2026-09-18-m1-normal-clone-ab.md
?? notes/log/2026-09-18-m1-physx-exit-owner-capture.md
?? notes/log/2026-09-18-m1-post-cross-sync-design-audit.md
?? notes/log/2026-09-18-m1-post-cross-sync-implementation.md
?? notes/log/2026-09-18-m1-probe-neighbor-contamination-fix.md
?? notes/log/2026-09-18-m1-reference-controller-design.md
?? notes/log/2026-09-18-m1-reference-fatal-diagnostics.md
?? notes/log/2026-09-18-m1-reference-gdb-capture.md
?? notes/log/2026-09-18-m1-reference-gdb-frames.md
?? notes/log/2026-09-18-m1-reference-gpu-resource-blocker.md
?? notes/log/2026-09-18-m1-reference-gpu7-faulttrace.md
?? notes/log/2026-09-18-m1-reference-gpu7-hold.md
?? notes/log/2026-09-18-m1-reference-gpu7-smoke.md
?? notes/log/2026-09-18-m1-reference-launcher-cleanup.md
?? notes/log/2026-09-18-m1-reference-metrics.md
?? notes/log/2026-09-18-m1-reference-owner-cleanup.md
?? notes/log/2026-09-18-m1-reference-preflight.md
?? notes/log/2026-09-18-m1-reference-runtime.md
?? notes/log/2026-09-18-m1-reference-stat-cache-gate.md
?? notes/log/2026-09-18-m1-reference-strict-run12.md
?? notes/log/2026-09-18-m1-reference-vulkan-preflight.md
?? notes/log/2026-09-18-m1-reward-hook-bootstrap-probe.md
?? notes/log/2026-09-18-m1-wheel-equalizer-ab.md
?? notes/log/2026-09-18-m1-wheel-reward-1024-pilot.md
?? notes/log/2026-09-18-m1-wheel-reward-implementation.md
?? notes/log/2026-09-18-m1-wheel-reward-physical-probe.md
?? notes/log/2026-09-18-m1-wheel-reward-smoke.md
?? notes/log/2026-09-18-m1-wheelreward-exposure-trace.md
?? notes/log/2026-09-18-m1-wheelreward-flat120.md
?? notes/log/2026-09-18-m1-wheelreward-large120.md
?? notes/log/2026-09-18-m1-wheelreward-small120.md
?? notes/log/2026-09-18-m1-wheelreward-tail-audit.md
?? plugins/
?? run_logs/
?? semloco/
?? tmp/
```
