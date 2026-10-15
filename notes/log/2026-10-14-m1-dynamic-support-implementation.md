# 动态支撑与实测抬轮实施

关联T306/teacher-feasibility/actual-crossing/lift-load-redistribution。Baseline04133e0及既有未提交rolling候选；用户已确认[计划](../../docs/superpowers/plans/2026-10-14-m1-dynamic-support-measured-lift.md)。仅隔离candidate，不改生产/BC/PPO。

## 当前实现

slow_rolling实际LIFT/PASS：原始载荷/实测COM保护保持，0.10s载荷EMA仅用于逆载荷目标COM排序；126有限候选/双几何/IK/连续性保持。身体参考限0.02m/s，轮参考受0.02m/s、实测领先0.02m及载荷/COM储备/下降趋势约束。活动轮Z、滚动锚点、原始碰撞及真实经过/恢复不放宽。fingerprint v14。

纯函数模块新增；pose可选排序；teacher scratch原子提交；probe独立JSON外层状态/动作/诊断复算，另保留纯反馈验证。完整外层输入绑定同帧preparation_input及实际关节输入。新动态候选诊断独立命名，不冒充BALANCE选择凭据。

## 验证进度

原lift_decoupling14基线通过。纯算法18 RED→GREEN；排序1 RED→55含pose回归；集成动态控制37通过。外层4 RED→GREEN，随后实际输入篡改6项RED确认审查发现；候选诊断串用反例RED确认并修复。最终相关回归进行中，尚无新物理结论。

独立只读审查：1Important（外层输入未绑定实际采样）已通过对应反例修复；Minor为新状态边界测试覆盖不足，已补已有历史编码拒绝/重复/拒绝后断帧及raw29N但EMA高的测试，双环境单行reset专项仍待补充。未发现确定Critical控制错误。审查不评价物理有效性，必须原生实测。

裸pytest已实际执行：9收集错误，8个同名测试模块冲突（历史归档/root副本与tests目录），test_m1_sdf_probe缺pxr。未删除历史归档或安装依赖，不能称全库通过。一次CPU并发导致线程竞争，中断自身回归234已通过但不算完成；之后CPU命令OMP/MKL线程1，物理配置未改。

## 决策及未完成

外层采用完整白名单JSON状态重放而非再复制一套公式：更完整验证阶段/回滚，代价是较大记录与复算开销、共享算法错误仍依赖独立断言。Git身份缺失，不伪造作者；保留未提交差异及SHA。尚未跨越、尚未开训练。

## 最新实际10cm结果（2026-10-14 UTC）

最终10文件相关回归319 passed/62.96s；裸pytest上述9收集错误仍在，不能称全库通过。专项双行reset及独立断帧/换腿测试仍未补齐，不用物理结果代替软件覆盖。

09:45:32Z在候选C=/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn启动evidence-first-obstacle-dynamic-support-v1，runner268078/probe268080；事前无竞争任务/GPU1MiB。实际stage3/10cm/seed101/4env/first-obstacle，非孤立支撑。4×186物理帧已完成，逐路verification.errors均空、success均false；总汇复算/退出归档继续收尾。

- env0：APPROACH60/BALANCE47/LIFT79，108帧首次LIFT，181帧APPROACH_UNREADY(reason11)保护锁停；推进0.12700653m。LIFT活动轮最高底部0.000052668m（约0.053mm，仍贴地），最低载荷57.63088N；其他三轮最低载荷76.13818N。锁停帧实测COM margin0.03701688m。1完整失败记录，非成功。
- env1–3：各APPROACH66/BALANCE58/LIFT62，125帧首次LIFT；各推进0.07682228m；活动轮最高底部0.000054084m、最低载荷32.51266N，其他三轮最低44.15547N。三路因env0停止同批中断，不能算三个独立失败。
- 全部零碰撞、零PASS/RESTORE/receipt/strict成功，无可用student demonstration。支撑失载较上一轮改善，但目标轮仍未实际抬起，不是“已经会跨”。
- env0第165帧储备1，实测轮心Z0.09710809m、接受目标0.11714552m，领先0.02003743m而冻结；目标轮仍67.7N。新实测领先限制按设计阻止参考继续悬空增长，尚未解决实际卸载/抬起与持续接近的协调。

下一根因节点仍属actual-crossing/lift-load-redistribution：先查障碍内活动腿实际卸载/执行与接近余量；不能从本次认定摔倒或碰撞惩罚导致失败，不盲调PD/门槛/加训。生产、BC、PPO均未改/未启动。

## 最终收尾证据

result.json为FAILED_DIAGNOSTIC，complete_full_denominator=false，recorded/count=4、complete=1、locked=1；诊断源env0/episode0/frame181/failure_locked，physical_failure=false、errors=[]。不是完整课程验收。原生exit0，268080已退出，GPU1MiB。

服务器归档/tmp/m1-dynamic-support-v1-evidence.tgz包含四路视频/JSONL/JSON、result/source及日志exit和对应4runtime/3tests；本地副本在本计划.superpowers/sdd/2026-10-14-m1-dynamic-support-measured-lift内。双方SHA256一致：a94d97ef91b535ee2f404409b075962b6480561ab0343c79af45cfa39c63f0be。env0视频已另存同目录stage3_seed101_env0_episode0.mp4；UI打开返回queued，不宣称已显示。

runtime SHA：dynamic8445baa4bb3961c3eb515600b59a13ca046cbc490b6ef850e46932b25ffa414d；pose e765c18890ff364a35157079fb12d250b624efc60db92caa943cf9e3aebc5d93；teacher2ffb6168d48ee75f94627d1b38c79b8d8b3ea63f1332a5446fdf77ab53f5211b；probe e93e74f7b6425d3768a6c07391123b43ea4ae01fd76cbf2f76cb8d0c5ab43ffa。保留未提交差异/证据，无生产替换、Git提交或push。
