# v21后续：活动轮接触力矩遗漏

## v22实施进度（本节优先于下方只读历史）

### 最终实测：未成功，证据有效

本地归档已独立Get-FileHash匹配远端完整SHA53e62bac5f024ee5d8254d52e1820a12be6054dad81e4bb8f2074eef0b44a74f；位于本计划workspace/m1-active-contact-v22-evidence.tar.gz。指定runtime/test git diff --check通过。下文“正在接收”是收尾前历史，当前已完成。

runner335499/python335501已退出0，GPU1MiB。唯一4env seed101 first10cm共4×144帧；result FAILED_DIAGNOSTIC，recorded/count4、complete3、locked3、stage3success0、duplicate0。env0随诊断中断，env1–3相同轨迹锁停，不称3次独立随机成功率；四路verification.errors=[]且success/usable均false。

首次锁定env1/frame139/input138：右后输入27.8248749N<30，锁停后13.0447073N；无碰撞/穿透，活动轮最大底高.000052236m（.0522mm，非有意义离地）。frame138输入右后30.4408N，纠正目标108.9475N，最后提交差分RR-.80604mm、公共heave-4.15556mm；实际仍失载，COM余量.006438m、roll-.099289rad。对比旧v21frame138保护，新139只晚一步，不能称改善跨越。

新分配正确性已在原生实数确认：frame114目标RR112.663N而非旧45N；全活动阶段力矩残差最大约6.07e-6N*m；数学纠正未带来实际跨越。

下一具体诊断不是盲加增益：活动腿最终执行插值仍低于实测轮心。frame125 measuredZ.0973595/goal.0982954，旧已发送q在当前机身下FKZ.093664，beta.5产生step.0959797，IK解.0959243；frame138 measured.096365/goal.0985516，旧FK.0921727，beta.5 step.0953621/solve.0952766。frame114 beta.125、旧FK.0814005，step.0832493/solve.0831830，明显仍向地面压。执行插值与IK误差约.017–.086mm，不能笼统归因IK求解错误。原因链需查实际joint-target连续性/全身回溯及当前实测状态的差别，不擅自跳过限速。姿态支撑Z通道缺失保持另一个OPEN，不混作唯一因果。

完整远端归档/tmp/m1-active-contact-v22-evidence.tar.gz，SHA53e62bac5f024ee5d8254d52e1820a12be6054dad81e4bb8f2074eef0b44a74f；包含原始JSONL/视频/配置/source/log/exit、7runtime及3test和审核结果。正在本地接收，需独立hash核实。此轮为progress：修复并实际否定其足以跨越，目标OPEN，未生产训练/BC/PPO/删PT。

最终回归660通过103.88s exit0，审查Important已RED/GREEN；无Minor。2026-10-14T18:38:41Z启动唯一隔离runner335499，evidence-first-obstacle-active-contact-v1，4env/seed101/first10cm/slowrolling/loadfeedback，kernel flock；启动前GPU1MiB/无其他native。正在运行，不能称成功。不重跑旧v21，不启动生产。

已按[实施计划](../../docs/superpowers/plans/2026-10-15-m1-active-contact-load.md)完成3runtime：required wheels_w、活动接触力矩补偿、原始几何独立审核、fingerprint v22；新字段未投影目标/仿射/残差。旧矩形目标120/120/60N反例RED，修正84/84/132N GREEN。35unit+29integration通过；第一全相关656通过103.61s。补原始v21frame114双dtype回归通过。

独立review C0/I1/M0：近共线合法float32相消，未投影总力错误/残差不实；已RED复现并改新分配几何与中间量double，target/offset仍输入dtype。54相关通过9.82s，producer→独立audit反例1通过；最终全相关回归运行中。未放宽审核容差、未改物理增益、安全线或production。此时尚未启动v22native。

本地/候选SHA逐项匹配：load_feedback b7bd29c4，reference_teacher a25d9119，probe a2d4fd25。候选目录/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn；生产未改。所有旧archive保留，Git无身份不伪造commit。实际跨越仍OPEN。

上一goal轮次为progress：635CPU、唯一实测和完整归档。当前重验v21 result FAILED_DIAGNOSTIC/exit0，328508不存在/GPU1MiB；未新native/未改runtime/未训练。

## 两项冻结证据

1. 姿态通道：frame114/120/125/130/135/137，command roll/pitch加.01rad，原几何支撑Z改变约1.5–3.8mm；v21固定高度后约1e-16m。实际roll -.00733→-.08758，pitch .01401→.05552。证实通道抵消，不证明唯一物理原因。
2. 活动轮仍承重时，旧target用三支撑总力乘目标三轮比例，遗漏活动轮力矩。frame114左前69.073N，旧RR目标45N/实测87.473N，旧反馈要求上移减载。计入同帧活动接触后RR目标112.663N，需要下移增载。旧合成COP相对选中COM差+.0627204/+.0334260m；新未触投影且差约1e-14m。frame137旧45.070/new105.977N，实测30.066N。

这只是数学反事实，不是物理成功。A=max(activeFz,0)，S=sum positive support，活动轮仿射b，目标λ*(S+A)-A*b；保留45N/总和S投影且记录残差。保持增益/速率/PD/安全线，先纠正遗漏，不同时恢复roll/pitch。

[v22规格](../../docs/superpowers/specs/2026-10-15-m1-active-contact-load-design.md)按用户直接执行授权定稿；下一精确实现计划、RED→GREEN和独立审核，再真实10cm，不重复要求确认。实际跨越OPEN。

脚本/JSON在.superpowers/sdd/2026-10-15-m1-support-heave/：attitude_authority.py、attitude-authority.json、active_contact_moment.py、active-contact-moment.json。远端/tmp/m1-heave-attitude-authority.*及/tmp/m1-active-contact-moment.*；均CPU只读原始v21轨迹。
