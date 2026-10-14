# Teacher v3 同 GPU 后端复算

## 范围与引用

- 用户要求继续验证抬腿跨越成功。本轮只读定位上一轮证据阻挡，没有修改控制器、验证器源码、容差或物理标准，没有重新启动 Isaac/BC/PPO。
- Stage：Teacher feasibility / bounded-feedback / native-verifier。
- Todo：[T306](../todo/T306-m1-ame-long-train-stability.md)。原证据：[v3 原生记录](2026-10-13-m1-teacher-bounded-feedback-native.md)。
- Baseline / Candidate runtime：`39a659032239cdb87edf096b4efe1231d58b142a`；Current Work Ref：`efd38c846896d167c67b377c573235aef063f481`，分支 `10-13`。本轮不更新 Last Feature / 原生验收 ref。
- Key file：`Go2Pvcnn/scripts/probe_m1_teacher.py`，SHA `85ea5cfaeaf01a7e57611a27fcf6d7866f8665dc23ffb875fe87974341ace307`，与原生记录一致。

## 输入与程序

服务器 `root@a21495354824192000872439`，candidate `/tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn`。前后只读核实无 train/play/native probe，GPU0 均为 1MiB / 0%。生产目录不写。

输入为冻结 `m1-feedback-flat-v3/stage0_seed101_env[0-3]_episode0.json`。scratch 脚本只读取记录，导入未修改的 probe，清空数学 replay/decoder 缓存，以 `with torch.device('cuda:0')` 调用原 `verify_feedback_transaction`，并用 `sys.settrace` 捕获实际拒绝字段。默认设备只在离线脚本中生效，不进入任何原生仿真。未绕过 verifier、未扩大容差、未修改记录 verdict。

环境：PyTorch `2.7.0+cu128`、CUDA `12.8`、RTX4090、matmul TF32 false、float32 precision highest。这仅记录本次环境，不声称旧原生已完整记录全部数学模式。

scratch 文件保存在本地 `.native-probe-artifacts/m1-feedback-v3-20261013/diagnose_gpu_replay.py`（仓库外）及 candidate `.diagnose-gpu-replay-20261014.py`；最终 SHA `c86ba4f7aef9fb28673b4c90ccfc788c582937b4237aa6ed78e4bba3a4c23712`。

```sh
cd /tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn
PYTHONPATH=.:tests:rsl_rl /opt/conda/envs/env_issacsim/bin/python .diagnose-gpu-replay-20261014.py /tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn
```

第一次调用漏传 candidate 参数，脚本在导入 torch 前报 `IndexError`，未产生验证结果；补足参数后首/末帧抽查退出0，8个样本均无错误。随后改 scratch 为完整记录遍历并再次退出0。

## 实际结果

| record | 样本帧数 | GPU 事务复核失败数 |
|---|---:|---:|
| env0 episode0 | 49 | 0 |
| env1 episode0 | 54 | 0 |
| env2 episode0 | 54 | 0 |
| env3 episode0 | 54 | 0 |
| 合计 | 211 | 0 |

完整复算18.69秒；原始28个证据文件前后 SHA 全部相同。通过含原数值容差比较及 request decode→applied 的逐位检查；不等于所有数学输出逐位相同，也不是完整 episode verifier 或新的物理验收。peers 是相关并行行，不能当独立实验。

对照前轮 CPU：env0 41/49、其余各47/54事务复核失败；此次同 GPU 后端211/211通过。支持阻挡来自跨 CPU/CUDA 数学复算差异，而非这些记录的实执行链矛盾；尚未隔离到具体算子，不推广到未知轨迹。

## 结论和下一步

后续2026-10-14 UTC：用户已确认下述最小修复，`de46186`已实现并通过相关测试/独立审查；新v4合同通过，继续串行物理诊断。详见[显式后端实现与原生验证](2026-10-14-m1-feedback-backend-native.md)。下文“待确认”为该诊断结束时的历史，不再阻挡已批准工作。

原 v3 `FAILED_DIAGNOSTIC` 不覆盖、不追认通过；原准备只证明 env0 实际连续6帧ready，四腿准备、抬落、10cm跨越仍未验证，Teacher A 继续 BLOCKED。未产生示范/模型，所有历史 PT 保留。

建议最小有界修复仅在 probe 的数学复核入口显式选择与 producer 一致的后端，记录后端来源、按后端区分缓存，缺少相应后端时拒绝验收而非静默降级。保留真实动作 receipt 逐位核验及全部物理门槛，增加错误动作/伪造诊断负例；修复后新目录按准备→单轮抬落→10cm跨越顺序验证。该验证器行为变更尚未实施，按 brainstorming 有界设计流程等待确认；不需要重新设计控制器或重新审批原支撑设计。
