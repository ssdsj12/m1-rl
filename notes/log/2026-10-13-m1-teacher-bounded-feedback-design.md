# Teacher有界跟踪补偿：设计审阅

日期：2026-10-13 UTC。阶段：Teacher A前的支撑准备；关联[T306](../todo/T306-m1-ame-long-train-stability.md)。

## 输入与目的

用户选择第一种Teacher有界补偿，非动力学力矩前馈。[前次调查](2026-10-13-m1-support-tracking-diagnosis.md)确认机身位置误差仅门控参考推进；承重静差是有证据支持但未完整证实的假说。

## 本轮输出

形成[书面规格](../../docs/superpowers/specs/2026-10-13-m1-teacher-bounded-feedback-design.md)：X误差经四轮共同小幅轮速纠偏，Y/Z经有限虚拟机身位移和既有IK；保留物理名义参考、原PD/物理/成功门槛。Teacher退出和学生阶段完全撤除。新轮速纠偏及具体数值仍待用户书面确认，未当作已授权执行。

## 自审过程与结果

检查坐标单位、名义/虚拟/实测分离、积分反饱和、拒绝事务、阶段退出连续性与原生试验预算。补清：slew只认证真实执行解；积分回退至多重算一次，总计算上限2遍×8档×2个四腿IK；APPROACH只衰减旧补偿不新增长误差反馈。

本轮仅文档，不运行CPU算法测试、原生仿真或训练。文档校验为相对链接存在及git whitespace检查，不等于算法或物理验收。既有教师A仍BLOCKED；保留剩余一次原生修订预算，禁止未确认就消耗。

## 后续

用户审阅规格，随后writing-plans形成实施计划，再按既有子代理约定执行。先CPU/独立审查，再串行原生逐级验证；BC/PPO不启动。notes入口、dashboard、T306和log索引同步本轮状态；旧混合未提交记录不整体stage。

## Git refs

- Baseline Ref / Last Feature Commit：4f5a875。
- Candidate Ref：10-13设计文档提交；runtime不变。
- Last Verified Commit：4f5a875（既有CPU证据，非本轮重跑）；Last Native Ref仍de423a7。
- Key Files：上述补充规格、调查日志、本日志和工作索引。
