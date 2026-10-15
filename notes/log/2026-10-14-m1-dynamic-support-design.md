# 动态支撑与实测抬轮方案

最新：用户已确认书面规格；[实施计划](../../docs/superpowers/plans/2026-10-14-m1-dynamic-support-measured-lift.md)已写并自审，待计划审阅后沿用主代理实施＋独立审查。覆盖纯算法、有限候选排序、原子状态提交、独立外层审计及直接10cm视频，不重复孤立支撑。当前仅文档；未测试/改runtime/连服务器。Git身份缺失未提交，Last Verified不变。下方待规格审阅是历史。

2026-10-14；T306/teacher-feasibility/actual-crossing/lift-load-redistribution。用户选择“动态支撑调整＋按实际运动推进抬轮”，承接[解耦实测](2026-10-14-m1-rolling-lift-decoupling.md)。

本轮只写[书面规格](../../docs/superpowers/specs/2026-10-14-m1-dynamic-support-measured-lift-design.md)，尚未实现/测试/服务器修改。新规格限定slowrolling LIFT/PASS：持续按实测载荷/COM重选有界机身目标；允许未满足旧1cm跟踪时的小步安全纠偏；轮Z参考受实际跟随及载荷/COM储备制约，不由帧数拉至最大。BALANCE/RESTORE、PD、包络、IK/碰撞/真实成功标准保持。

新增控制初值明确记录在规格，不把参数当已验证效果：机身/抬轮参考速率0.02m/s、Z领先最多0.02m、排序滤波0.10s、载荷30–45N与COM10–15mm连续减缓带。原始硬保护不滤波、不放宽。直接10cm完整诊断，不做独立支撑。三方案权衡已讨论，用户选择闭环调整，未选择单纯慢抬或改PD。

流程清单：上下文/失败链已读；非视觉选择，无需浏览器伴随；目的/边界与方案已获选择；书面设计已写并完成一致性/范围/占位自审；待用户审阅书面细化后写实施计划。Baseline04133e0+既有未提交候选；本轮无runtime/新native/训练，不更新Last Verified。
