# M1 本次提交相对既有版本的改进

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref: e4c0b9a. Candidate Ref: containing commit.

## 本次代码增量

- 新增四足支撑滚动对照：60 帧稳定、20 帧有限加减速、20 帧停车。
- 新增窗口速度单元测试；窗口外速度严格为零。
- 增加实际轮速度、目标速度、估算驱动扭矩及 PhysX 关节限位诊断。
- 阻尼 5/20 对比仅限显式开启的诊断，不改变生产训练默认参数。

## 与前面改进的关系

此前提交已加入接触驱动单腿抬升、受限下降与稳定落足门槛、实测轮包络越障门槛、滚动加速度限制。历史平地八环境抬升及稳定落足证据见
[SETTLE 验证](2026-10-07-m1-settle-contact-persistence.md)。这些结果不等于实际障碍跨越成功，也不是新训练好的策略模型。

## 验证

- 本次复跑：`python -m pytest tests/test_m1_rolling_speed.py tests/test_m1_support_effort.py tests/test_m1_effort_guard.py -q`，20 passed，1.53 s。
- 四支撑诊断原始记录：`/tmp/m1_four_support_roll_20261007.log`、`/tmp/m1_four_support_gain20_20261007.log`。两组均完成 100 帧；先前分析记录表明阻尼增加没有恢复有效前进，不能宣称驱动问题已解决。
- 限位记录：`/tmp/m1_wheel_limits_20261007.log`。本次读取的八环境四轮 PhysX 限位均约为 ±3.402823e38，不支持“轮关节被有限位置范围锁住”的假设。
- GPU7 占位进程已恢复，核实 PID 2011308；本次没有启动训练或修改显示配置。

## 未完成与上传边界

有效前进、实际障碍顶部净空、远侧落足、无碰撞连续跨越仍需物理验证。不能将命令位移、平地抬升或日志输出当作跨越率。下一步继续有效滚动根因排查，不盲目增加增益或放宽验收。

仅上传独立 `codex/m1-contact-crossing` 分支，保留原工作目录修改；不包含 checkpoint、私钥或原始运行日志。Git push 成功与否以服务端结果为准。
