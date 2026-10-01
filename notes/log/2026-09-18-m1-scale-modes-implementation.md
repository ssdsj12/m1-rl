# Task 2：显式 reference baseline 与共同 scale identity

日期：2026-09-18。范围仅为隔离候选
`/home/hexinkun/m1_debug_tools/scale1024_20260918/adapter`。
本轮未启动 Isaac/AppLauncher 或 GPU 仿真，未改 SDK、依赖、参考源、正式目录或提交。

## 实现与 schema

- `runtime.py` 只改 `parse_args`：新增 `--controller-mode {post-cross-sync,reference}`，默认 `post-cross-sync`；reference 仅接受 1024 环境、1600 步，解析期间即拒绝其他组合。
- `scale_identity.py` 为 CPU-safe builder：不导入 torch/模拟器；从冻结 `sync_bridge.PARAMETERS` 深拷贝参数，读取七份实际源码计算 SHA256。
- `run.py` 只改 metadata 和控制器模式分支：仍先 instrument 原 wrapper，再按模式安装 candidate wrapper；reference 直接使用 instrumented original wrapper，并真实调用冻结的 `validate_live_contract` 写 `sync_live_contract.json`。
- `configuration.json` / `provenance.json` 的 1024 模式新增顶层 `controller_mode`、`scale_identity`。reference 不含 `diagnostic_candidate`；candidate 保留完整 `candidate_metadata()`。N8 不新增 mode/identity 字段。
- 1024 的日志和 `candidate_report.json` 增加实际 `controller_mode` 与 `controller_purpose`；reference purpose 明确标记 reference baseline。没有制造 passed/completed，finalizer、cleanup、run.sh 未改。

Task 3 消费接口固定为：

```text
configuration.json / provenance.json
  controller_mode: "post-cross-sync" | "reference"
  scale_identity:
    version: "m1_reference_scale_v1"
    num_envs: 1024
    layout_name: "m1_grid32x32_v1"
    controller_parameters: deepcopy(sync_bridge.PARAMETERS)
    files: {run.py, runtime.py, scale_layout.py, scale_identity.py,
            sync_verdict.py, post_cross_sync.py, sync_bridge.py} -> lowercase SHA256
```

共同 identity 不含 mode，也不含运行路径；同一组源码的两种模式、configuration/provenance 使用同一身份值。各次 builder 返回的嵌套参数和 files 均相互独立。后续 Task 3 修改 `sync_verdict.py` 时其哈希自然更新。

## TDD 证据

