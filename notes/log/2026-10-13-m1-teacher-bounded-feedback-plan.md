# Teacher有界补偿：规格确认与实施计划

日期：2026-10-13。阶段：Teacher A前支撑准备；[T306](../todo/T306-m1-ame-long-train-stability.md)。

## 输入、目的与结果

用户使用using-superpowers并明确“确认”，已批准[补充规格](../../docs/superpowers/specs/2026-10-13-m1-teacher-bounded-feedback-design.md)中的Teacher轮速纠偏和虚拟位移细节。按writing-plans形成[四任务实施计划](../../docs/superpowers/plans/2026-10-13-m1-teacher-bounded-feedback.md)，不重复选择执行方式，沿用子代理。

任务依赖：纯反馈→双参考事务→实测证据→串行原生。逐项列出函数签名、张量形状/单位、RED/GREEN反例与测试命令、提交边界。代码接口只读核对：ReferenceTeacher、backtrack_reference、adapter、probe schema5及既有CLI；计划升级到schema6/fingerprint v8，不误称已经升级。

## 自审及检查

- 对照规格逐段映射；五类输入风险均对应具名测试。
- 修正双参考求解与真实decoder之间的依赖：纯执行检查回调逐beta验证，避免pose反向import Teacher，也避免解接受后再clip。
- 明确限轮速与slew无可行交集时拒绝，不择一违规；保留两遍×8档×2四腿IK上限。
- 文档相对链接和git whitespace检查；未运行算法CPU测试、原生仿真或训练，不将计划自审计作控制验收。

## 后续与边界

计划待用户审阅，随后按superpowers:subagent-driven-development实施。原生剩余一次单机制修订未消耗；教师A仍BLOCKED，BC/PPO/生产部署及自动监控仍不启动。todo、T306、notes入口及log索引已更新；无关未提交历史与watcher保持。

## Git refs

- Baseline Ref：c01bb8b（文档）；runtime Last Feature/CPU Verified：4f5a875。
- Candidate Ref：10-13计划文档提交；Last Native：de423a7，未重跑。
- Key Files：上述规格与计划、此日志及四个工作索引。
