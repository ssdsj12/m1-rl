# Teacher 双支撑几何筛选设计记录

日期：2026-10-14 UTC；Stage：Teacher准备姿态候选；关联[T306](../todo/T306-m1-ame-long-train-stability.md)/actual-support-geometry-gap/candidate-retention。

用户已确认在固定锚点之外增加实测支撑三角形筛选，保持原IK、PD、包络和成功门槛。已将[只读调查](2026-10-14-m1-measured-support-selection-diagnosis.md)与独立审查转为[书面规格](../../docs/superpowers/specs/2026-10-14-m1-dual-support-selection-design.md)，待书面审阅后进入计划。

最新：用户已明确确认书面规格。writing-plans已开始只读接口梳理，随后用户要求优先上传当前快照到10-14；未产生实施计划文件，未编写或执行新控制代码。下方待审阅为此前状态；下一步是完成实施计划，而非重复设计审批。

- Baseline Ref：`b4b5f03756fa44af099ea80526ca230bb4f708a3`；Teacher runtime `39a6590`、verifier `de46186`未变。
- 方法：核对原候选选择/TeacherConfig fingerprint/probe schema，以及v4已冻结的969帧保持证据；本轮不重复原生测试。
- 设计：全部126候选使用同一个预测COM，同时满足固定锚点和当前实测三角形余量≥10mm；固定world IK目标不变，保留原代价与失败处理。只用于候选终点，不要求未完成插值已满足候选余量，不以预测代替真实ready。
- 证据：同帧身份与两种余量需新合同复核，拟Teacher implementation v9/probe schema7，旧记录不补造字段。
- 自审：目标/插值/真实事件分离；候选切换、反馈命令不可行、测量动态变化仍是风险；CPU可行不证明实际跨越。不加PD/力矩/额外控制机制。
- 当前结果：仅规格和notes更新，未runtime/服务器/训练变更，无新增native结果。Teacher A及BC/PPO仍BLOCKED。
- Next Step：用户审阅规格后编写实施计划，沿用测试先行、独立审查及GPU串行逐级验证。
- Key Files：本规格和四个notes入口；现有无关dirty修改、watchers和旧PT保留，不stage。
