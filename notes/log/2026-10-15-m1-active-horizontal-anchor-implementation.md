# v34 活动轮水平起点实施

最新v34终态：428986不存在/exit0，FAILED_DIAGNOSTIC，4记录3完整失败3锁定0成功，env1 frame134锁定/errors[]，未完成全分母。原始包双方SHAba2001283bbc209910d865bdeef8280685ecef290179ffceb2f6d377ce3168db，29帧10fps视频已检查0/14/28。XY捕获正确但未离地。冻结130候选126IKvalid、0载荷eligible，最好29.26377N；仅静态候选改measured姿态得到6eligible/42.53421N，未部署且请求姿态链尚未一致，不能当执行可行/物理成功。详见notes/log/2026-10-15-m1-active-xy-native-diagnosis.md。下一结构性核对支撑姿态/COM/执行一致性，不继续盲补或放宽门槛。当前无native/生产，goalactive，本轮进展。

最新终态CPU：985passed312.94s，/tmp/m1-v34-final-full.exit=0，runner426312已退出。deploy.ps1退出0：v33原始归档SHA/两runtime包与单文件SHA一致、无训练/native/pytest、GPU1MiB。launch.ps1执行唯一runner428984，2026-10-15T00:40:59Z，kernel flock，prefix evidence-first-obstacle-active-xy-v1。当前原生运行中，不重复启动/不覆写candidate；生产未动。真实跨越与恢复尚无结论，需同PID终态/trace/video/审计及归档。Task2完成，Task3进行中，goal仍active。

最新：独立历史审计10RED→10PASS33.31s；唯一最终review发现请求XY未绑定（0Critical/1Important），已用“anchor正确但真实请求错误且共享replay”反例RED复现，追加raw→requested绑定后26相关PASS47.00s。冻结请求和非零yaw＋3mm共同滚动两项PASS8.61s。review复核阻断项关闭。第一次完整回归SSH断开后原PID423628已不存在，无完成结果，不计通过；当前durable完整985测试runner426312，/tmp/m1-v34-final-full.log与.exit，不重复运行/覆写overlay。裸collect3834项遇13既有导入错误4.45s，不能称全库通过。候选仍v33；v34包只上传/tmp尚未部署；待完整回归后直接隔离10cm原生。真实跨越未成功，不生产训练。

教师SHA b4398203433e69edd1e359fbe1d3c87eac2da92bbb3bb523e9eadf041b40afbe；probeSHA3ee017a13f1476b430083fc197fcda561fddd472a4396a2543e8c41b009c6861；两runtime包SHAf3c1daa9ee04246a3fa7e33519a95cdfca77fac85cb93caa606a7f15d5909c63。独立审计用标量pre/input/post重算共同滚动、首次activeXY捕获、失败无提交、LIFT/PASS推进/冻结请求；不依赖producer重复计算。保留全部历史证据，禁止把静态green当跨越。

Task1最终四文件87passed49.15s；包含10项新生命周期测试及原load/lift/reference回归。teacher SHA b4398203433e69edd1e359fbe1d3c87eac2da92bbb3bb523e9eadf041b40afbe。Task2独立历史审核/完整回归/最终review尚未完成，不部署原生，真实跨越未验证。

T306/teacher/active-horizontal-anchor；base04133e0工作树，候选版本未提交。用户直接执行授权有效，主代理inline，最终独立审查一次。

设计/计划：docs/superpowers/specs/2026-10-15-m1-active-horizontal-anchor-design.md 与 plans/2026-10-15-m1-active-horizontal-anchor.md。只在slow_rolling非diagnostic且原准备条件允许BALANCE→LIFT时克隆wheel_anchor，把活动轮XY设为同帧实测值；支撑腿/所有Z不变，经原有有界IK与最终encode才提交。fingerprint v34。不修改PD、轮速、载荷底线或成功条件。

首轮测试命令漏candidate PYTHONPATH导致extension.parallelism导入错误，不算有效RED。补全现有overlay+candidate路径后，首次捕获4腿和失败重试5项按预期RED，2既有行为通过，23.66s。最小实现后7passed20.55s。追加重复步、PASS不重捕获、最终encode失败回滚回归；新文件+load/lift/reference提交共四文件回归正在运行。

当前只本地及/tmp/m1-v30-audit-fixed CPUoverlay更新teacher，原生candidate仍v33；未新native/生产训练。Task2独立锚点证据审计尚未接入，不部署半成品。旧v33原始归档与视频完整保留，实际跨越仍OPEN。
