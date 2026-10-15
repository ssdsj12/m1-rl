# 低速连续过障

T306/teacher-feasibility/actual-crossing/slow-rolling；当前用户确认低速接近、滚动中移重心抬腿、跨后恢复。旧停稳抓取/0.8m/s PASS不再是本次目标。

基线HEAD04133e0及未提交XYZ反馈候选；[上一轮实测](2026-10-14-m1-body-wheel-allocation.md)4×107无碰撞/无LIFT，不能当成功。当前仅隔离candidate，不改生产、物理PD、奖励、PPO。

按[短计划](../../docs/superpowers/plans/2026-10-14-m1-slow-rolling-crossing.md)实施：0.05m/s、0.10m/s²轮速斜率；前向滚动支撑参考共移、不吸收横滑/单轮漂移；实测三轮承重/碰撞/恢复检查保留。运行中安全拒绝仍停轮。保持历史配置可重现，探针显式选择新模式。

过程：先反例RED，再实现与相关回归/独立审查，直接实际10cm第一障碍；不重做独立支撑试验。1000步限时只作本次诊断，不足全程则明确部分证据，不擅自增加训练轮数。

## 实施与开跑 2026-10-14T08:06:43Z

- TeacherConfig显式slow_rolling，probe增加--slow-rolling；正常所有阶段轮面目标0.05m/s，斜率0.10m/s²，提前0.16m进入滚动移重心。
- prepared后将实测三支撑轮共同位移投影到锁定航向，只运输前向分量；anchor/anchor_pose/goal/accepted/support_origin同步运输。横向与差分滑移仍保留，IK失败不提交运输，重试只运输一次。capture及独立ready复算均比较相对滚动速度，不要求静止。
- 独立审查发现未ready持续滚动可能耗尽障碍距离，2项反例RED后补APPROACH_UNREADY明确保护：near_x余量耗尽且实测轮底仍未清障则锁停，不伪造碰撞/成功。正常状态不停轮。审查复查此P1已关闭；禁止slow模式与local诊断混用，CLI和teacher入口同时校验。
- 新16测试及相关六文件合计229passed/47.89s。此前扩展probe-contract整组因大型证据检查耗时被SIGINT结束，252passed/1failed（缺输出镜像字段的测试fixture，后已补齐并纳入最终229）；不声称全库通过。
- 本地/服务器teacher SHA ac4abb7afa8a21de9a6bc078936d521293f33f35fdd6a62abeb48e584dffbb2a，probe SHA b1a068e8ebab3642b000c3f333d159a66404dc6da7e13c5f034985f759f98a95。
- GPU1MiB且无训练/native/pytest后启动隔离first-obstacle/slow-rolling/1000steps/4env/video；runner252786，输出evidence-first-obstacle-slow-roll-v1。尚待真实结果，不是已跨越。

## 实测收尾 2026-10-14T08:14:06Z

实际四行各178帧，env0第108帧、env1–3第125帧进入LIFT控制阶段；此前停稳方案未到LIFT。轮面正常目标低速连续，实际根部X相对出生前进约0.146m/0.081m。**进入LIFT不是实际抬轮成功**：目标轮仍贴地承重，无PASS、RESTORE、receipt或成功。全程无碰撞/物理失败。

新的明确卡点是T306/teacher-feasibility/actual-crossing/rolling-lift-tracking-freeze：

- env0 frame112输入root对已运输accepted误差9.821mm，lift_age5；frame113增至10.535mm（XYZ +2.872/-2.319/-9.867mm），触发TRACKING，lift_age停5。目标轮accepted中心Z已到0.115185m，但实际轮底约0.000048m、Fz约52N，不能用参考高度冒充离地。
- env1 frame130误差9.205mm、lift_age6；frame131误差10.617mm（XYZ +4.265/+4.211/-8.763mm），同样冻结，轮底约0.000051m、Fz约42N。env2/3同类。
- env0 frame173实测未清障且接近余量耗尽，APPROACH_UNREADY明确保护锁停，frame178全批结束。其余三行是diagnostic_interrupted，不算自身已失败。没有“抬起来后摔倒”的证据；当前是参考跟踪冻结与实际未卸载/未离地。为什么载荷/高度动态跟不上仍需实际控制诊断，不擅自归因单一PD或放宽1cm门槛。
- 结果FAILED_DIAGNOSTIC：recorded/count4、complete1（完整失败记录）、locked1、stage3_success0、full_denominatorfalse；4条verification.errors均空。没有完整跨后恢复可验，既有时钟问题也不因此消失。
- 自然exit0只代表脚本结束，非跨越通过。08:14:06UTC再次核实ACTIVE_TASKS0/GPU1MiB，无训练/回放残留。

视频、原始JSONL、最终JSON/结果、source、runtime4与tests6已归档。服务器和本地同SHA：
`c0122ea2d8909c5bc27425032e4c89f95ba2b1bc0edadea02939eff10307115c`。
包名evidence-first-obstacle-slow-roll-v1.tgz，本地位于本worktree的.superpowers/sdd/2026-10-14-m1-dual-support-crossing-recovery；解包direct-crossing同名目录。env0视频已请求Codex打开，工具返回queued，不声称用户已看到。

下一步只围绕实际跨越内的机身跟踪与目标轮卸载耦合，保留本轮为对照；不返回单独抬腿支撑，不改生产/训练/PD/奖励，不以阶段标签当成功。低速控制代码及测量回归已验证，完整10cm跨越和跨后恢复仍OPEN。Baseline04133e0/原runtime02a70cf；Candidate为未提交隔离工作树+上述SHA，不更新Last Verified为物理成功。
