# v21 公共支撑升降纠偏

承接[v20结构诊断](2026-10-14-m1-support-height-authority.md)：固定支撑世界Z把机身高度目标到支撑Z的响应抵消；实际机身下沉/COM边距恶化/抬轮冻结，不能继续单靠固定轮高。此前4env实测0成功，保留全部证据，生产训练关闭。

按用户“直接运行，自己许可”沿用inline连续实施，不重复审批。采用[规格](../../docs/superpowers/specs/2026-10-15-m1-support-heave-design.md)及[计划](../../docs/superpowers/plans/2026-10-15-m1-support-heave.md)：固定基准+零和载荷差分之外，三支撑共同项h；目标为负的机身高度误差变化，±.02m/.02m/s，初次capture误差消除跳变，RESTORE退零。活动腿/XY/PD/30N安全/真实经过与恢复不变。本次仅公共高度，不声称恢复roll/pitch全部通道或必然跨越。

## 当前实做

新增m1_teacher_heave.py纯函数及execution_targets可选support_heave_w_z[B]。19测试RED缺module→19GREEN1.32s；4active×2mode×2beta及非法输入共20RED后，连同v20/旧execution/load事务108GREEN4.88s，exit0。覆盖正负误差、初始无跳、幅度/速率、RESTORE、NaN冻结、shape/dtype/flag、三支撑同向且活动/XY不变、一次beta。

教师capture/commit/rollback/恢复及独立审核现已接入v21：初始事务3RED→4GREEN，新增证据9RED→9GREEN5.38s；相关整组622GREEN97.80s，后补11个契约/失败回滚/多行reset/RESTORE归零门槛用例使事务15GREEN4.30s，最终633回归进行中。仅/tmp候选，未新native、无生产训练。fresh最终review已派发；历史dirty/PT全部保留，无Git作者不伪造commit。

冻结v20实际帧114/130/150/180的数学敏感度：commandRootZ+1mm，v20支撑Z响应约0，新共同项使三个支撑各-.0004m（.02m/s×20ms）；新增贡献不改XY/活动腿。不是物理结果。初始脚本误要求全部几何XY响应0，已纠正为新增共同项贡献0，未改runtime迁就断言。原始数据和脚本保留。

Base04133e09c986595484801c6539f3e9415700389e加工作区修改，计划ledger `.superpowers/sdd/2026-10-15-m1-support-heave/progress.md`。物理跨越目标仍OPEN。

## 最终审核与启动

独立review未发现明确runtime缺陷，1Important为最终encode拒绝测试缺口，已补首次捕获/已有非零共同项两例，事务17通过。覆盖测试直接GREEN，不伪称修复runtime bug的RED/GREEN；既有提交位于最终编码门后。最终635相关CPU通过100.93s，5runtime双方SHA一致，gitdiffcheck通过。

2026-10-14T18:06:37Z（本地10-15 02:06）唯一隔离native已启动，runner328506/python328508，路径/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn/evidence-first-obstacle-support-heave-v1，first-obstacle/slow-rolling/load-feedback/4env seed101/真实10cm；启动前GPU1MiB且无训练/探针/pytest，kernel flock。尚未获得完成结果，不称成功，不改生产训练。

## 已写入的失败证据（总审核/进程退出尚待核实）

四路各143帧，env1–3同轨迹（非3独立随机试验），首次保护frame138：input137右后Fz27.683N低于30N，post138为14.627N；无碰撞/穿透，活动轮最大底高.00005272m（.0527mm），没有有效抬起/经过。heave生效24帧，最低committed-.003955m。env0未进入heave，随诊断边界中断；不能当完整课程。

同frame137/input136对比v20：新rootZ .5899109m，旧.5812246m（高度保持好约8.69mm），但新post RR27.683N，旧52.634N；不能称整体改善。COM余量新.0109069/旧.0149389m，combined_reserve皆0。新活动轮中心goal .0985943、solved .0955909，轮底仍贴地。

独立FK分解frame137新执行目标相对实测：活动轮Z-.658mm，FR -17.576mm、RL -10.776mm、RR -3.481mm；实际q FK与轮心约.2mm误差。不是简单的IK单位错误，也不能以各目标都向下推论载荷足够。最后物理子步computed/applied torque逐项相同，最大13.7625Nm，仅该子步证据，不宣称所有子步无饱和。

下一诊断聚焦姿态/差分支撑与真实载荷失衡；公共高度通道改善局部高度但未解决跨越，不继续盲加增益。failure-detail.json、tracking.json、v20-comparison.json保留于本计划workspace。所有已写episode verification.errors=[]且success=false/student_demonstration_usable=false；最终result/exit仍待收齐。

## 最终退出与归档

上述待核实已完成：exit0、328508退出/GPU1MiB。result FAILED_DIAGNOSTIC、complete_full_denominator=false、recorded/count4、complete3、locked3、stage3success0、duplicate0；停止源env1 frame138/physical_failure=false/errors=[]。这是教师保护失败，不是完整课程成功率。

完整视频/逐帧/source/config/log/exit/5runtime/3tests归档服务器/tmp/m1-support-heave-v21-evidence.tar.gz，本地计划workspace同文件，双方SHA d908da07501d54bd0304a30cc4e90adc30c7bd618b46297f6ba8baa11409b446。保留历史、不启动生产、不更改PD/安全线。下一查差分姿态支撑与真实载荷分配，目标OPEN。
