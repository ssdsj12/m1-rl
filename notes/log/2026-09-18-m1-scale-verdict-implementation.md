# Task3：预算显式化的独立离线 verifier 实施记录

日期：2026-09-18。实施范围仅为 `scale1024/adapter/sync_verdict.py` 和新增 `tests/test_scale_verdict.py`。本记录由 Task3 实施子代理维护；主计划、索引、SPEC/quality 审核和 freeze 由主代理管理。

## 当前结论

实现及 CPU 验证完成，等待主代理的独立审核。没有启动 GPU/Isaac 物理运行，没有改 SDK、reference、正式 adapter、旧冻结 8-env adapter、控制器、runtime、桥接、指标、run.sh、既有测试或用户已有修改，没有 commit/promotion。

- 显式不可变 `RunBudget` 仅接受实际 Python int 的 `(8,1600)`、`(1024,32)`、`(1024,1600)`；默认旧 API 语义保留。
- 1024×32 startup 必须无 baseline；独立 observer/control replay、完整 1024 环境、动作 bitwise 和共同证据仍必须通过；明确 `strict_behavior_passed=false`，不生成 prefix/tail/strict 通过结论。
- 1024×1600 strict 必须有同规模 baseline。五十个 32-step chunks、1024 个 env IDs、Jacobians 维度、所有源绑定、实际 layout/grid/几何、初始随机化、live contract、cleanup/native/common guards 均验证。
- 只在完整验证后忽略 configuration/provenance 的指定顶层 `controller_mode`、候选专属 `diagnostic_candidate`；嵌套字段仍逐项相同，baseline 禁止 diagnostic metadata。
- baseline 可保留原始行为负结果和 wrapper3，但共同执行/传感/源/场景证据必须通过；完整首回合前缀必须持续到 candidate activation−1。后续 reset 不会缩短前缀或把 baseline 负结果改写为通过。
- 原 observer/event/control 运算与固定阈值、tail800/799 differences、半端点 ULP、完整动作 bitwise 比较保持；所有 N/T 仅为局部 budget 参数，没有全局维度 monkeypatch，没有导入 controller/torch/simulator/reference evaluator/scale_identity。

## TDD 与实际结果

先完整读取 `test-driven-development/SKILL.md` 及 `testing-anti-patterns.md`，先写新测试并上传服务器运行 RED，随后才修改生产代码。

1. 初次 focused RED：`45 failed, 1 passed, 1 deselected in 4.98s`。失败为缺失 immutable budget、budget API、startup CLI 等预期缺失；唯一通过项是已存在的 import independence。
2. 独立完整 fixture RED：真实生成 1024×1600 candidate/baseline 和 50-chunk 数组，`1 failed, 46 deselected in 29.41s`，因缺少 evaluate budget API 失败；maxRSS 143,168 KiB。这不是仅用八环境模拟维度。
3. 初次 focused GREEN：46 passed / 12.25s。
4. 第一轮完整读取触发 fixture bug：baseline 负结果只修改 final report，未同步 candidate_report 的 pre-final metrics，生产 guard 正确拒绝 `final/pre-final metrics evidence mismatch`。40.37s，maxRSS 7,678,056 KiB。修正 fixture 的真实 finalization 语义并重新绑定 candidate hash，未放松 guard。
5. 自审补充五条 RED，全部确实失败：缺少原始 gate、startup failure latch、浮点 config budget、浮点 cleanup steps、跨 chunk dtype 被 concatenate 提升。修复后新增测试 52 passed / 59.30s。
6. 补充 strict baseline later-reset/common-failure 正反例，并使独立 fixture 显式包含 wave interval 和最终 1.6 m local x。最终完整 suite：**504 passed（原445 + 新59）in 143.03s**，随后 `bash -n run.sh` 成功，整体 exit0。

最终全量命令（SSH 4090，当前目录 `/home/hexinkun/m1_debug_tools/scale1024_20260918/adapter`）：

```bash
/usr/bin/time -v env PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q -s --tb=short -p no:cacheprovider tests && bash -n run.sh
```

`-s` 仅为显示 synthetic fixture 资源统计；既有 failure-injection/orchestration 测试会输出其预期错误和替身进度日志，不代表启动了物理 simulator。

## 1024 实际数组证据与资源

开始前只读检查可用 RAM 954,304,548,864 bytes、磁盘 44,108,431,360 bytes。完整测试另对其独有临时目录检查 disk/RAM 各至少12 GiB。

最终 full fixture 路径：

`/tmp/pytest-of-hexinkun/pytest-218/test_full_1024x1600_fifty_chun0`

- 独立构造的固定 wheel velocity/command trace；prelift/overbar/passed/touchdown = 100/150/200/210，连续 readiness 245..249，activation=250；没有调用任何生产 replay/controller 生成预期 sidecar。
- 完整 candidate samples50、sync50、baseline samples50，1024 环境全部通过独立 replay、250-sample prefix、tail800/799-difference 检查；tail target RMS=0。
- baseline 最后一个环境保留原始 aggregate wheel-speed flag 负结果，`first_failure_step=null`，wrapper3，passed_envs1023；verdict 保留原始负报告和 metrics，没有将其改判通过。
- 单次 full fixture 构造+验证 wall45.670s；磁盘20,496,944 bytes（压缩 NPZ，加载时验证真实完整数组）。
- 完整504测试 `/usr/bin/time -v` wall2:23.68，maxRSS8,245,548 KiB，swap0，exit0。
- 独立 startup fixture 包含真实1024×32数组，并逐项实际改坏最后环境 shape/ID、replay、Jacobian、原生退出、source/layout/randomization/scanner 等证据验证拒绝。
- reset helper 正例包含两个后续 termination sample，而报告 reset_count仍为首回合结束计数1；公共计数不误当总 reset 次数。prefix边界单独覆盖 activation−1 拒绝、activation及更晚允许保留更早前缀。

