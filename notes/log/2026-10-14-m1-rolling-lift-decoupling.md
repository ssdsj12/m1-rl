# 滚动抬轮进度与机身纠偏解耦

2026-10-14；T306/teacher-feasibility/actual-crossing/rolling-lift-tracking-freeze。用户明确“实施”，执行[短计划](../../docs/superpowers/plans/2026-10-14-m1-rolling-lift-decoupling.md)，承接[逐帧定位](2026-10-14-m1-rolling-lift-gate-diagnosis.md)。

## 范围与合同

只改隔离候选teacher：slowrolling LIFT/PASS以当前实际三支撑轮Fz>30N、切向力<=Fz、COM余量>=10mm、原相对姿态<=.15rad独立推进轮参考。1cm位置跟踪仍约束body_age与机身参考插值，机身PI纠偏继续。初始BALANCE、RESTORE、legacy/local保持原条件；实际轮底清障才PASS，实际远侧才RESTORE。碰撞、失载、接近未清障保护、IK2mm/关节连续性/事务回滚不变，无新门槛。新增命名整数诊断body_tracking_ready/wheel_progress_ready，拒绝事务归零。

不改生产、PD、奖励、地形、训练；不启动BC/PPO，不重做独立支撑夹具。Baseline HEAD04133e09c986595484801c6539f3e9415700389e+既有未提交slowrolling；Candidate未提交v13-lift-decoupling。Last Feature/Verified不冒充物理成功。

## 软件验证

新反例旧实现4failed/4passed：安全条件满足却被root误差冻结LIFT/PASS、COM不安全仍推进、缺独立诊断。最小修改后8passed；扩展真实clear/不clear、恢复跟踪、BALANCE、失败重试/reset至13passed。与既有六文件合计242passed/51.22s。独立审查无Critical/Important；Minor补强unsafe测试有效事务与wheel_progress_ready=0后13passed/4.36s。不是全库通过，也不是物理成功。

本地/服务器teacher SHA a9b09206838d50849e72d71580b3b88aa9e924bfe5aa6ec71eee1a0dd2283353；probe保持b1a068e8ebab3642b000c3f333d159a66404dc6da7e13c5f034985f759f98a95。CPU日志/tmp/m1-lift-decoupled-green-final.log。

## 实际障碍验证

候选/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn，独占kernel flock；命令probe_m1_teacher.py --mode teacher --teacher-scope first-obstacle --slow-rolling --diagnostic-steps 1000 --headless --device cuda:0 --enable_cameras，4环境、实际10cm第一障碍、视频与逐帧原始证据。输出evidence-first-obstacle-lift-decoupled-v1。实际结果待收尾记录，不以阶段或参考高度判成功。

### 初始化阻塞与一次同配置重试

08:39:38Z v1 runner259134/Python259136启动，GPU起始1MiB。场景生成后在08:40:22 Starting simulation停止新日志；约8分钟仍只有render_configuration.json、GPU3923MiB，无控制帧/碰撞/teacher结果。Kit末条08:40:24 CreateJoint disjointed root_joint警告，不能据此认定根因。SIGINT及SIGTERM后仍不退出，确认cmdline属于本次probe后SIGKILL终止，exit137、GPU回到1MiB。没有删除任何证据，也不算跨越失败。

08:48:31Z无native/训练/pytest且GPU1MiB后，仅一次完全相同源码和配置重试v2（输出evidence-first-obstacle-lift-decoupled-v2），runner259897。未改网络/显示/物理参数。v1属于T306/teacher-feasibility/actual-crossing/native-initialization-block新诊断节点，不用“代码测试通过”掩盖原生未运行。

## v2实际结果与失败链

自然exit0，4环境各125帧；env0第108帧LIFT，env1–3第125帧刚进入LIFT即随批中断。全程无碰撞、无PASS/RESTORE/receipt/成功，实际前进约0.10549m/0.03686m。env0第120帧SUPPORT_LOST，125帧全批收尾，不把其他三行算成自身失败。原始result为FAILED_DIAGNOSTIC/recorded4/counted4/locked1/stage3_success0/full_denominatorfalse。

同env/frame明确链条：

- frame112 body_age42/lift_age5；frame113–118 body_tracking_ready0但wheel_progress_ready1，body_age42保持，lift_age6→11。这6帧证实解耦真实生效，不再卡在旧5步。
- 实际轮底在LIFT期间最高约0.000060m，仍贴地；接受的轮中心参考Z从0.115185→0.141168m，不是实际离地。
- frame118输入实际COM余量10.723mm，三支撑Fz中右后36.13N，允许该帧；frame119输入余量8.917mm，wheel_progress_ready0，抬轮参考暂停。该帧执行后右后Fz25.752N。
- frame120读取上述同环境右后25.752N<30N，SUPPORT_LOST锁停；没有碰障/overlap/实际越过。不能据此把“参考进度推进”说成已经抬起后摔倒，也未证明PD或某个奖励是唯一根因。

当前新的实际问题为T306/teacher-feasibility/actual-crossing/lift-load-redistribution：抬轮参考增加时，目标轮未真正离地，而非目标右后轮减载、COM余量变差。下一步应在同一真实障碍流程内处理抬轮与支撑载荷再分配，不通过放宽保护或加训练轮数冒充解决。生产/BC/PPO未改。

## 证据复核修正

初始记录verification报bounded feedback transaction evidence mismatch。定位为本轮新增wheel_progress_ready被旧wheel_泛前缀误纳入纯命令事务回放；回放不执行外层phase门控，默认0与实际1不符。原始结果和源码已冻结后，增加真实teacher→observer→replay反例RED；仅将校验字段限定为wheel_nominal_surface_speed_/wheel_final_surface_speed_/wheel_headroom_limited，反馈、IK、实际动作/轮速与容差保持。新测试也篡改两种轮速要求拒绝。修正后243passed/51.20s；限定独立复审无问题。

修正版probe SHA0709a54b6635fc4963ddd36fa0470f22810609441a5dc10a472c7d5731500e84。修正版复核另写/tmp/m1-lift-decoupled-v2-reverified.json，不覆盖原始verdict。外层两个ready诊断旗标不是该纯事务重放认证范围，不当成功凭据；实际逐帧输入和输出仍保留。

原始v2视频/JSONL/JSON/result/source4/tests7及v1启动日志归档，服务器与本地同SHA4b5ab3e1b41de41ae5a2183b8481472dfb73d9b83f895603c1576cb5ef36a311，文件evidence-first-obstacle-lift-decoupled-v2.tgz。本地.superpowers/sdd/2026-10-14-m1-dual-support-crossing-recovery，解包direct-crossing同名目录。env0视频已请求打开，工具queued，不声称用户已看到。原生已退出/GPU1MiB后才开始独立数学复核，非并发native。

修正版完整记录复核完成：4条errors均空、success均false、student_demonstration_usable均false。env0 complete=true表示完整失败记录，另3条complete=false表示同批中断；不修改原始complete0/失败verdict。修正版复核文件和243测试日志另存本地证据目录。初始化重试成功只消除本次阻塞，不证明该间歇性根因已修。

08:59:51Z最终只读核查无train/play/probe/recheck/pytest进程，GPU1MiB。修正版审计SHA51408ae42fec105b5dc109b98c380dd044547e2ea955549c97db3c6ab8ad73c1。本轮未commit/push/merge，保留此前脏改动；本地/隔离服务器notes同步，不覆盖生产文档。
