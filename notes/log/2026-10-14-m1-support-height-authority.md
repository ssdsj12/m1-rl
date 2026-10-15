# v20 支撑竖直目标来源分离

## 目的、依据及当前状态

T306/teacher/support-load-feedback/geometry-compensation-conflict。承接[v19失败实测](2026-10-14-m1-support-load-feedback.md)，不以旧数据推断新物理成功。上一目标轮次为progress，本轮现场再次确认旧native退出0/GPU1MiB，无重启。

独立分解v19 env1：input113 RR几何目标相对实测-4.656428mm；input129变为+1.331589mm，漂移5.988017mm。该帧载荷偏置+0.311559mm，合成目标+1.643148mm，实际下发IK目标+1.690993mm（残差及float32坐标误差范围）。input载荷31.623N，下一帧29.464N。说明几何目标的竖直漂移没有被小幅载荷积分抵消，尚不能证明新方案一定稳定。

## 设计与范围

采用[规格](../../docs/superpowers/specs/2026-10-14-m1-support-height-authority-design.md)与[计划](../../docs/superpowers/plans/2026-10-14-m1-support-height-authority.md)：从进入LIFT时实测root/已下发q捕获支撑世界Z基准，水平几何控制保留，活动轮轨迹不变；支撑Z只由基准和载荷反馈给出，RESTORE有限速接回。不增大增益、不改变30N保护/实际经过/恢复标准、不启动生产训练。

沿用用户直接执行授权与inline+最终独立审查，不重复许可。保留现有worktree及全部dirty/PT；Git作者未配置，继续用文件/证据SHA，不伪造提交。

## 已执行测试

Task1目标构造器execution_targets新增可选support_reference_w_z[B,4]。11项新测试RED（参数不存在）；实现后与旧execution_targets、load_feedback_transaction合计57passed3.19s/exit0。覆盖4活动轮×2模式，倾斜实测root与不同虚拟root下支撑世界Z独立、XY和活动腿不变、fraction=.25旧FK衔接、NaN/形状/mode0拒绝。

命令：CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 PYTHONPATH=.:tests:rsl_rl /opt/conda/envs/env_issacsim/bin/python -m pytest tests/test_m1_teacher_support_height.py tests/test_m1_teacher_execution_targets.py tests/test_m1_teacher_load_feedback_transaction.py -q。

## 未完成与下一步

已继续接入pose的paired高度回溯：8项新测试RED（未知参数）后，65相关测试GREEN3.33s/exit0。LIFT/PASS基准不漂移、RESTORE限速.01m/s、完整proposal只做一次执行beta，非法历史拒绝。仅/tmp候选pose/目标接口及测试已同步；教师capture/commit/rollback/reset/RESTORE生命周期和独立审核尚未接入，禁止现在启动native。下一步先生命周期RED测试，再接入，完整回归/review后真实10cm。物理跨越目标仍OPEN。

## 最新实施进展（覆盖上述未接入状态）

教师生命周期、height诊断、独立历史/FK/world目标/commit审核现已接入，fingerprint v20。首次捕获与RESTORE测试2RED、诊断1RED后86相关GREEN13.51s；独立篡改6RED后17GREEN7.11s，新增保留历史LIFT/RESTORE两例合计9GREEN5.16s。全相关回归568passed91.08s（该次启动早于新增2历史例，二者已另测）。不称全库通过。

RESTORE几何接回源取本帧完整requested+反馈proposal，每次反馈重算同步更新；最终solve证据唯一，完成仍需beta1和实际恢复。旧目标、旧载荷和高度仅在完整编码/连续性成功后提交。reset与完成清理高度。

冻结v19 input113首次已下发q/root作为基准，在input129保留旧load proposal比较：RR目标相对实测+1.643147519mm→-2.811392417mm，XY变化0，活动轮不变。此为反事实命令检验，非物理成功；脚本保存于本计划workspace/frozen_v19.py。

最终独立review已发出；现场GPU0为1MiB，未发现train/play/probe进程。未运行v20native，未启动生产。审查完成后使用唯一目录实测真实10cm并保留完整证据。

## 实测启动

最终独立review无Critical/Important；Minor为RESTORE接回完成门槛缺专门正反例（已有单步限速和实际恢复条件源码检查），保留待补。四项runtime双方SHA相符。2026-10-14T17:32:23Z启动唯一`evidence-first-obstacle-support-height-v1`，runner319205/python319207现场已确认，4env/seed101/first-obstacle/slow-rolling/load-feedback/真实10cm。仅隔离教师，生产训练未启。当前尚无结果，不将初始化或目标反事实算成功。

