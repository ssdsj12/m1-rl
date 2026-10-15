# 三轮承载储备实施（进行中）

用户已确认规格与四任务计划；无需重复审批。仅 dual-support-recovery worktree 与服务器隔离候选，生产/BC/PPO未改。

## 已实现

- 独立三轮准静态载荷计算，排除活动轮，保留负份额，坏数值行隔离。
- 保守载荷标尺为当前正向力和与准备捕获值的较小值；成功事务才提交捕获，reset/结束清理。
- 125网格＋旧参考，原双几何/IK限制不变；双三角形预测最弱轮至少45N，优先最大化最弱载荷，再按动作成本/索引。
- BALANCE进入LIFT增加实测输入预测>30N；预测储备与原真实储备取min后推进高度。零预测储备仍允许有界移重心和低速前进，真实安全不放宽。
- probe增加独立标量方程审计，避免生产与重放共享同一错误自证；捕获原始力和身份、选择姿态均归档。

## 验证

纯计算18通过；候选及既有pose/dynamic72通过；控制接线与v15相关412通过（72.64s，probe最后修改前）。独立证据/旧动态证据20通过（8.69s），包括共同篡改生产预测的反例。当前最终相关回归与独立review进行中，尚未新native，不是跨越成功。

裸pytest collect-only仍9收集错误：缺pxr的test_m1_sdf_probe；reference_teacher、teacher_feedback、teacher_feedback_evidence、teacher_feedback_transaction、teacher_lift_decoupling、teacher_obstacle_hold、teacher_reference_commit、teacher_slow_rolling与历史源码归档同名导入冲突。保留历史、不删除；不能称全库通过。

## 执行记录与边界

计划工作区 .superpowers/sdd/2026-10-14-m1-tripod-load-reserve 保存brief/ledger/review包。Windows无Bash，使用apply_patch账本与远端CPU验证代替skill脚本；无Git身份，保留未提交差异，不伪造作者。

滚动测试夹具改为在rolling模式真正准备/捕获，不能用旧legacy准备后强行切模式再要求新储备存在。物理PD/力矩/0.05m/s/0.1m/s²/实际三轮30N/恢复标准未改。

最终相关回归417通过（74.16s），日志/tmp/m1-tripod-final-related.log；GPU核实1MiB、无native/train/play。审查进行中，未启动新原生。

独立审查完成：0Critical/2Important均实际反例复现并修复。成功恢复时原work.pop+row.update未删除旧捕获，现原子替换行内容且审核完成帧使用旧决策凭据；共同篡改lift增量可绕过仅reserve审核，现独立按原始高度/lead/ceiling/dt/rate重算并绑定requested轮高。2反例RED→GREEN，证据＋控制17通过（5.95s），最终综合回归重跑中。

排序独立性边界：独立标量审核验证选中候选双几何>=45N；全候选maximin/代价/索引排序仍由生产selector重放核对，不宣称独立全排序证明。该项Minor留待后续；单行reset及finish后不同载荷新目标重新捕获已补入Important状态生命周期修复测试。历史v15未重复全面审查，组合回归继续覆盖。

冻结旧teacher_input_frame108的preparation_input：总载荷396.892143N、份额[.489786,.462469,.0477446]、最弱18.949465N、新external_reserve0。历史18.85N取输出端快照，二者时间位置不同，不伪称同一输入数值。脚本保留在本计划工作区audit_frozen108.py，未改旧记录。

下一步：审查重要问题反例修复，核CPU与GPU安全边界后，直接第一处10cm障碍4环境1000步上限；保留完整视频/逐帧结果，未实际成功前目标仍OPEN。

## 原生实测启动

修复后420相关CPU通过（74.77s）；6个runtime/脚本本地与远端逐SHA一致，diff --check无错误。2026-10-14T11:50:04Z启动唯一目录evidence-first-obstacle-tripod-reserve-v1，runner289388，first-obstacle/slow-rolling/4env/seed101/1000步上限。启动前GPU1MiB、无train/play/probe进程。结果尚未产生，不算成功。

## 最终实测与复核（2026-10-14）

直接10cm first-obstacle / slow-rolling / 4env / seed101 已执行完，runner289388退出0，未启动生产或训练。每环境99帧；env0 APPROACH60/BALANCE39，其余APPROACH66/BALANCE33。四路均未进入LIFT/PASS/RESTORE，0跨越，failure_locked / invalid_teacher，不能用执行退出0或证据无错误称成功。

首个无效候选：env0输入89，诊断最优可行候选双预测最小载荷52.02497/44.57584N、IK残差1.39184mm；env1–3输入91为52.70227/44.98041N、IK残差1.99185mm。45N硬筛选排除了这些候选。低门槛搜索仅CPU诊断，未进入控制。不能将reason5直接解释为IK求解错误，也不能据此保证放宽候选偏好后必能跨越。

原native记录存在selected minimum独立审核误报：世界坐标float32量化与审核double预测COM不同（大约15微米ULP），差0.0025–0.00594N。实际冻结env1输入67反例RED后，仅审计把预测COM显式还原生产float32表示，再独立标量求解；未放宽容差、控制或45/30N阈值。原JSON/log不覆盖，独立复核另存。

最终相关421CPU通过75.16s。全4条完整record使用同cuda:0/torch/TF32设置复核errors=[]；env0 complete=true，其余false，全部success=false / invalid_teacher=true / failure_locked=true / student_demonstration_usable=false。complete只表示记录终止条件，不是跨越。复核报告/tmp/m1-tripod-full-reverification.json，包含原记录SHA和新probe SHA。

本地原始视频/JSONL/原JSON保存于.superpowers/sdd/2026-10-14-m1-tripod-load-reserve/evidence-first-obstacle-tripod-reserve-v1，未删历史。目标仍OPEN。建议下一设计将45N从硬候选筛选改为优化目标、保留实际30N保护及渐进储备，但尚未实施，需用户确认这一合同变更。独立全候选排序证明Minor仍延期；已执行的重要生命周期与共同增量审计问题均有RED/GREEN回归。没有Git身份，不伪造作者或提交。

后续归档核验：服务器与本地28个顶层证据文件逐SHA256全部一致，含4视频/4JSONL/4原始episode JSON；清单archive-sha-verification.json保留于本计划工作区。本轮未改控制规则，45N门槛调整仍待用户决定。

