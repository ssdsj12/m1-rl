# 三轮承载45N软目标实施

用户确认后，沿用隔离worktree/candidate，未触碰生产训练。前版4路BALANCE筛选失败的原始证据保留。

## 已改

choose_support_pose载荷候选默认严格>30N，仍按最弱载荷maximin、动作成本、索引选择。45N仍对应满抬腿储备，30–45线性，30及以下不增轮高。实际承载、IK、几何、速度、PD、碰撞及恢复条件未改。指纹v17隔离旧记录。独立审核候选底线同步30N（原数值容差不变）。

## 实际验证

合成42.9N可选反例先RED；冻结原env0/input89真实帧先RED无效事务。控制修改后事务有效、候选44.57584N，但旧审核仍报below45，第二RED；审核同步后424相关CPU通过75.66s。首次远端shell退出变量转义错误，pytest自身输出明确通过但wrapper exit1，因此正在使用单引号here-string重新跑完整相关测试取得正确退出码。

裸pytest9收集错误4.01s：test_m1_sdf_probe缺pxr，其余reference_teacher/teacher_feedback/teacher_feedback_evidence/teacher_feedback_transaction/teacher_lift_decoupling/teacher_obstacle_hold/teacher_reference_commit/teacher_slow_rolling与历史归档同名冲突。未删历史，不称全库通过。

本地/服务器三个变更文件SHA逐项匹配：pose4c304cda、teacher67c227b8、probeffa00fb6。独立审核进行中，新原生尚未执行，不宣称跨越成功。计划与rulings在.superpowers/sdd/2026-10-14-m1-tripod-soft-target。

最终相关424pass75.52s、正确shell退出0。独立审查0Critical/Important，Minor默认恰好30N边界fixture留后续（显式99等号已覆盖严格比较）；未独立重复全套CPU、不静态判物理成功。源码快照/tmp/m1-tripod-soft-v17-source.tar.gz SHA16e3ccbb869c5112e712f1f84da077ab44c4a383feab0678a4aab07add486db1本地保留。

2026-10-14T12:27:26Z：GPU1MiB/无并发train/play/native后，唯一evidence-first-obstacle-tripod-soft-target-v1启动runner298788，4env/first10cm/slowrolling/1000步上限。结果待实测，不算成功。

## 最终结果

runner298788/python298790退出0，GPU回到1MiB；result FAILED_DIAGNOSTIC，4record/0complete/0success，3locked。原生完整审核全部errors=[]，但不是跨越成功。env0仍BALANCE；env1–3于输出frame114进入LIFT，至137共有24个LIFT标签，只有19有效决策；目标轮底最高0.00006161m，未真实抬起。4路collision帧均0。首个物理失败env1/input132，support_lost；该输入右后Fz26.15175N，前一输入33.47820N，后续停下读数28.25N不可混作首因。无需降低30N保护。

同env/input113进入LIFT时当前准静态最弱47.42688N，选中目标双几何最弱36.74813N，dynamic reserve却1，轮高命令增量.0004m；按选中目标的30–45线性储备仅.449875（对应上限.00017995m）。19有效LIFT中13帧目标储备比当前进度储备更低。输入113→132右后实载87.47253→26.15175N，目标轮仍贴地。支撑目标预测及实际动态跟踪共同影响尚需定位；该算术反事实不证明减慢抬腿即可成功，不擅改保护/PD/训练。

整组视频/逐帧/原JSON/log归档/tmp/m1-tripod-soft-v17-evidence.tar.gz，SHA479051d18d72527da7f16a80f2b13647e450d71b221d9e0399e363ba7b53b60b。源码快照与审查rulings另存本计划工作区。目标仍OPEN，已批准45→30候选修改已完成，不重复该审批。后续重点为当前姿态与新支撑目标共同约束抬腿推进以及实际执行误差，尚未实施第二控制变更。
