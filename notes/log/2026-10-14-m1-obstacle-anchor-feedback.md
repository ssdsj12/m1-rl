# 10cm障碍内支撑锚点纵向反馈诊断

- Stage/Todo：T306/teacher-feasibility/actual-crossing/support-anchor-drift。
- 基线：04133e0文档/02a70cf runtime，加上一轮未提交capture衔接修正。
- 用户要求：直接完整接近、抬轮经过、落轮恢复；不反复单独支撑/抬腿验证。最新要求覆盖旧准备门禁顺序，正式成功仍须实际完整事件。
- 输入证据：`evidence-first-obstacle-capture-bridge-v1` env1 frame40–97。支撑参考固定，机身前移误差触发四轮负轮速目标，frame70共同轮面纠偏-.0324323m/s；后支撑轮移动约3.5–4.8cm后，候选实测三角形最高margin从10.83降至8.69mm，无可行抬腿目标。不能仅以这些汇总断言纠偏是所有轮位移的唯一原因。

## 本轮单变量假设与候选

BALANCE移重心时，机身X误差和支撑轮锚点X误差不是同一目标。现有共同轮速PI按前者驱动，可能主动移走固定支撑三角形。候选仅将BALANCE的X反馈改为三个支撑轮相对固定锚点的heading-X平均误差；YZ仍为机身误差，原增益、积分/幅度/斜率、IK、关节限速、支撑门槛不变。APPROACH/LIFT/PASS/RESTORE行为不在此修改范围。不是机械锁轮，不保证无滑移；需原生同场景对照。相比盲增摩擦/PD或放宽COM门槛，此实验只改变导致轮滚动的误差信号；若无效，保留反例，不叠加大幅参数修改。

本轮按用户明确“跨越中出问题修改”采用小反例→实际完整障碍流程，省略新的长篇前置规格/全套门禁循环。没有开始BC/PPO。

## 验证与运行

`test_balance_longitudinal_feedback_holds_support_anchors` 先旧代码RED：轮子未移位仍倒转、轮子后移时纠偏方向仍向后；另一个正向偏移负纠偏用例原已通过。改后reference_commit/feedback_transaction/feedback_evidence三个文件84 passed in26.27s，非全库通过。探针原始context新增控制阶段/目标轮/固定锚点/实测轮位供同算法重算；Teacher fingerprint改为v10-anchor-feedback，旧结果不能称新版本验收。

2026-10-14T06:44:36Z确认无任务/GPU1MiB后启动4env first-obstacle、1000步上限、10cm、录制视频，runner227606/python227608。路径 `/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn/evidence-first-obstacle-anchor-x-v1`；直接完整障碍流程，未独立跑flat-preparation或single-wheel。源码SHA：Teacher `b4aa56417e3ee7c0f95f77ff90c2fd88517fb19c79860e98a573328bf84799e7`，probe `3c13ea69d167d0ddb3d5998d4eda8098bc4e4473e63f375ba2e7caa84e61e3ed`。生产、训练PT、物理、奖励未改；历史callback时钟证据问题仍未解决，不据此签发A成功。

## 实际障碍结果：本候选未解决跨越

截至06:50:32Z原始记录每行182帧，均只有APPROACH/BALANCE，没有LIFT/PASS/RESTORE或receipt。env1–3首次碰撞在输出frame177、锁定在下一次决定；env0没有碰撞/锁定，因同批失败结束观察，不写成它独立失败。末端文件重算尚在运行，此时不声称完整退出。

与上一轮不同，本轮未先发生候选几何拒绝，而是参考跟踪停住：env1 frame177接受机身X=-25.720356，实际X=-25.698133，误差22.22mm，超过10mm跟踪界限；body_age停在10，尚未完成侧向移重心。三个支撑轮锚点平均X误差10.48mm又使共同轮速正向纠偏15.04mm/s，连待跨前轮也一起驱动，随后遇到障碍。此时四轮Fz约121.7/109.2/94.0/77.8N，未出现先抬腿再失载摔倒。不能把碰撞笼统归咎于学不会或奖励。

因此“只换共同轮速PI的X误差信号”不足：保住支撑锚点、移动机身重心、停住待抬前轮是不同控制目标，共同轮速一个通道无法同时满足。本候选只能作为失败对照，不能称修复成功或发布为生产改进。下一步应针对实际过障中的腿部机身跟踪与轮滚动分工，不再独立重复支撑/抬腿试验，也不放宽成功或物理门槛掩盖问题。局部capture衔接反例修正与此未成功的控制假设分别保留证据。

## 收尾核实

06:53Z原生进程自然退出0，result为FAILED_DIAGNOSTIC，recorded_episodes4 / counted4 / complete0 / locked3 / stage3_success0，完整成功分母false。不能把4份闭合视频/日志或进程正常退出说成4次完整跨越。现场ACTIVE_TASKS=0、GPU1MiB，无遗留训练/原生任务。所有四份mp4及原始帧、episode、source/imported modules、result、log/exit归档已下载，双方SHA256一致：

- 归档名：`evidence-first-obstacle-anchor-x-v1.tgz`。
- SHA256：`9de2f15b29f516cc527acca2f7c3077a874912be7137ff3435b723a5c42d0a06`。
- 本地：本worktree的`.superpowers/sdd/2026-10-14-m1-dual-support-crossing-recovery/`，解包在其`direct-crossing/evidence-first-obstacle-anchor-x-v1/`。
- 本轮小修和反馈假设保留为未提交候选，未合入生产、未启动BC/PPO、未上传GitHub。生产成功门槛未放宽。后续不得仅凭84CPU通过部署这个失败候选。
