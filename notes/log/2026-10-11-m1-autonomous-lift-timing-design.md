# 自主抬落时机：2cm语义纠正与设计

Parent [T306](../todo/T306-m1-ame-long-train-stability.md)，
pure-ppo-learning/autonomous-lift-timing，关联attempt-failure-trace。

用户明确“提前2cm”是水平接近距离，而非竖直抬高2cm；确认不固定起抬距离，
让PPO自行学习时机。先前把竖直2cm门槛当成用户要求的解释错误。

只读检查dynamic/strict crossing、wrapper调用及required_crossing奖励：
`.25`是遭遇范围，`.02`竖直门槛驱动early_lift/失败/落轮资格；奖励`/.02`
仅为尺度。小增量实际已可获奖。历史teacher时序测试不是当前纯PPO行为。

[书面规格](../../docs/superpowers/specs/2026-10-11-m1-autonomous-lift-timing-design.md)
记录stage1–3取消2cm预抬硬前提、安全的障碍前抬落探索，独立保留支撑、
重叠3cm净空、远侧落轮和稳定恢复。奖励尺度/预算、stage0/mixed4保留。

状态DESIGN ONLY：未改运行源码、未停训、未启动probe、未运行新合同测试。
本轮没有现场轮询训练；最近核实仍见[700后续训记录](2026-10-11-m1-prelift-failure-trace700.md)，
不将历史701–702当本轮最新迭代。书面审阅后再计划/TDD/验证/安全部署。
env283真实失支撑证据保留，不因删2cm而算成功；物理失载原因与学习均OPEN。

Baseline Ref:b244024；Last Feature/Verified Ref:6960a4b（本次无新增运行验证）。
Candidate Ref:本次设计提交，非运行实现；Current Work Ref:codex/m1-ppo-repair-upload。
Key Files:规格、dynamic/strict tracker、wrapper、required reward。
保留既有未提交notes和未跟踪watcher，不纳入本设计提交。
