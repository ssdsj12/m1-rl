# M1 普通物理复制隔离 A/B 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** 验证关闭快速物理复制能否消除 run10 的 post-close 原生崩溃，同时保留既有场景与碰撞隔离要求。

**Architecture:** 用户已于本轮“继续”批准此前记录的隔离方案。复制 run10 adapter 到独立 normal_clone_20260918 目录，不改正式入口或 SDK。仅增加 `scene.replicate_physics=False` 配置差异；新增观测只读取场景，不修改 USD。原始源代码、控制器、奖励和阈值不变。

**Tech Stack:** amp Python 3.10、Isaac Sim 4.5、IsaacLab45、pytest、USD 只读 API；物理 GPU7。

设计依据：[run10 证据与用户已批准候选](../../../notes/log/2026-09-18-m1-physx-exit-owner-capture.md)。范围不含自动重启、SDK 补丁、正常训练或占位进程操作。

## 1. 隔离与基线

- [x] 保留正式 adapter 和先前诊断现场。工作目录 `/home/hexinkun/m1_debug_tools/gdb-jammy/normal_clone_20260918/adapter`；本地对应 `m1_reference_validation_stage/normal_clone/adapter`。这延续用户指定的隔离副本，不新建或切换正式 git 工作树。
- [x] 使用 amp + 已安装 omni.usd.libs 的 PYTHONPATH 和 bin 的 LD_LIBRARY_PATH 运行复制 adapter 全套 CPU 测试：170 passed in 23.45s。两次初始调用分别遗漏 Python / 动态库路径，均已修正，不是产品回归。

## 2. 最小实现与 TDD（一个实现代理）

**Files:** `adapter/runtime.py`、`adapter/tests/test_runtime_contract.py`；必要时新增独立 `adapter/clone_evidence.py` 和对应测试，避免扩大 runtime.py。

- [x] 先在既有 adapt_cfg fixture 中声明 `replicate_physics=True, filter_collisions=True`，断言 before 为 true、after 为 false、changes 包含精确字段，同时 filter_collisions 和控制器/奖励配置未变。先运行看到预期失败。
- [x] 最小配置改动：

```python
# _ALLOWED_CFG 新增这一精确字段，不允许改变 filter_collisions。
"scene.replicate_physics"
# adapt_cfg，在创建环境前：
cfg.scene.replicate_physics = False
```

- [x] 从实际 `env.scene.cfg` 与 USD stage 读取复制方式、collision groups 和 collider collection / filtered-group 关系，写入独立证据或 scene manifest；要求 filter_collisions=True。读到缺失/无效关系时失败关闭，而非仅记录警告。具体公开 API 依据已安装 Cloner 的 filter_collisions 实现。
- [x] 用 CPU USD stage fixture 先验证碰撞证据的有效/缺失/跨环境串组案例，再实现最小只读采集/验证函数。不得创建或修改实测 stage 的 prim、属性、关系。
- [x] GREEN 后运行全部 CPU 测试；规格审查通过后再做质量审查，修正 must-fix 后由主代理独立复跑。

## 3. 单次实测（主代理）

- [x] 核实 GPU7 UUID、空闲显存、占位 PID2795762 的身份与命令，确认无重复自有 Isaac；正式 adapter 对 b60ca0f diff 仍为零。
- [x] 使用候选原有 run.sh，以 `--num-envs 8 --steps 32 --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x32_11_normal_clone` 运行，无 GDB、无自动重启、无超时强杀。保存 stdout/stderr；定期检查本次 PID 和 status。
- [x] 要求 native exit=0、wrapper/finalizer=0、32 samples/counters 完整、source bindings 有效、scene valid、实际 replicate_physics=false、碰撞过滤证据通过。对照 run10 的场景、初始状态与配置，分别记录差异，不把所有浮点量强行认定一致。
- [x] 失败时保留证据并停止扩大测试；通过也仅说明短 smoke 和场景契约，不是 10000 轮或跨越成功。正式接入和 3×8×1600 属于后续阶段，不能跳过行为门槛。

## 4. 证据交付

- [x] 更新 notes/todo.md、T306.6h.5c.2 和日志索引、新增本次日志；记录 baseline/candidate hashes、准确命令、CPU/原生退出结果和未验证事项。
- [x] 确认本次子进程自然退出、占位保留、正式代码未改，报告实际范围。不以 shell0 掩盖原生134，不以 checkpoint 续跑代替稳定性修复。

## 自审

最终结果：212CPUtests、规格复审/质量审查通过；run11单次8×32 native0/wrapper0/startup_passed=true。只有复制flag配置不同，28非计时采样字段与run10完全相同。正式入口未接入、占位保留；后续接入/3×1600/1024/10000不在本次已完成范围。[结果](../../../notes/log/2026-09-18-m1-normal-clone-ab.md)。

设计与前次用户已批准候选一致；没有 SDK 升级或物理/奖励参数扩展。增加场景只读证据是防止切换 clone 路径损坏过滤的验证手段。仅本隔离候选可改，失败不改正式工作树。
