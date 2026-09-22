# M1 AME 跨越任务对齐设计

## 目标

将原 M1 项目的语义障碍物跨越任务迁移到 `m1_rl` 的 AME 环境，同时保留 M1 的 16 维动作、12 维 planner/reference 状态、M1 link/joint selector 和 semantic scanner。训练日志和 checkpoint 评测必须使用可比较的跨越率定义。

## 状态机

每个环境维护独立的 crossing state：`NO_OBSTACLE`、`APPROACH`、`FRONT_AXLE_CROSSING`、`REAR_AXLE_CROSSING`、`COMPLETED`、`FAILED`。状态转换由 semantic obstacle candidate、四轮相对障碍物位置、轮底 clearance 和 termination 信号决定。semantic large obstacle 不进入 crossing state machine，而进入 avoidance 统计路径。

## M1 参考动作与奖励

当前跨越阶段只对目标轮提供 M1 顺序抬腿参考，其余轮保持正常步态。轮底目标 clearance 为障碍物顶部上方 5--10 cm；轮心计算显式包含 `M1_WHEEL_RADIUS_M`。Teacher ratio 在训练进度中从 0.30 衰减到 0，后段为纯 PPO。

## 统计

环境逐 episode 记录 `semantic_candidate_episodes`、`semantic_crossing_episodes`、`crossing_failure_episodes`、`crossing_collision_episodes`、`large_obstacle_candidate_episodes` 和 `large_avoidance_episodes`。TensorBoard 写入 `Metrics/semantic_crossing_rate`、`Metrics/semantic_candidate_rate`、`Metrics/crossing_failure_rate`、`Metrics/large_avoidance_rate`、`Metrics/lift_phase_rate` 和 `Policy/m1_teacher_ratio`。无有效 candidate 时显示无样本，不写 0% 假成功率。

## 评测接口

`m1_checkpoint_eval.py` 的评测口径迁移为 M1 AME evaluator，支持 `--semantic-crossing`、`--obstacle-threshold`、`--min-crossing-rate` 和 `--disable-crossing-reset`。评测固定障碍布局、障碍尺寸、速度命令和 episode 时长，并输出跨越、无碰撞成功和大障碍绕行指标。

## 验证顺序

先运行纯逻辑状态机测试，再运行 8-env runtime smoke，随后运行固定障碍评测 smoke；全部通过后才恢复 1024-env 长训。训练 checkpoint 不与评测脚本共享可变状态。
