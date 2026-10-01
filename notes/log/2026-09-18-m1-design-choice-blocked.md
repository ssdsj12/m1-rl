# M1 后续行为设计等待确认

2026-09-18 23:36；T306.6h.6a.1a.2，关联首次几何子项 .1。本记录是阻塞审计，不是新测试通过或验收完成。

## 当前证据与决定

- 前一目标轮有实质进展：[首次几何源函数回放](2026-09-18-m1-scale-first-cross-geometry.md) 独立复核了 FAR 的 world 高度目标与 RAR 的 root/yaw 分量，并同步了记录。
- 同一待选条件已跨越三次连续目标轮：首次提出 [A/B 重入方案](2026-09-18-m1-scale-wave-reentry-diagnosis.md)；随后在等答复期间完成首次几何只读诊断；本轮仍未收到选择。自动目标续行不是用户对新设计的确认。
- 已有重入源码、几何、AME 生命周期只读审计不能替代行为方案确认。现有证据足以确定下一步需要设计/实现；重复同一检查不会解除阻塞，没有仍在运行的训练可等待。
- `brainstorming` 的设计确认门槛要求在修改行为前得到用户批准。目标已通过 `update_goal(status="blocked")` 标记为等待用户输入；完整目标不变，未标记完成。

## 本轮核验

通过 SSH 读取最新 dashboard/T306/重入诊断与当前进程、GPU7 compute-apps。23:36:33 仅见原占位 `python sleep.py` PID351307、15744 MiB；未见本任务 train_m1/reference/scale adapter 计算进程。未终止占位、未启动仿真、未修改源码或 SDK。

## 恢复条件与保留范围

等待用户选择 A（推荐）：首次有序跨越及恢复完成后记录同一障碍已完成，阻止再次抬腿，reset 清除；保留首次轨迹、保护和阈值，先 CPU 回归/审查再 8-env。B 仅推迟首次同步接管，不解决重复激活本身。两者均不自动修复 18 个首次跨越几何负例。

收到选择后从隔离设计、计划与验证继续，不重启旧失败候选、不用重启拼接 10000、不改分母。所有源码、负例日志、checkpoint、占位与已完成阶段证据保留。AME 接入、policy-only 小跨越/大绕行及单进程 10000 更新仍未验收。

Baseline Ref：formal646f486 / scale frozen Task3，repo HEAD5553e84；Candidate Ref：无新候选。Key Files：重入诊断、首次几何审计、[T306](../todo/T306-m1-ame-long-train-stability.md) 与已有 scale 计划。dashboard/branch/log index 同步本状态。
