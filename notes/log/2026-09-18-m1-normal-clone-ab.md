# M1 普通复制路径隔离 A/B

## Purpose / Stage / Todo

T306.6h.5c.2，依赖已完成的 .5c.1 原生责任库定位。用户确认“继续”，实施 run10 之后的隔离候选。参见[设计](../../docs/superpowers/specs/2026-09-18-m1-normal-clone-design.md)、[计划](../../docs/superpowers/plans/2026-09-18-m1-normal-clone-ab.md)。

## 条件与基线

- 正式 adapter baseline 为 b60ca0f，未修改；候选基于 run10 的隔离 cache-off adapter。
- 工作目录 `/home/hexinkun/m1_debug_tools/gdb-jammy/normal_clone_20260918/adapter`。
- amp Python、物理 GPU7；占位 PID2795762 保留。17:41 预检查 GPU7 为 15754 MiB used / 8328 MiB free，0%。
- CPU 基线首次缺少 USD Python 路径，7 项出现 `pxr` import 错误；第二次缺动态库路径，7 项出现 `libtf.so` 错误。均为测试调用配置问题，未安装任何包或修改产品代码。
- 使用既有 USD Python 与 bin 路径后，完整基线 **170 passed in 23.45s**。

CPU 命令：

```bash
cd /home/hexinkun/m1_debug_tools/gdb-jammy/normal_clone_20260918/adapter
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 \
LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin \
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q -p no:cacheprovider tests
```

## 当前状态

**run11 隔离启动验收通过**：8×32 全部完成，native=0、wrapper=0、startup_passed=true，没有重启或强杀。规格复审与质量审查均通过。正式入口尚未接入；本结论不扩展为长训、跨越或动态碰撞过滤已通过。

## 实现与 CPU 证据

仅修改 runtime.py、tests/test_runtime_contract.py，新增 clone_evidence.py、tests/test_clone_evidence.py。runtime 相比 run10 隔离副本仅增加 7 行；run.py/run.sh/metrics/provenance 保持相同。碰撞证据是只读声明图，不是逐 collider/instance-proxy 或动态过滤证明。

- 配置 RED：1 failed in 0.21s；GREEN：1 passed in 0.16s。
- helper 缺失 RED：1 failed in 0.31s；GREEN：28 passed in 0.63s。
- validate_scene 接入 RED：2 failed / 28 deselected in 0.44s（缺证据、坏图未拒绝）。
- focused GREEN：31 passed in 0.80s。
- 完整实现代理回归：200 passed in 24.23s。
- 主代理独立回归：**200 passed in 24.05s**。日志：`/home/hexinkun/m1_debug_tools/gdb-jammy/normal_clone_20260918/cpu-tests-main.log`。
- `bash -n run.sh` 通过；正式 adapter 对 b60ca0f 的 diff 仍为零。

规格审查发现 inactive group / physicsScene 仍可被接受，已增加必需 prim/group 的 IsActive/IsDefined 检查。12 个 inactive/undefined 反例先 RED（12 failed / 30 deselected，0.62s），再 focused GREEN（42 passed，0.92s）。完整实现代理回归212 passed in 24.53s；**主代理独立212 passed in 24.43s**，原始输出 `cpu-tests-main-final.log`。审查代理独立重放两原始反例，均拒绝且 USD 未改动，规格复审通过。

候选 SHA256：

```text
runtime.py b37c98fee20c480fda451d727e8b697187a37a99fd790e9749c3154f5c1da91e
clone_evidence.py eb35f3e110e2d6fc806b05e540707e219e4ef993301be2d043090e7fb011a583
tests/test_runtime_contract.py 8f99cc21d5eee50e684e83f694e24e6b1cc18b05817d0e0b6476edcf2d3f457c
tests/test_clone_evidence.py 34f3e08bf387f032200d31cb17ca3cd0fb14234adf15d06e6f3fd48f13c9d2d2
run.py d81b598f74d940b76f64ca5d77390c25c99ad3d8b46d3bdf8515949c8f36771a
run.sh 9588480e6ad56ac1503026935318450303ffe341c065d9e8b9e0466cfe4d5700
```

## run11 实测结果

```bash
bash /home/hexinkun/m1_debug_tools/gdb-jammy/normal_clone_20260918/adapter/run.sh \
  --num-envs 8 --steps 32 \
  --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x32_11_normal_clone
```

原始 stdout/stderr 保存在输出目录同名前缀的 `.log`。无 GDB，core dump 禁用；无超时信号和自动重启。

- PID3438416，run ID `54b142d6-a94f-4248-812b-eddcbdabc6a8`；amp Python 3.10.21，物理 GPU7 UUID 与要求一致。
- 完整32步，prepare=32、IK=32；128次物理传感器更新，每个记录步4个子步；8个环境均0 reset、无first_failure，所有采样字段有限。
- native exit **0**、wrapper/finalizer **0**、completed=true、startup_passed=true、finalization_errors=[]、measurement_issues=[]。全部关闭标志出现后自然结束，PID已不存在。
- `passed=false` 是尚未运行1600步严格行为验收的标志，不代表此次 startup 失败；不要混淆两个门槛。
- scene valid、scanner valid、source bindings valid；9个实际碰撞组声明图符合预期，8条横杆均无collection归组，如实记录。未证明横杆own-env专属过滤或有接触机会时的动态过滤。
- 实测配置仍为cache-off，标准importlib hook，fast_shutdown=False；新增配置差异只有 `scene.replicate_physics: true → false`。
- 与run10比较：去掉新增collision证据后，scene_manifest逐字段完全相同；bindings_before完全相同。初始root/joint位置速度、mass/material、origins六组数组完全相同。
- 32步采样共29字段，**除elapsed_seconds外28字段逐元素完全相同**，包括root状态、关节状态、轮位置/接触、控制器/IK动作；这只覆盖短测轨迹，不外推所有后续物理行为。
- 报告elapsed_seconds=15.554117338964716；该值不含完整进程关闭耗时。run10有重型GDB，不能用两者直接宣称复制路径性能提升。
- 运行中单次GPU显存快照4931MiB（不是峰值测量）；结束后GPU7恢复15754MiB used / 8328MiB free、0%。占位PID2795762仍为原`python sleep.py`，未触碰。

质量审查无Critical/Important；Minor是stage不一致分支未有专门负例，可后续补，非此次阻碍。主代理独立复核CPU、配置差异、NPZ数据、原生码与进程退出。

## Git / Follow-up（最终）

Baseline Ref：b60ca0f；设计提交4b735f8；Candidate Ref：上述隔离文件哈希。正式adapter对b60ca0f的diff仍为零，SDK `_physx` SHA仍为2e88c44ddec4e9b76f2b8b2b520a003cd19e3466ede7b7db7402825ce731f420。

.5c.2关闭为“隔离startup已验证”；新.5c.3待接入审查及既定3次8×1600严格行为验收，之后才可1024容量/行为验证。本次wave_gate一直false，还没有跨越动作或学习；未启动10000轮。当前占位下GPU7仅约8.3GB空闲，1024容量不能预设可容纳。保留全部候选与证据，不合并、不清理、不修改正式环境。与[任务分支](../todo/T306-m1-ame-long-train-stability.md)同步。