实际执行命令（SSH alias `4090`，从候选 adapter cwd 执行）：

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short -p no:cacheprovider tests/test_scale_modes.py
```

1. 先加测试，尚未改 production：`12 failed, 1 passed in 2.02s`。缺少 CLI mode、identity 文件及 reference branch；原 N8 orchestration 测试已通过。
2. 只实现 CLI/identity 后：`2 failed, 11 passed in 2.30s`。失败明确为 reference 调用了被设置为必抛的 `make_sync_wrapper`，证明真实分支缺失。
3. 实现 run 分支/metadata：`13 passed in 2.11s`。
4. 新增完整 reference 1600 循环/正常返回测试：`1 failed, 13 passed in 2.45s`，缺少 `candidate_report.controller_mode`。补充 1024-only 报告 mode/purpose 后：`14 passed in 2.78s`。

新测试保留真实 `run.main`、argument parsing、adapt_cfg、instrumentation、step_once、write_json、cleanup、sync wrapper/bridge/core 与 live contract。SDK/CUDA 启动、场景测量、传感器采样为显式 CPU 边界替身，复用旧测试的完整 action/actuator 合同结构。未新增 production test-only API。

两种 1024 模式的比较用例刻意在两个 CPU 采样后停止：明确断言 return code 1 与 `Simulation stopped prematurely before step 2`，验证失败清理、身份一致、原 prepare/IK/reset 归属和 sidecar 分支。这只是 CPU 分支证据，不是完整物理运行。独立 reference 正常返回用例执行声明的全部 1600 次循环，断言 1600 次原 prepare/IK、一次 reset、真实 candidate 报告/POST_CLEANUP/hash、正常 cleanup，以及仍未 process-finalized；同样不代表物理验证。

还覆盖：错误 reference 参数在 interpreter/output/App 之前拒绝；baseline 禁止创建 candidate wrapper/SyncBridge、sync_observer 始终为空；实际 action scale 错误被 live contract 拒绝；两模式 live contract 内容相等；runtime_metadata 中实际写入的 scale_layout 等于 scene_report 返回值；原 GPU7/device/fast_shutdown 与 N8 metadata/默认 candidate 分支保持原样。

## 全量验证

```bash
cd /home/hexinkun/m1_debug_tools/scale1024_20260918/adapter
env PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short -p no:cacheprovider tests && bash -n run.sh
```

结果：`445 passed in 78.13s (0:01:18)`，退出码 0，包含旧 431 项全部测试和新增 14 项；`bash -n run.sh` 同链通过。

## Diff / 哈希与自查

`diff -rq /home/hexinkun/m1_debug_tools/scale1024_20260918/task1_accepted/adapter /home/hexinkun/m1_debug_tools/scale1024_20260918/adapter` 仅列：修改 `run.py`、`runtime.py`，新增 `scale_identity.py`、`tests/test_scale_modes.py`。旧测试全部逐字节不变。

对以下文件在当前候选和冻结原 8 环境候选 `/home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter` 执行 `sha256sum`，结果完全相等：

| 文件 | SHA256 |
|---|---|
| post_cross_sync.py | 18aeb0c711344af06dff41c49254048ea5f37cea94adc605c989e1f1057bc87c |
| sync_bridge.py | 817ed0358dda874e020661862d9019ba1bbe5abee4a99858f5b64fdb36390254 |
| sync_verdict.py | 1e93707e2f959b7ae2226438300a734ed3dd0911ffa782a589b98aa6986324bf |
| metrics.py | a9487322dc3bda415877786f0d243c0a76b0067669f2ee06953c857845d1b419 |
| provenance.py | e065452fed2340d1be1539ed4849e6fcff680de99ef21ef26c6253ec92929e31 |
| clone_evidence.py | eb35f3e110e2d6fc806b05e540707e219e4ef993301be2d043090e7fb011a583 |
| run.sh | 9588480e6ad56ac1503026935318450303ffe341c065d9e8b9e0466cfe4d5700 |

Task1 冻结 `scale_layout.py` 保持 `11cea40eea64d9182e5ae5d23e249018d3246486bbd438077512d4317f4b8633`。
本地 `Get-FileHash -Algorithm SHA256` 与远程 `sha256sum` 的四个 Task2 文件完全相等：

| 文件 | SHA256 |
|---|---|
| run.py | bcd44b214a2201a435ff21d44e4dd7d4d1e774e70216efb402fc03b43c9d665d |
| runtime.py | 1ce59eb067ec6a84d94df689d966fb3fc21d48bef57b7f93a60be14e3d135f27 |
| scale_identity.py | 2d4bc4b49843da157236ae9323047a93fead8453756a1252a18c2d0f9fccd037 |
| tests/test_scale_modes.py | 7cbddda03403907e391be04d7cf8e7acde78248f3dbc4f06446ec65c06b39f79 |

自查确认：runtime diff 仅参数解析；run diff 仅导入、metadata、模式分支；原 instrument→wrapper init/reset→validate_scene→RuntimeSink→holder 顺序保留，原 release_runtime_owners/cleanup/finalizer 内容未改。新增对象仅为普通 metadata，未额外保留 native owner。未实现 Task3 verifier，也未将候选带入正式工具目录。

## 独立审查与阶段冻结

主代理重新执行focused14tests：2.47s，exit0，并核对四文件local/remote SHA一致。独立SPEC PASS（14passed2.79s），独立quality PASS（14passed3.08s；无Critical/Important/Minor阻断）。两者都确认仅授权四文件变更、真实main/contract/cleanup测试以及formal646f486不动。Task1的静态metadata测试弱点已通过本Task2写入payload测试补覆盖。

Task2源字节已冻结到本地 `m1_reference_validation_stage/scale1024/task2_accepted/adapter` 和远端 `/home/hexinkun/m1_debug_tools/scale1024_20260918/task2_accepted/adapter`，新目录预检查、复制及远端diff-qr通过。后续Task3仅允许更改working candidate的verifier并新增其测试；本快照和Task1/原8env快照保持只读。仍无1024物理运行或10000训练结果。