## 实测最终结果

进程已终止，exit0、GPU0回到1MiB；result FAILED_DIAGNOSTIC，4 recorded/counted、1 complete、4 locked、0 stage3 success，完整分母false。每路182帧，四路verification.errors=[]，全部student_demonstration_usable=false；env1–3相同轨迹不是三次独立随机证明。

最早诊断停止env0 frame177，physical_failure=false，reason11 APPROACH_UNREADY（不是IK失败）；未进入高度反馈。env1–3有67高度反馈帧，活动轮最大底高仅0.064969mm，未真实抬起。frame180有效事务后RR28.20219N，下一frame181 reason3 SUPPORT_LOST锁定；无碰撞/穿透。frame180 execution_fraction=.25，活动轮goal Z=.09866169、solved Z=.07540634，wheel_progress_ready0；说明最后阶段命令仍有回溯/进度冻结，不能称修复成功，也不能把原因仅归于IK公式或惩罚。

全部视频/原始JSONL/episode JSON/配置/source/log/exit及本次源码测试已归档服务器`/tmp/m1-support-height-v20-evidence.tar.gz`和本地计划workspace同名文件，双方SHA256 `42529ed5fa021f864e2056aebd34429c05080407f792a1b0943691a7750aac0a`。只读详细统计m1-height-native-summary.json与m1-height-failure-detail.json已复制本地。无生产训练、无删除。

下一步基于同env时序拆解冻结开始的实际载荷/倾角/目标与实角/目标限速，查明活动轮持续承载而弱支撑失载的机制；不盲目提高增益或降低保护。目标保持真实10cm跨越后恢复，尚未完成。

## 后续逐帧结构诊断（无需新native）

再次现场确认319207缺失、exit0/GPU1MiB。上一goal轮次progress（v20实施及完整失败实测）。本轮仅只读分析，脚本analyze_tracking.py/posture_sensitivity.py与JSON保存在本计划workspace，原始归档未改。

env1首次wheel_progress_ready=0为frame140/input139：三支撑原始Fz最小51.574N仍高于30N，但COM保守边距.007188m低于.01，当前三角估计最小载荷10.225N；候选三角估计51.248N不代表机身已到候选位置。tripod_combined_reserve=0，进度冻结是实际支撑几何条件不满足，不应删门槛。

frame114→180，rootZ .599004→.401120m；FL实际HIP -.07456→.96008、KNEE -.38480→-2.48403rad，轮底仍贴地，说明出现机身下沉/弯腿而非活动轮离地。frame114已下发新目标FK比同帧实测轮低14.544mm且X落后65.345mm；frame130低.660mm；frame180又低18.746mm。实际q FK与实测轮误差约.2mm，不支持“FK本身厘米级错误”的说法。

独立冻结敏感度：保持同帧root/q/anchor/load不变，仅command.body.pos_z增加1mm。frame114/130/150/180，旧几何路径三支撑世界Z响应分别约-.999875/-.998198/-.987756/-.923845mm，v20仅浮点零（<=1.7e-16m）。这是固定世界Z覆盖完全消除机身竖直纠偏通道的代码级证据，不能把它当作已验证物理唯一原因。v20解决目标漂移同时移除了关键姿态支撑自由度，架构须重新分离机身公共支撑与零和载荷分配，不继续盲加增益。

所查114/130/140/150/170/180最后物理子步computed/applied effort差0，最大绝对力矩分别10.47/13.31/13.32/14.54/16.66/27.23Nm；此记录只覆盖最后子步，不能证明全子步不饱和或力矩充分。保留原PD、不据此调参。

下一单独假设：给三支撑保留明确的机身高度公共纠偏通道，载荷零和差分单独调配；保留活动轮实测IK和全部物理门槛。先设计坐标/状态/回溯与独立敏感度检验，再隔离10cm，尚未实施或宣称成功。用户直接执行授权仍有效，不重复常规审批，不自动训练。

Baseline/Current Work Ref：04133e09c986595484801c6539f3e9415700389e加工作区修改。关键文件Go2Pvcnn/ame_baseline/m1_teacher_execution_targets.py、Go2Pvcnn/tests/test_m1_teacher_support_height.py；只读分解脚本和JSON保存于旧v19证据workspace，不改变原归档。
