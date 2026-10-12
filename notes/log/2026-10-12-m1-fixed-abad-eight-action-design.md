# 固定ABAD、8维PPO设计记录

最新：用户已确认书面规格；[实施计划](../../docs/superpowers/plans/2026-10-12-m1-fixed-abad-eight-action.md)已完成自检，等待计划审阅。沿用“当前镜像内逐项执行”选择，不重复审批方向/模型。6任务覆盖动作、历史、迁移、入口时钟、原生、部署；未改runtime/启动训练。

- Purpose/Stage：T306/pure-ppo-learning/action-contract/fixed-abad，关联空地策略退化，非已证实根因修复。
- Baseline Ref：83aa11d（GitHub10-12已独立核实）；Candidate Ref：本规格提交；Last Feature/Verified仍6d90e80。
- Input：用户选择固定ABAD目标0、8维HIP/KNEE，最新“直接从200pt开始续训”覆盖此前从零。
- Procedure：只读动作展开/16列历史、85/88观测、runner合同和checkpoint迁移；将200来源与按关节裁剪Adam明确写入规格。
- Key Files：[书面规格](../../docs/superpowers/specs/2026-10-12-m1-fixed-abad-eight-action-design.md)。
- Result：架构级规格已写；新合同/策略未实现，训练保持停止。固定目标不保证绝对直行，大障碍绕行和平衡有损风险保留。
- Verification：文档自检来源、维度、状态保留、加载拒绝、安全部署和评价时钟一致性；未运行新CPU/native，不宣称实现通过。
- Follow-up：先书面规格审阅，再writing-plans与执行方式选择；不重复询问已确定的约束方式或模型起点。
