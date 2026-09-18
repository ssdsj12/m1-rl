# M1轮式障碍奖励（用户已确认）

## 目标与范围

2026-09-18用户确认：将不适合轮式越障的腾空奖励替换为真实前进与随前进抬轮奖励。仅改M1 AME/AME-AMP共用环境，不改PPO/AMP算法、动作/观测维度、物理接触规则或失败终止。目标仍是amp、GPU4、1024环境、最终单进程完成10000更新，且小障碍跨越/大障碍绕行需要独立行为证据。

## 已知证据

旧1024×1000可完整结束，但障碍成功率0且后期策略塌陷。最新semantic1轮接触修正的1024×120也完整结束，平地8/8，小/大障碍仍0。固定姿态0.05m台阶四轮8/8、腾空奖励始终0；0.10m台阶固定姿态0/8。probe邻居串扰已单独修复，不再以该误计为理由放宽碰撞惩罚。

## 接口与数值语义

新增独立tensor模块`ame_baseline/m1_obstacle_rewards.py`，输入为当前命令、真实root/wheel LINK-origin运动状态及现有semantic scanner转换的地图。按M1链接名选取四轮，不能混用质心速度和link-origin位置。无跨episode缓存，无规划器调用。

1. 语义门：沿世界命令方向在每轮邻域及前方0.30m采样，必须是有效有限地图且有semantic1；任一轮邻域出现semantic2，整环境新奖励为0。命令速度>0.1m/s，姿态保持正立。
2. 真实进度：root沿命令方向的实际速度/期望速度，限制[-1,1]，0.02m/s死区。反向为负，侧移/停止/轮子原地自转为0。
3. 抬轮：扣除root平移与`omega × arm`刚体转动后，轮心必须真实向上且相对机身向上；速度上限0.2m/s。奖励再乘root与轮心的较小正向速度比，超过障碍顶面+轮半径+0.02m则不再奖励抬高；四轮均值。
4. 初始权重：progress1.0、climb0.5；旧feet_air_time/air_time_variance禁用。原geometry collision=-10、非轮部件接触、姿态、能耗、限位及滚动打滑规则全部保留。全体有限有效数据的Go2路径不改变；显式valid mask不能掩盖原始NaN/Inf是共同上游安全修正。

这些是局部密集引导，不是“已经跨过障碍”的成功计数，也不保证排除所有多步奖励投机。观察到振荡/冲撞或行为退化时应依据日志诊断，不把权重调大当作验收。

## 验证与后续

先tensor RED/GREEN（停/空转/原地抬腿、升降/俯仰、坐标旋转、semantic2、NaN/invalid、高度上限、body乱序），再配置与M1/AME/collision回归。一次只运行一个Isaac任务：8env物理信号探测、8env×2更新，随后fresh1024×120并进行固定flat/small/large评测。所有训练要求complete标志、退出码、精确iteration、finite checkpoint/TB；失败明确记录而非悄悄重启。仅在实际行为改善后进入10000轮长训。

实施步骤见[plan](../plans/2026-09-18-m1-wheel-obstacle-rewards.md)，状态与证据见[T306](../../../notes/todo/T306-m1-ame-long-train-stability.md)。不迁移到其他虚拟环境，不使用旧supervisor，不覆盖已有用户修改。
