# v32 支撑膝余量候选排序

## 后续冻结高度敏感度（CPU，非物理反事实）

归档SHA已重验、原生进程确已退出。`height_sensitivity.py`保持记录的command/载荷/上次q/捕获支撑高度/历史heave，只扰动测量rootZ±1mm并经过实际production heave与execution_targets。122/125/129的heave限速已饱和，测量root下降1mm会令三支撑body目标Z向上约.999/.998/.993mm，即顺着机身下沉缩腿。119首次捕获附近仍约.613mm。说明现有固定世界支撑Z加限速heave存在跟随下沉的几何通道；尚不能声称是全部物理原因或已修复。

`height_anchor_counterfactual.py`只读试算：支撑参考高度加入相对首次119帧测量rootZ变化，活动腿不变，保留当前heave/载荷偏置。122原IKmaxdq .02480不变，125由.02970变.04924仍小于.05；129需要.09349超过原单步.05，故不能迟到后直接下发。119/120 full fraction求解本来就超过限速，本脚本不是完整backtracking或安全验收。该结果支持在捕获起点处理测量跟随项、继续保留原事务回溯的下一假设；不扩大步长、不放松真实支撑。两JSONL输出已复制本地ledger，未改runtime/未新实测/无生产训练。

最终：411683/411685已退出，exit0，result FAILED_DIAGNOSTIC；4记录/3完整终止/3锁定/0成功，完整分母false，env1 frame134 failure_locked、physical_failure=false。四路verification.errors=[]，unsafe=false，均不能作为学生示范。139帧trace全部保留；不要把complete=true的失败记录当成功。原始视频/源码/证据归档本地与服务器SHA `2e094f42f358d4a2caa118215f573709924b256fd429026427558408c57aa3cb`，文件 `/tmp/m1-knee-reserve-v32-original-evidence.tar.gz`。env1trace SHA `4fc9ee5adbdb3ca7196ab23d7959e4a602e4bfe244742786bd2ecb4f9dc91b2a`。视频29帧抽取0/11/18/22/27/28已查看，可见机身降低/倾斜而没有完整越障；视频帧号非遥测帧号。当前无训练/原生任务，不自动重启；下一步只读检查承载姿态目标与机身高度/活动轮执行的相互影响。以下运行中叙述为历史。

实测阶段证据（进程411685仍活，终态尚未出）：四路trace已到139帧，env1–3首先在130帧reason5。119进入LIFT：实际三支撑119/134/78N，轮底仍约.000049m。122–129 execution_fraction=1、intent=1，129请求z.098772/解z.098734/实测轮心.097664，未离地；机身z从119的.53558降至130的.52440。130实际三支撑159.76/140.12/54.60N，实际静态预测最弱34.53N，而所选姿态对实测三角预测28.97N导致combined reserve0和停止；不得称实际三轮已失载。支撑膝仍弯曲，旧贴近伸直限制已不再是该时刻事实。继续核查机身下沉/倾斜与目标姿态预测、执行之间偏差；不降安全门槛，不改PD，无生产训练。进程仍在逐记录审计，不重复启动或把部分记录当完整结果。

最新：最终927相关CPU通过192.07s；审查无阻断。v31归档SHA、v32两runtime SHA与tarSHA964fc8204a1134375d21f194af416190835cbea54f4687bb2da481b0ca2dfe64核验一致，GPU1MiB/无并发后runner411683与python411685启动唯一 `evidence-first-obstacle-knee-reserve-v1`。现场核实命令及Isaac初始化日志；尚无实际跨越结果，不重复启动。以下“尚未部署”为历史阶段。

用户已授权直接实施、隔离实测，不重复审批；不启动生产训练。真实10cm跨越与恢复仍OPEN。

v31实测原始归档双方SHA `3e77947bd4954314777a1af35e685c1e641a56658875e5c986df55fe66c5efb0`；0成功，frame139支撑失载。冻结几何显示支撑膝接近伸直边界，不能据此认定单一物理因果。

仅修改有载荷候选排序：精确最弱预测载荷优先，然后三条非活动腿最小膝余量，最后原运动代价与索引。无载荷路径、资格条件、实际30N支撑、IK残差/限速、恢复要求全部保持。v32 fingerprint与排序两个runtime文件；候选服务器尚未部署。

TDD缺helper12RED，真实frame90集成1RED/12pass后接入，62相关通过。首次926项回归922pass/4fail；两项旧位置完全冻结断言改成既有限速下非向上变化；一项主动腿错误注入被真实下游intent重新计算消除，改注入支撑腿以检验最终错误拒绝；一项旧BALANCE样本尚未达到新较低goal，应留在准备阶段而非按旧姿态进入LIFT。四文件77pass16.74s。最终927回归正在远端 `/tmp/m1-v32-full-corrected.log`，不得把启动当通过。

独立审查Critical0/Important0，Minor非均匀支撑margin回归覆盖记账延后。裸pytest仍13个已记录依赖收集错误，不称全库通过。细节与原始诊断脚本见 `.superpowers/sdd/2026-10-15-m1-support-knee-reserve/`。
