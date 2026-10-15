# M1 v18 实测抬轮与受限执行协调

## 最终实测结果（优先于下方进行中记录）

v18已结束：FAILED_DIAGNOSTIC，recorded/count=4，complete=0，stage3_success=0，locked_failures=3，duplicate=0。首次诊断停止源env1/frame129/control_step129，support_lost，physical_failure=true，errors=[]。四路各134帧，均未完成跨越；所有单路审核errors=[]不等于物理成功。

env1首有效LIFT frame114：统一预测储备0.449875，请求Z .0979072、实测Z .0977272；旧命令FK起点 .0814005，执行目标 .0961913、求解 .0831830。末有效frame129：请求 .0989137、执行目标 .0989137、求解 .0988856（差约.028mm），实际轮底 .0000575m仍贴地。该帧右后Fz29.7507N低于30N，collision=false；下一决策拒绝。说明小增量执行精度已改变，但物理承载仍先恶化，不能认定已真正抬轮或跨越。实际相对捕获Z受姿态/轮轴几何影响，不替代轮底离地证据。

runner305581/python305583已退出，退出码0，GPU回到1MiB；未生产训练。4路视频/完整JSON和JSONL/source/log/exit全部归档。服务器/tmp/m1-reconciliation-v18-evidence.tar.gz及本地.superpowers/sdd/2026-10-14-m1-measured-execution-reconciliation/m1-reconciliation-v18-evidence.tar.gz双方SHA256：1fa550c74b73462a73dbd7db0200dd44f03666a8814edaecee7e8d9c9edce601。新问题仍为抬轮执行期间承载储备与真实受力不一致，原因需继续逐帧定位，不能靠放宽保护或宣称成功处理。

2026-10-14 UTC。用户已确认总体设计、书面设计与实施计划，Native实施；仅隔离候选，禁止生产训练。

## 已实现与验证

- 活动腿执行IK逐腿容差0.1mm，其他腿/非执行模式保持配置精度。IK最多32次、原分支/关节范围/每步2.5*dt不变。
- 抬升请求以同帧实测高度为下界，受储备/lead/ceiling约束；旧命令FK仍作插值起点，多步追赶不当实际抬升。
- 当前、候选锚点、候选实测三种几何最弱预测取min；真实载荷及趋势保护仍取更小值。
- 新指纹v18，分别记录物理请求/实际轮高/执行起点目标和求解轮高、逐腿容差、实际相对捕获抬升及统一储备；审核器独立复算。
- RED/GREEN：小增量19失败→相关92通过；高度与储备5失败→相关67通过；新证据字段2失败后实现；恢复缓存残留反例失败后补清理。
- 最新相关495项通过80.77秒，命令exit0。覆盖4个v17真实失败帧冻结输入（113、118、123、131），只是CPU数值回放，不是新物理轨迹。
- bare pytest仍9项收集错误：pxr缺失及历史归档测试重名，详见实施账本。不得称全库通过。

## 隔离与证据

本地linked worktree dual-support-recovery，分支codex/m1-dual-support-recovery；历史dirty修改保留。服务器a21506654554025984756592，候选/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn。7个runtime文件本地/服务器SHA逐项一致，生产目录未动。

实测前只读GPU0为1MiB，无train/play/probe/pytest进程。源码预审快照AF40B084BDDD32A016FEC2AB38F8F0ECFE81FEB70AD8BD1C5F1B859CAA93719E。

状态：独立审查无Critical/Important；Minor为四个冻结帧不覆盖连续命令回灌，已保留该范围限制。2026-10-14T13:11:52Z启动唯一隔离4环境10cm原生实测，runner305581/python305583，GPU启动前1MiB且无并发训练/回放。输出evidence-first-obstacle-execution-reconciliation-v1；跨越成功未证明。未提交/发布（Git作者未配置），未删除旧PT/证据。

实现计划：docs/superpowers/plans/2026-10-14-m1-measured-execution-reconciliation.md。详细记录及测试日志：.superpowers/sdd/2026-10-14-m1-measured-execution-reconciliation/。
