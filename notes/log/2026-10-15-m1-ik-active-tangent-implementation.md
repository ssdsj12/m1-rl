# v27 constrained tangent IK

当前：真实v26失败反例6RED，最小实现后75专项GREEN；完整772回归进行中。独立review C0/I0/M1（四腿/configuredboundary测试未显式证明reducedpath触发，保留改进项）。未v27原生/未生产训练。
最新进度覆盖上句：772项完整回归已通过143.49s，样本SHA与原始trace独立一致。GPU1MiB/进程检查及flock通过后，服务器2026-10-14T20:55:29Z唯一启动runner368879，输出evidence-first-obstacle-ik-tangent-v1。原生正在运行，尚未跨越结论；禁止重复启动/生产训练。

仅在原始有限膝候选越过既有有符号边界时，将合法膝位移从目标误差中扣除，再用ABAD/HIP约化Jacobian求候选。两个候选均保留有限性/关节/分支/边界与实际FK严格下降要求；只选残差更好的合法候选。原32迭代/.25rad分量/.1mm执行门槛/外层限速/编码/实际恢复要求不变。正常内部区间不使用备用路径，非法备用候选不能替换合法原候选。

两runtime SHA本地/remote一致：IK1d0ac560c21348df549f7308d951ae0a56d47047ef4d73d946ef451fce11a9ca；teacher8dfa603b5cd788ebe3e4e844b922b24b99ab4114e821bbb3c4ac8bf5aaf29eaf。设计/计划同日期m1-ik-active-tangent；证据与baseline在.superpowers/sdd/2026-10-15-m1-ik-active-tangent。

v26最终：4×142帧，3locked/1interrupted/0success，首锁env1/137；所有4auditerrors=[]，退出0/GPU1MiB。完整归档双方SHA2b458d11adb10f5bcddc212820e44c308217c43e7c1c47fd97405e3706c41618。视频30帧/10fps已查看末帧，仍在障碍前，没有有效抬轮/跨越。原生完成后才部署v27源码，未改变运行中audit来源。

用户直接执行授权沿用，不重复批准；已有隔离分支，不改全局Gitidentity，不删除证据/PT。下一同4env10cm唯一实测；CPU和review不是物理成功。

## 原生中间结果：175帧，尚待最终审计

env1–3在170帧锁停，env0未锁停；活动轮底最大0.0541mm，未有效抬轮，不能以旧137锁点被越过声称成功。166起candidate_index=-1/count100，执行目标缺失，teacher reason5/freeze3；三支撑轮仍有约124–136/95N。最终回合审核/exit未完成，原进程继续，禁止重复启动。

frame150同帧预控制轮中心Z95.9739mm、原目标97.7913mm、回溯执行目标81.8548mm、原关节指令当前FK81.6738mm，共同步长仅.01123047。冻结逐腿可行性检查：活动腿beta.25时IK合法且dq.048829rad在.05限速内，但共同候选左后工作空间拒绝；更小beta仍左后残差受限。这证明共同回溯压低抬腿进度，不证明拆分步长就是全身安全解（beta.25活动中心也仍低于实测）。新166候选全拒绝须另行反向追踪，不能混同旧残差问题或称摔倒导致。下一支撑可达性/整体进度耦合诊断，未改变runtime。