这是 synthetic CPU 工件证据，**不是1024物理稳定性、动态 collision filtering、10000+并行或 learned crossing/avoidance 的证明**。layout 仍诚实保留 dynamic_collision_filtering_verified=false、bar_own_environment_isolation_verified=false。

## 文件完整性

本地与远端一致 SHA256：

- `sync_verdict.py`: `785a044f9d7f4f563e646787923e51e0181cb69718984e0ccffae8387d8bcdad`
- `tests/test_scale_verdict.py`: `8a65067369360b6760fe30b78f977f47982fc35f3dd6ba41fb684c45d2c48db3`

本地逐文件比对 Task2 accepted snapshot：除允许的 verifier 以外所有旧文件 hash 一致。远端 `diff -qr --exclude=sync_verdict.py --exclude=test_scale_verdict.py --exclude=__pycache__ task2_accepted/adapter adapter` 无差异。既有 `tests/test_sync_verdict.py` 与全部旧445测试文件未改。

主代理已另行使用旧冻结 verifier 对真实旧 run14 做只读复核（accepted=true/errors=[]/exit0）；该动作不属于本子代理运行的新1024 synthetic suite。

后续由主代理完成 SPEC/quality/freeze；若审核发现缺陷，应继续按测试先行处理并更新本记录。物理运行仍未授权于本实施子任务。

## 主代理独立复测

2026-09-18 主代理在服务器候选目录重新运行完整测试（不带 `-s`）及 `bash -n run.sh`：**504 passed in 142.19s**，整体 exit0。GNU time wall2:22.84，maxRSS8,246,416 KiB，swap0。远端 Task2 snapshot 排除这两个授权文件后 diff-qr 无差异；两个新文件 SHA 与上述实施结果完全一致。此处仍是 CPU 工件验证，等待独立 SPEC/quality 审查与物理容量测试。

## SPEC P2 修正：排除前验证 diagnostic metadata 的完整 schema

独立 SPEC reviewer 复现：候选 configuration/provenance 都追加相同未知字段 `diagnostic_candidate.unvalidated_physics_override={"friction":0}` 时，已知字段检查仍通过，随后整个对象被排除，未知内容未被验证。此问题与“先完整验证、再排除指定顶层差异”的合同不符。

按 TDD 新增 startup 和 strict metadata pair 两个参数化回归案例。先只上传测试，**2 failed, 59 deselected in 2.44s**：startup 仍错误 accepted=true，strict pair 未抛错，确认 RED。随后生产文件只加三行 1024 分支 exact-key-set guard，要求 diagnostic_candidate 恰有 `name/parameters/gate_source/gate_reasons/files` 五个规范键；原来各值、参数、gate、文件hash验证继续保留。旧8路径不增加该限制。

修复后 focused 命令：

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short -p no:cacheprovider tests/test_scale_verdict.py tests/test_sync_verdict.py -k "not full_1024"
```

结果：**101 passed, 1 deselected in 34.39s**。完整506测试（445旧 + 61新，包含50chunk全1024 synthetic replay）和 `bash -n run.sh` 已启动；完整结果另附后续记录。

此修订本地/远端一致 SHA256（替代前文实施阶段哈希）：

- `sync_verdict.py`: `3930483e477e0a1c6faa15c3a66dea97a20289d8e78cec9d9f4e6ca708dc79c5`
- `tests/test_scale_verdict.py`: `7fe86f1cbde05627087251a18b922f2f99d5b84964da3290576f44cdc993819a`

旧文件相对 Task2 snapshot 的逐项 hash 仍一致；此修订未执行任何 GPU/物理仿真、SDK/reference/正式目录修改或推广。

P2修复后的最终完整结果：**506 passed in 146.22s（原445 + 新61）**，完整命令与主代理标准命令一致（不带 `-s`，外层 `/usr/bin/time -v`），包含重新构造和验证的1024×1600五十chunk synthetic candidate/baseline，随后 `bash -n run.sh` 成功，整体 exit0。GNU time wall2:26.87、maxRSS8,243,444 KiB、swap0。源码维持上述最新两个SHA，未在测试期间修改。远端 snapshot `diff -qr` 再次无差异/exit0。此修复实施完成，交回主代理独立复审与 freeze。

## 独立审查及冻结完成

- SPEC 首轮发现上述 P2，修复后复审 PASS，独立101passed/1deselected；确认1024精确schema与旧8兼容。
- 质量审查 PASS，无具体 Critical/Important/Minor 问题；独立60passed/1deselected16.82s，并核对真实 runtime/metrics 产物语义。
- 主代理修复后单独验证 P2 两例：2passed1.68s；再次完整运行新旧 verifier suite，包含实际50chunk1024×1600构造和回放：**102passed78.81s**，bash语法与整体exit0。GNU time wall1:19.43，maxRSS7,883,376KiB，swap0。
- 本地 `scale1024/task3_accepted/adapter` 和远端 `/home/hexinkun/m1_debug_tools/scale1024_20260918/task3_accepted/adapter` 新建冻结副本，远端与候选 diff-qr0；没有覆盖 Task1/Task2/旧8 源码。正式 adapter 仍为原先推广版本，未推广scale。

Task3 已完成。接下来由主代理按 Task4 执行一次1024×32容量测试；未实际运行前不宣称物理稳定或行为通过。
