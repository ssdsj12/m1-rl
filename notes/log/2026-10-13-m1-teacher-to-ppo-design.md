# M1 教师预训练到独立PPO：设计审阅

Parent：[T306](../todo/T306-m1-ame-long-train-stability.md)。阶段：动作控制、示范学习、PPO交接；本轮仅设计，无生产修改/原生探针/训练启动。

## 输入与证据

用户确认教师预训练→撤掉教师→PPO，并明确不保留固定ABAD/固定轮速/8动作，随后确认16维全控制。此前碰撞每控制步2/累计20与fresh平地后直进10cm仍有效，但尚未部署。

参考锁定ssdsj12/m1 `8aeb845f73e39fd1e121758522ef05ee2378150f`：ContactFree默认sequential/IK且腿residual为0；PolicyPlay名字不能替代其policy_control=False的事实；m1_wave_distill使用监督模仿loss而非PPO探索。参考6cm固定场景成功不等于本项目10cm已通过。

本地只读确认 `ame_baseline/m1_ame_actions.py` 仍有16维MixedJointAction，12腿position/4轮velocity；`m1_ame_contract.py` 使用显式关节序与1.50rad腿尺度、轮半径速度映射。旧8维和固定轮配置不可直接套用为新动作合同；旧16维PT也不因维度相同就兼容。

## 结果与限制

[书面规格](../../docs/superpowers/specs/2026-10-13-m1-teacher-to-ppo-design.md)记录教师验收、行为克隆/学生状态再标注、完全撤除、critic校准及PPO接续；教师动作数据不进入PPO on-policy更新，最终actor不读教师phase或场景registry。

新节点 `T306/teacher-to-ppo` 替代当前纯PPO/固定动作方向，子节点teacher-feasibility → student-withdrawal → ppo-handoff顺序依赖。若教师不能跨越原10cm课程，不能假定模仿就能解决。原训练和自动监控保持暂停；本轮未现场复查play是否仍运行，不复述旧PID为当前存活证据。

本轮只进行源码阅读和规格一致性检查，没有运行CPU/原生学习测试，没有部署2分/步或16维，没有启动预训练。数值验收门槛是设计提议，待用户书面审阅。

## Git与下一步

- Baseline Ref：`7cd372c9ed8a123dcc3bc5d7b6f0d6085d370739`。
- Candidate Ref：本次design-only提交；不改变Last Feature/Verified代码ref。
- Key Files：上述规格与动作/合同源文件（源文件未修改）。
- 下一步：用户审阅规格后writing-plans；不得重启旧训练或把设计提交当部署。

## 2026-10-13 规格确认与实施计划

用户已确认书面规格。[实施计划](../../docs/superpowers/plans/2026-10-13-m1-teacher-to-ppo.md)划分为新合同/教师原生验收、模仿与无教师学生验收、critic校准/PPO交接三个串行里程碑。已定位真实代码入口位于ame_baseline而非参考仓库tasks路径；现有ActorCriticAME共享CNN/MHA且含BatchNorm，critic校准须同时冻结共享权重和统计量，不能只冻结actor head。

只读发现的接线风险已进入计划：runner在固定轮模式才保存旧action_contract，新16维须显式新合同；LearningCurriculumGate当前依次晋级0..4，新profile须保存(0,3)；CollisionBudget当前5*dt*signal，新profile须显式2*(signal>0)并保留旧模式以便历史诊断；旧get_mpc_teacher_action不得借此重新启用。

本轮只写计划并自查规格覆盖，没有运行测试/修改runtime/部署/开训。设计f58f1fd为本地提交；预存监控/诊断notes和watcher不纳入本次文档提交。等待执行方式选择，不重复要求批准既定路线。
