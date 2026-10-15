# 机身XYZ腿部纠偏 / 阶段轮速分离

- Stage/Todo：T306/teacher-feasibility/actual-crossing/control-allocation。
- Baseline：HEAD04133e0及未提交capture衔接修正；失败anchor-X轮速候选已由本方案替代，旧归档保留。
- 输入：[上轮实际障碍](2026-10-14-m1-obstacle-anchor-feedback.md)4×182帧、未LIFT、3行在frame177碰障。共同轮速无法同时满足移重心/固定锚点/待抬轮不滚动。
- 方法/计划：[控制分工计划](../../docs/superpowers/plans/2026-10-14-m1-body-wheel-allocation.md)。用户确认直接实际障碍迭代，不重复独立支撑或规格审批。原有诊断数据和失败假设保留，不伪装已跨越。

## 设计与实现

XYZ位置误差都变为腿部IK虚拟机身位移，X采用已有YZ位置系数Kp.5/Ki.5、积分.01m/输出.02m/斜率.02m/s。新的BodyFeedbackConfig显式标记新单位；不把原X轮速输出m/s直接当位置用。所有阶段同一米制状态，APPROACH清积分并有界衰减，reset逐行清零。phase nominal/yaw轮速原样输出，移重心不再附加共同滚动纠偏。

固定支撑锚点、2mm双IK、.05rad/20ms命令限速、两遍事务及8次回退、真实COM/载荷/姿态/碰撞/恢复条件不变；不改PD/质量/地形/奖励，不进入生产或训练。Teacher fingerprint v11-body-xyz；probe重算使用相同新config/nominal轮速。历史证据必须使用归档旧算法，不以新版重算声称旧版通过。

## 实施台账

- Task1反例：root前偏.03m、轮保持原锚点；旧代码虚拟X不变，RED在accepted_command.X断言失败。新方案虚拟X负纠偏且轮命令0，physical进度仍由实测决定。
- 首轮针对性测试77通过/8失败：旧轮速反馈和旧单位预期不再适用，逐项改为新控制分工；第二轮128通过/1失败来自把诊断out.valid（不能作训练标签）误当reference_valid，已改为独立reference_valid断言，不放松执行验证。
- 决定：用户要求实际跨越优先，本轮不重新跑独立flat-preparation/single-wheel；仍保留小反例、相关回归、一次只读代码审查和同10cm场景串行验证。若假设失败则记录，不叠加放宽成功门槛。
- 相关测试、审查和原生结果待以下追加；未提交/未上传/未部署生产，禁止把候选等同完成。

## 回归与实际试跑（UTC）

- 扩展回归首次205通过/6失败，HEAD同6测试全部通过。定位捕获时保留过期world accepted会冻结刹车后的跟踪；修正为当前measured body + FK(last_q)，保留上一执行关节几何，实际wheel_anchor仍实测，branch仍实际q。loaded-q跳变反例保持通过，4个阶段计数回归修复。
- 剩余2个坐标平移测试漏移com_pos_w；诊断显示虚假COM偏移近100m。补齐质心平移，并加强为两边必须valid，避免旧版本“两边都拒绝”造成虚假通过。
- 独立只读审查无Critical；发现无context证据验证还用旧X界限，新增2反例RED后改用cfg.feedback，文档同步XYZ米制。capture追加审查无新Critical/Important。
- 最终5文件相关CPU：213 passed in 45.11s。只声明相关测试通过，不声明全库或物理跨越成功。
- 2026-10-14T07:16:54Z启动实际first-obstacle 10cm、4env、1000步上限、视频试跑；runner241214，输出evidence-first-obstacle-body-xyz-v1。启动前GPU1MiB且无train/native。4个变动runtime本地/服务器SHA逐项一致；生产/BC/PPO未动。

## 实际结果：仍未跨越，不作成功发布

- 最终4×107帧；phase只有APPROACH/BALANCE，LIFT/PASS/RESTORE及实际跨越receipt均0。env1–3第98帧首次无可行候选，第102帧5次拒绝后锁定；env0在第107帧同批中断，不把它记成自身失败。
- result：FAILED_DIAGNOSTIC、recorded/count4、complete3、locked3、stage3_success0、complete_full_denominator=false；物理failure=false、无碰撞，非抬腿后摔倒。完整失败记录不是完整过障成功。
- env1第97帧输入：支撑轮1/2/3相对固定锚点X约-8.80/-36.34/-22.22mm，Y约-9mm；四轮仍承重。第94帧输出横向速度约-.203m/s，不能将零轮关节目标等同轮中心静止。
- CPU只读重算原始selection_context：所有126候选（含几何包络外项）的实测支撑三角形最大margin，frame97为10.51456mm、98为8.74297mm、102为3.58615mm。即第98帧任何候选均不足既有10mm要求；不是只看返回的失败候选，也不是数值打印0造成误判。
- 本轮控制分工解决了软件层面X纠偏驱动共同轮速，但不能宣称已解决实际支撑漂移。仍有机身过冲/支撑轮实动；父连杆运动与轮关节零速、制动跟踪之间的贡献尚需分解，不能直接认定单一因果。下一步仍在完整10cm障碍场景修正支撑轮运动/机身阻尼，不重做独立抬腿夹具，不放宽成功门槛。
- 原生自然exit0；07:23:31Z现场ACTIVE_TASKS=0、GPU1MiB，生产/训练未改。保存4段视频、原始trace、结果、对应4runtime/5tests及log/exit。
- 归档：evidence-first-obstacle-body-xyz-v1.tgz，本地和服务器SHA256均e5eb0b3b2d3a2a19a80700b374b454d387964651ae332f6fe18f56f46ff4c47a；本地位于.superpowers/sdd/2026-10-14-m1-dual-support-crossing-recovery/，已解包direct-crossing/。候选仍未提交/上传/生产部署。
