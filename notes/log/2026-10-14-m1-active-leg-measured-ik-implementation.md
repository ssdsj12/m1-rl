# 活动腿实测IK实施与实际10cm验证

- Stage: T306/actual-crossing/lift-load-redistribution/active-leg-command-frame。
- Baseline: 04133e0 + 已保留v14未提交候选；Candidate: v15未提交，仅隔离worktree/candidate，不改生产/BC/PPO。
- Plan/spec: [计划](../../docs/superpowers/plans/2026-10-14-m1-active-leg-measured-ik.md)、[规格](../../docs/superpowers/specs/2026-10-14-m1-active-leg-measured-ik-design.md)均获用户确认。
- Key files: `m1_teacher_execution_targets.py`、`m1_teacher_pose.py`、`m1_reference_teacher.py`、`probe_m1_teacher.py`及三个对应测试。

## 实现

LIFT/PASS仅活动腿按同决策实测root完整wxyz变换，支撑腿保持command body纠偏。执行目标由last_applied FK向分腿终点有界插值，最多8档、编码后仍<=2.5rad/s×dt；不硬裁剪IK结果。RESTORE全腿command目标仍走有界衔接，fraction未到1不能结束。无新卸载阶段、无PD/力矩/奖励修改。execution_单独记录目标/中间点/档位，最终两次抗饱和求解结果复算，不混成physical参考。

## 已执行验证

- 新目标模块缺失RED→33项GREEN；新teacher参数缺失RED→首批接线通过；旧probe不接受新动作RED→对应复算通过。
- 13文件相关CPU367 passed68.18s；另补6项换腿/断帧/单行reset/RESTORE测试后12项集成全过5.21s。最终合并回归待后续追加。
- 裸pytest:9 collection errors，pxr缺失及8个历史归档/根目录同名模块冲突；未删历史证据，不能称全库通过。
- 原v14 env0 frame165冻结CPU：终点世界Z117.145mm，旧下发FK82.400mm；新选beta1/8，下一步FK85.485mm、最大关节步长0.035327rad，向上但仍低于实测97.108mm。这是有限过渡，不能声称一步抬起。其他3行frame180同样beta1/8、0.039644rad；4行均两次反馈求解。
- 独立审查完成：1 Important独立几何验算缺口，生产/重放共同目标错误反例RED后，补直接坐标/FK/编码后残差审核；39项证据相关GREEN。Minor延后：强制首解/二次解不同beta的专门元数据替换测试；现有4冻结样本均两次求解且取最终结果。工作记录Minor在收尾同步。
- 最终13文件合并回归374 passed69.92s。2026-10-14T10:44:01Z确认无任务/GPU1MiB，runner277424启动`evidence-first-obstacle-measured-ik-v1`，4env/seed101/first-obstacle/slowrolling/1000步上限；原生进行中，不是训练。

## 参数与运行边界

既有FK/关节映射/16动作编码、DLS32迭代/2mm残差、PD、20ms/4亚步、碰撞与真实恢复标准不变。旧实际参数审计见[诊断](2026-10-14-m1-active-leg-command-frame.md)。新原生必须确认GPU空闲后串行，仅第一处10cm/4env/seed101/slowrolling。

## 后续

## 实际10cm初始结果与同帧定位

4路各123控制帧；env0 APPROACH60/BALANCE47/LIFT16，108帧首LIFT，119帧因SUPPORT_LOST(3)锁停，其他3路仍BALANCE而同批中断。零碰撞、无PASS/RESTORE/strict，不称4路均失败完成。env0推进0.096821m，目标轮底最大约0.0507mm，仍贴地。

同env输入/输出时序：frame118输出右后Fz26.98257N；frame119实际决策输入左前26.35775N、右后26.98257N，右后低于30N支撑门槛而锁停，不是碰撞或IK拒绝。左前最低输出23.7394N，未离地，不能称完成卸载。

修正后的实际命令确实消除了旧259采样共同的错误方向：frame112已beta1；frame114活动轮目标世界98.1456mm、编码后角在实测body下FK97.2868mm，实测96.9744mm；frame118目标98.4621mm/FK97.8096mm/实测96.3918mm。但前后对角载荷同时下降，抬升参考因支撑储备下降在约98.46mm停止，尚不足以离地跨障。frame114活动HIP目标-实测约0.100676rad，KNEE约-0.038221rad。所录最后子步最大腿effort约18.008Nm且computed/applied差0；不据此断言全亚步无饱和或必须调PD。

新的后续节点：actual-crossing/lift-load-redistribution/diagonal-support-loss-after-measured-ik。坐标分配修正已软件/同帧几何验证，真实支撑跟踪仍未解决；需以此次动作/力矩/载荷相位定位支撑纠偏与抬腿的动态耦合，不能放宽支撑门槛或盲加PD。完成记录认证与归档后停止本次诊断，不启动BC/PPO。

## 最终回执

2026-10-14T10:52UTC最终result为FAILED_DIAGNOSTIC，4 recorded/count、0complete、1locked、0success，complete_full_denominatorfalse；首次停止源env0/frame118实际support_lost，physical_failuretrue、errors[]。4记录verification.errors均空，不把证据通过当跨越通过。进程277426已退出/exit0/GPU1MiB，生产及训练未改。

四runtime本地/服务器SHA一致：execution_targets d359084ce5f97e38470f4ee79373633372b78e7644f09db829cf2c142eb3a135；pose 6f87b8e317cd209bbe45487cc0c964308f20c19ba6794962de1f65651359ed0d；teacher c0ee5468317b86aadc1d19da28470181741db3d3220bf9d200b71ec371201428；probe 293016ecccdb44133b1f7d5a56dfae0dd5f13258812d07bae1bf53d454879f26。候选源码tar双方4729a99e8d838508b64161afc73614a4506e1d54f154fc2f32b694c82d46c86d。

保留未提交worktree及SDD证据：Git身份仍无配置，未伪造作者/改全局Git/推送。相关374测试通过但裸pytest9历史收集错误，未合并或宣称全库通过。

完整证据归档`/tmp/m1-measured-ik-v1-evidence.tgz`已下载本计划SDD，双方SHA256 `1ac9994dbf292f9f53ac73e1346d3e5cb6907308b429ecc4d9c06696865789db`。包含4路视频/JSON/JSONL/result/exit、候选源码tar、冻结与实际同帧审计、相关及全库日志。env0视频另存SDD便于查看。执行器裁决：远程pytest保留命令与日志，未使用依赖本地环境的task-done包装；未配置Git身份故保留未提交工作树和证据，未清理。审查未评判的原生动力学已由本次失败诊断单独报告，不推断生产/训练资格。
