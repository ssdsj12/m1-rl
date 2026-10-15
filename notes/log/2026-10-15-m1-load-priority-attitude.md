# 统一载荷优先支撑调整：实施中

当前candidate修复已完成CPU针对性验证，正在修复后的完整回归，未启动native或生产训练。v23仍是最后完整物理结果（0跨越）；新数学不能称跨越改善。不要运行旧launch脚本。

设计见docs/superpowers/specs/2026-10-15-m1-load-priority-attitude-design.md，计划同名；ledger在.superpowers/sdd/2026-10-15-m1-load-priority-attitude/progress.md。

## 已做

- propose_load_feedback新增可选attitude_error_m，单一offset/速度投影。共用±15mm/.01m/s，保留活动接触力矩/45N目标；None保留原行为。
- 缺载轮和明显过载轮的修正方向受约束，进一步保留纯载荷可行解的最小修正幅度，避免姿态偏好抵消补载。二次位置投影也带相同约束。
- 纯姿态几何函数centered_support_attitude_error：相对旋转作用于轮相对body向量，三支撑去均值、活动轮0，处理无效行。
- 教师dynamic分支初步接入，e0仅成功事务捕获，恢复完成/reset清理；尚需完整生命周期和独立审核配套。

## 证据

分配器4个RED缺keyword断言后GREEN42，扩展至57通过9.05s；几何10个RED缺模块后综合67通过9.31s；事务捕获1RED/1已有PASS后15事务通过3.55s。测试包含相反姿态偏好下RR仍补载、边界、float32/64、4活动轮、250步序列、无效行、姿态几何yaw/translation/sign不变性。

## 必须接着完成

Task2拒绝事务/非零二次PIpass测试已完成；Task3上下文与独立标量复算、篡改负例已接入，runtime指纹升级support-ik-transaction-v24-load-priority-attitude。完整相关回归708通过116.72s。

最终独立审查无Critical，3项Important均复现后修复：原始姿态command未绑定整步重放（RED2）；float32两个零和误差之差可能超过1e-8引发异常（RED1）；独立审核double目标与runtime float32在15N门槛分歧（RED1）。修复分别为outer observer绑定完整姿态上下文、差值重构第三支撑项、标量target先按输入dtype舍入。针对性14通过8.07s；中间710通过118.81s不代表全部最新修改，最终完整回归日志另存/tmp/m1-v24-reviewed-full.log。

次要测试补强（直接比较载荷baseline幅度、已有e0的RESTORE结束清理）列入ledger，未因此放宽行为。审查不替代物理证明；**最终回归、SHA和GPU前置核实完成后才运行唯一4env原生**。新输出evidence-first-obstacle-load-priority-attitude-v1；禁止重用旧launch或生产训练。

全局Git身份缺失，保留未提交历史与本轮文件，不改全局配置、不删PT。用户直接执行授权持续有效。

## v24实测收尾中

最终712通过119.59s，4runtime SHA核对一致。唯一runner352737/python352739于2026-10-14T19:47:07Z启动，先核实GPU1MiB，无并发native或训练。输出candidate/evidence-first-obstacle-load-priority-attitude-v1。四路各136帧；env1–3同轨迹，非独立重复。单路审核errors=[]，env1–3 teacher_failure_locked，env0 diagnostic_interrupted，全部不可作为学生示范。汇总审核尚在运行，尚不声明exit0。

首次env1 input130右后Fz29.53047N；frame131保护锁停，输出右后2.16558N。此前无碰撞/穿透；活动轮底最大0.000050053m（0.05005mm）未有效离地。比v23 frame132提前1帧保护，不算改善。视频env1共29帧/10fps，抽查视频第26帧，未见跨越；本地保存env1-replay.mp4与video-frame26.png。

冻结同输入分配器对照（仅CPU算子，不是物理反事实）：actual attitude vs零姿态偏好、同raw/target/previous。frame117–127右后未触发weak，姿态项额外抬高当步proposal约0.01369→0.15452mm；frame127累计右后offset+1.1749mm。frame128才进入weak后姿态附加项归0，frame130 proposal仍+0.79475mm，随后input130载荷低于30N。说明历史收缩和判定时机值得继续诊断，不等于已证明唯一物理根因；不能盲加抬升/放宽保护。

下一步：汇总完成与归档校验后，冻结检查实际执行支撑目标、载荷变化和移重心滞后，决定如何让姿态修正考虑未来承载储备。跨越目标仍OPEN，无生产训练。

## 最终状态

汇总FAILED_DIAGNOSTIC，stage3_success0/complete_full_denominator=false；记录4、完整3、锁停3、duplicate identity0，首次frame131 failure_locked，physical_failure=false/errors=[]。原生exit0，python352739已退出，GPU回1MiB。完整证据包/tmp/m1-load-priority-v24-evidence.tar.gz SHA17e7f69f2431ca65e1d220345d077613c3bc27d2cd23ce9501418ed19c72c8dd；本地同名包校验后为收尾依据。控制及独立审计源码/RED-GREEN/最终712日志/四路视频与逐帧记录均保留。
