# 原地/打滑双惩罚规格记录

- Purpose/Stage：T306/pure-ppo-learning 的 reward/stall-slip 子节点，关联timeout-without-crossing诊断。
- Baseline Ref：e45a007；Candidate Ref：本设计提交（无runtime代码）；Key Files：m1_required_crossing.py、m1_ame_rewards.py、m1_ame_env_cfg.py、ame_env_wrapper.py。
- 用户已确认双惩罚方向；[规格](../../docs/superpowers/specs/2026-10-12-m1-stall-slip-design.md)明确2秒/5cm、当前承重打滑和有界费用。
- Procedure：只读现有feet_slide接线与rolling residual，确认已有-0.1项且使用history接触最大值；当前改为替换而非重复叠加。
- Input：参考机器人v2/85与88state/12腿/固定轮.30/stage1–3；不引入动作控制。
- Result：建议原地上限.50/秒、打滑.25/秒、滑速容差.03m/s，dt积分；这些细化数值等待书面审阅。
- Verification：文档公式、单位、reset/terminal、阶段隔离、激励风险与验证范围自检；尚无新CPU或原生实现测试。
- Conclusion：设计方向确认不等于已部署；未改生产、未停止/重启训练；保留已有未提交监控notes和两个未跟踪watcher。
- Follow-up：审阅规格后writing-plans/TDD；安全GPU边界验证，显式同谱系奖励合同迁移而非从零训练。
