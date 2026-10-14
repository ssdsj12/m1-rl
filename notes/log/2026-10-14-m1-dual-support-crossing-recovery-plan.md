# 2026-10-14 双几何准备与跨后恢复实施计划

- Stage/Todo：T306/teacher-feasibility/dual-support-selection + crossing-recovery-outcome；日期UTC。
- Baseline Ref：ccbd00fb421e28810bd63594e04515552b07e764；Candidate Ref：本次文档提交。runtime39a6590/verifier de46186未改。
- 用户确认两份书面规格，包括0.3秒连续恢复与>=1cm实际净前进；沿用子代理执行选择。
- 输出：[实施计划](../../docs/superpowers/plans/2026-10-14-m1-dual-support-crossing-recovery.md)，5任务覆盖纯选择、同帧证据、纯结果监视器、探针生命周期、独立审查及新主机串行验收。
- 自审：同一预测COM/固定锚点、目标筛选与实际ready分离、15区间16观测、四轮圆柱远侧、原始终帧及sticky失败、正式A分母均有明确任务和负例。修正selector包装参数work为事务dict，非PoseReference。
- 验证范围：仅文档相对链接、diff和本轮精确暂存；不运行runtime测试，不声称物理修复或A通过。
- 新host root@a21506654554025984756592仍未连接核实；无服务器/生产/训练/显示变更，所有旧PT及dirty历史保留。
- 发布状态：本次仅本地文档；不把未push提交说成GitHub已更新。
- Next：按writing-plans要求交付计划审阅；通过后沿用子代理TDD及独立审查，不重复询问执行方式，不越过Teacher A启动BC/PPO。
