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
