# 固定轮速与12维腿PPO：设计核查

Parent [T306](../todo/T306-m1-ame-long-train-stability.md)，
pure-ppo-learning/fixed-wheel-leg-only OPEN，关联steering-feasibility/checkpoint-migration。

用户确认轮子固定前进、PPO只管腿，小障碍跨越、大障碍由腿动作避让；拒绝偷偷保留轮速决策。
[书面规格](../../docs/superpowers/specs/2026-10-11-m1-fixed-wheel-leg-only-design.md)待审阅，未实施。
候选固定速度0.30m/s是建议，不冒充已批准数值。

只读检查当前actions/contract、m1_kinematics、actor_critic和runner：
当前16维含轮速输出；FK仅ABAD-X和HIP/KNEE-Y，没有独立yaw转向关节。
因此纠正先前“腿调整轮子朝向即可绕行”的过度简化，腿部接触动态避让能力仍OPEN，
并未证明绝对不可能。12维模型需显式选取旧300腿输出行/std/optimizer状态，不能直接载入16维PT。
当前环境已保存配置前进目标0.18–0.45随机，未固定实际轮速；未来恒速目标不保证机身位移。

本轮仅设计与文档；无训练停启、生产修改、native、网络或PT删除操作。
先审阅书面规格后规划，仍遵守用户长训优先，不以未学会避障作为初始开训门槛。
Baseline/Current HEAD80818c3；Feature/Verified仍c7ed76f；分支codex/m1-ppo-repair-upload。
Key Files：m1_ame_actions.py、m1_ame_contract.py、actor_critic_ame.py、ame_runner.py、规格。
