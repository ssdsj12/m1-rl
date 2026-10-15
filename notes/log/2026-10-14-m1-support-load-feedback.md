# M1 v19 支撑载荷闭环实施与隔离验证

## 目的与范围

T306教师10cm实际跨越子节点。用户确认规格并授权直接连续实施。由三条支撑腿实测Fz反馈修正世界Z执行目标，保留30N实测保护、碰撞/穿透否决及真实经过、远侧落轮恢复。不启动生产训练，不删除旧PT与证据。

规格：[support-load-feedback](../../docs/superpowers/specs/2026-10-14-m1-support-load-feedback-design.md)。计划：[implementation](../../docs/superpowers/plans/2026-10-14-m1-support-load-feedback.md)。

## 实现

- 新纯张量载荷投影：支撑三轮总量，不含活动轮；目标每轮至少45N，低于135N或无效测量不推进。
- 增益.0002m/(N*s)、单轮.01m/s、幅度15mm、三轮零和；活动轮偏置0。
- 世界Z经实测root逆旋转进入执行IK，支撑容差.1mm。只完整事务成功才提交；拒绝回滚，RESTORE有界渐退至0。
- 默认load_feedback=False保留旧路径；原生显式--load-feedback --slow-rolling。
- 独立审核从原始载荷/三角形比例复算投影、历史偏置、回溯、实际下发q和执行几何，不以控制器自身日志当物理成功。

## CPU与审查

Task1最初19RED→19GREEN；Task2教师/IK10通过；证据9通过。增加比例来源篡改反例1RED后修复。相关回归534passed83.86s。

附加400步混合活动轮float32测试发现零和累积漂移1.0245e-8；积分后的偏置再次投影到同速率/幅度零和域，实际速度由增量回算。数值/审核30通过；随后535相关测试通过87.60s。

最终独立review发现1Important：回溯补偿被beta重复缩放。强制beta=.5反例RED显示.2mm提案实际仅.05mm，而提交.1mm。已改为执行goal使用完整proposal，body_step仅一次插值；attempted记录goal偏置、selected记录实际回溯偏置。修复后21相关测试通过5.83s；新增非零旧偏置与RESTORE覆盖，完整回归正在执行。

裸pytest收集仍9项错误（pxr及历史归档source-tests同名），3470项已收集，不称全库通过，不删除归档规避。

## 原生状态

最终回归538passed87.08s；5runtime本地与/tmp候选逐SHA一致，diff-check0。2026-10-14T17:06:22Z，GPU0 1MiB且无train/play/probe后启动唯一隔离runner314921，output=evidence-first-obstacle-support-load-v1，显式--load-feedback --slow-rolling/4env/seed101/first-obstacle/1000步上限。原生结果待定；候选/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn，生产未改。

## Git与未验证事项

## 原生最终结果与下一定位

2026-10-14 UTC运行结束：runner314921/python314923正常退出0，GPU0回落1MiB。result.json=FAILED_DIAGNOSTIC；4路计入、0完整跨越、3路锁定、env0同批中断。四路各135帧，最终审核errors=[]。首次物理失败env1/frame130，右后29.464361N、无碰撞；env1/2/3轨迹相同，不当三份独立随机验证。

env1共17个load反馈帧；活动轮最大底高0.000059485m（约0.06mm，仍贴地），最大偏置0.466861mm。第一反馈帧右后实载87.4725N、分配目标45N，正向偏置逐渐积累；到input129右后31.623N时虽向下修正，已提交右后偏置仍为+0.311559mm。最终实际下发q在同帧实测root下的轮心目标，相对实测FL/FR/RL/RR分别+2.461/-20.904/-15.122/+1.691mm；下一帧右后29.464N。反馈未抵消整体几何目标对弱轮的抬高，不能称成功，也不能单凭这组数据认定增益唯一原因。

最后记录的物理子步computed/applied effort差0、最大15.301Nm；FK与实测轮位误差约.20–.22mm。仅证明记录到的末子步，没有声称所有子步都未限幅。当前对照v18失败帧129到v19帧130，不作为显著稳定性改善。

完整原始四路视频/JSONL/JSON/配置来源及变更源码、测试归档：server /tmp/m1-support-load-v19-evidence.tar.gz；local .superpowers/sdd/2026-10-14-m1-support-load-feedback/m1-support-load-v19-evidence.tar.gz。SHA256 5505ae0f1bdf4296c862d6115460442fc54bcd04089b95e6e1b861416900c784。

子节点T306/teacher/support-load-feedback/geometry-compensation-conflict OPEN：弱支撑腿目标仍被抬高，实际载荷闭环与几何支撑目标冲突；后续从这次同帧证据修正，不再孤立试抬腿，也不放宽30N保护，不启动生产/BC/PPO。

Baseline/Current Work Ref：04133e09c986595484801c6539f3e9415700389e + 保留的工作区修改；Git作者缺失，不伪造提交。关键文件：m1_teacher_load_feedback.py、m1_teacher_execution_targets.py、m1_teacher_pose.py、m1_reference_teacher.py、probe_m1_teacher.py及三组load_feedback测试。

独立review未裁定原生稳定性/跨越/恢复、未复审全部历史v18修改；这些由本次隔离证据承担。CPU通过不代表学会或跨越成功。目标仍OPEN。
