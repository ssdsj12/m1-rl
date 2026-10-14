# M1 双几何准备与跨后恢复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复准备候选只看旧支撑锚点的局限，并用实际完整跨越后连续0.3秒恢复前进作为整机结果，逐级验证10cm Teacher能力。

**Architecture:** 固定锚点继续生成IK目标，同帧实测轮位只增加候选准入检查。独立、无动作输出的结果监视器消费原始物理状态和局部凭据；探针持续采集至恢复窗口完成，并从原始证据重算结果。两个已批准规格在探针schema7统一集成，不重设计动力学控制器。

**Tech Stack:** Python、PyTorch、pytest、Isaac Lab隔离原生探针；CPU纯数学/证据测试与GPU物理验收分开。

**Spec:** [双几何筛选](../specs/2026-10-14-m1-dual-support-selection-design.md)、[跨后0.3秒恢复](../specs/2026-10-14-m1-crossing-recovery-outcome-design.md)，两份书面规格均已获用户确认。

**执行状态（2026-10-14 UTC）：** 用户已确认计划。Task1–4实现/审查及最终532项相关CPU通过，冻结02a70cf；原生控制合同通过，准备关发现physics-callback-clock-quantization后主动停止。Task5未全部完成：后续抬落/跨越/正式A均NOT_RUN，待时间证据来源修订；不改物理门槛或开BC/PPO。[最终证据](../../../notes/log/2026-10-14-m1-dual-support-final-validation.md)。下文待审阅描述为原计划快照，不再等待重复确认已批准内容。

## Global Constraints

- 2026-10-14 UTC；本地分支10-14，计划基线ccbd00fb421e28810bd63594e04515552b07e764；runtime39a6590/verifier de46186尚未修订。本计划待审阅，不是执行回执。
- 126候选、原成本/平局规则、固定IK锚点不变；两个预测三角形余量均>=0.010m。真实COM不足时仍可搜索，实际起抬门槛不降低。
- rootZ .62m、物理/资产/质量/PD、膝分支、包络前后±4cm/侧向±6cm/降低≤8cm、IK2mm/32次、slew2.5rad/s、回溯8档和无效5步锁定保持。
- 保留16维Teacher、原两遍反馈事务、实际三轮支撑和每轮远侧5帧恢复；不新增MPC/WBC/外力/状态写入，不把最终恢复条件施加到整个LIFT/PASS。
- 保留10cm、8目标+70填充、20秒含恢复窗口、每碰撞控制步2分累计20重置且不重复termination。旧PT/记录不删；生产奖励/学生PT合同不迁移。
- Teacher实现标识support-ik-transaction-v9；probe schema7；结果合同crossing-recovery-0p3-v1。旧schema不可补造新证据。
- 新主机root@a21506654554025984756592尚未核实；仅隔离候选，禁止训练/native并发，不改生产、网络、全局SSH/Git或显示，不恢复旧watcher。
- 执行方式沿用用户指定子代理；各任务实现后规格审查、质量审查，最后整体验证。失败不得自动扩包络/改增益/降门槛；Teacher A未通过不启动BC/PPO。

## Review Focus

1. 上一accepted候选125或退化实测三角形绕过新筛选：任务1负例必须拒绝且不改变固定锚点。
2. 同行执行后测量或其他env/frame被当作准备输入：任务2生产端上下文与篡改测试必须拒绝。
3. 15个观测被误算成0.3秒、断帧/重复帧累计时间：任务3验证14/15区间及异常身份。
4. root越线但倾斜轮体仍重叠、空required或单轮凭据冒充整机：任务3四轮圆柱投影和scope测试拒绝。
5. reset/timeout终帧或先前碰撞被恢复窗口洗白，探针早停漏记录：任务4终帧、并发peer及旧证据测试拒绝。

## File Map 与依赖

- 修改 `Go2Pvcnn/ame_baseline/m1_teacher_pose.py`：候选双几何纯计算（任务1）。
- 修改 `Go2Pvcnn/ame_baseline/m1_reference_teacher.py`：同帧传参、选择调用边界与诊断（任务2）。
- 新建 `Go2Pvcnn/ame_baseline/m1_crossing_recovery.py`：纯结果监视器及合同（任务3）。
- 修改 `Go2Pvcnn/scripts/probe_m1_teacher.py`：选择上下文、后端重算、原始恢复样本、结束条件及正式验收（任务2/4，禁止并行编辑）。
- 修改 `Go2Pvcnn/tests/test_m1_teacher_pose.py`、`test_m1_reference_teacher.py`（同目录）：任务1/2回归。
- 新建 `Go2Pvcnn/tests/test_m1_teacher_selection_evidence.py`、`test_m1_crossing_recovery.py`、`test_m1_teacher_recovery_evidence.py`：任务2/3/4证据及结果测试。
- 修改 `Go2Pvcnn/tests/test_m1_teacher_probe_contract.py`：schema/正式套件结果（任务4）。
- 任务5维护本计划、两个规格及README、notes索引/T306、ai-17/human-17现有入口与新实施日志；不暂存旧watcher或其他dirty。
- 依赖：1→2；3独立，可与1并行；2+3→4→5。每个worker只拥有列出的文件，主代理整合共享探针。

## Task 1：候选对同一预测COM做双几何准入

**Files:** pose模块及其现有测试。
**Interfaces:** `choose_support_pose(measured, anchor, accepted, com_w, wheel_anchors_w, active_wheel, nominal_root_z_w, q_seed, branch_q, cfg, *, measured_wheels_w) -> PoseChoice`；新增必填轮位[B,4,3]同dtype/device。`PoseChoice.measured_triangle_margin_m: Tensor[B]`；原predicted_margin_m仍指锚点预测。

- [x] 添加RED测试 `test_previous_candidate_must_pass_measured_triangle`：构造125锚点>=.010但实测预测<.010且有替代候选，断言 `choice.valid.all()`、`choice.candidate_index.item()!=125`、双margin>=.010；另测全无解 `not choice.valid.any()` / index=-1。固定solver使几何负例不依赖物理解。
- [x] 添加 `test_dual_geometry_contract_and_invariance`：同几何与原规则相同、活动轮不入两三角形、旋转/批行隔离、锚点逐元素未变；shape/dtype/device错误抛合同错，NaN/退化行无效；candidate_count保持包络数量，成本平局仍最小索引。
- [x] 运行 `python -m pytest Go2Pvcnn/tests/test_m1_teacher_pose.py -q`；确认新增测试因缺少新接口/行为失败，而非缺依赖。
- [x] 在pose模块校验新输入，对126个相同predictedCOM分别调用support_margin；仅扩大eligible布尔条件，保留成本/无效诊断参考和锚点IK。更新所有调用者传明确实测轮位，不提供自动fallback。
- [x] 同命令GREEN，并运行 `python -m pytest Go2Pvcnn/tests/test_m1_teacher_ik.py Go2Pvcnn/tests/test_m1_teacher_reference_commit.py -q`；所有用例通过且既有IK/事务不回退。
- [x] 审查后仅提交此任务文件，消息 `feat: filter teacher pose candidates against both support geometries`。

## Task 2：Teacher同帧接线及生产端选择证据

**Files:** Teacher、probe、现有Teacher测试及新selection_evidence测试。
**Interfaces:** Teacher新增 `_select_preparation_pose(self, s: TeacherState, i: int, work: dict, accepted: PoseReference, q: Tensor, branch: Tensor) -> PoseChoice`，work为当前事务行字典，仅包装原BALANCE选择点并传同一s轮位；不另算第二套选择。probe新增 `observe_preparation_selection(teacher, state, contexts)` 包装此边界，参照现有feedback observer按env/episode/input_frame捕获owned快照。

上下文键固定 `selection_context`：identity、measured/root、anchor、accepted、com_w、wheel_anchors_w、measured_wheels_w、active_wheel、nominal_root_z_w、q_seed、branch_q、cfg、producer_backend；choice含index/valid/count/双margin。`verify_preparation_selection(context: dict, choice: dict, *, replay_backend: str, require_backend_evidence: bool) -> list[str]` 返回错误列表并复用既有后端检查、原数值容差。

- [x] 添加RED `test_not_ready_can_search_but_cannot_lift`：真实COM<.010时选择器收到原s实测轮位且执行搜索，`phase != LIFT`；插值中间余量不足不触发新增目标筛选，LIFT/PASS/RESTORE不调用新selector。
- [x] 添加RED `test_selection_evidence_rejects_tampering`：真实producer上下文正例errors=[]；换peer/输入frame、执行后轮位、删字段、篡改候选/任一margin分别 `assert errors`。测试125与无解、单行reset清缓存、重复输入不能混旧上下文。
- [x] 运行 `python -m pytest Go2Pvcnn/tests/test_m1_reference_teacher.py Go2Pvcnn/tests/test_m1_teacher_selection_evidence.py -q`，记录预期RED。
- [x] 接入单一调用边界；新增诊断 `candidate_measured_triangle_margin_m`，BALANCE对应实际choice，非BALANCE为明确N/A。捕获生产端上下文和backend并调用原selector重算，不用输出帧或CPU宽容值冒充原GPU结果。
- [x] 升Teacher implementation v8→v9及probe schema6→7；扩展现有record校验，新schema缺选择证据拒绝，旧schema明确不兼容。保留request/process/apply、两遍反馈、合法hold/abort/5步锁定逻辑不变。
- [x] 上述两文件及 `test_m1_teacher_feedback_evidence.py`、`test_m1_teacher_feedback_transaction.py`、`test_m1_teacher_replay_backend.py`、`test_m1_teacher_reference_validity.py` 全部GREEN；冻结v4仅做几何反例，不回写旧记录。
- [x] 审查并精确提交任务文件，消息 `feat: bind dual support selection to producer evidence`。

## Task 3：纯整机跨越恢复结果监视器

**Files:** 新m1_crossing_recovery模块及同名测试，不导入Isaac、不引用Teacher私有可变状态。
**Interfaces:** 下列dataclass字段均为Tensor，B为环境数/C为本scope障碍数；标识long、mask bool、状态同浮点dtype/device，时间内部float64。冻结scope用clone，reset仅指定行。

- `RecoveryScope`：`env_id[B], episode_id[B], scope_id[B], course_ids[B,C], required[B,C,4], centers_w[B,C,3], half_extents[B,C,2], forward_w[B,3]`；forward为固定水平单位向量，required非空才有跨越资格。
- `RecoveryFrame`：`env_id[B], episode_id[B], scope_id[B], frame[B], sim_time_s[B], dt_s[B], root_state_w[B,13], leg_pos[B,12], default_leg_pos[B,12], wheel_pos_w[B,4,3], wheel_quat_w[B,4,4], wheel_force_w[B,4,3], nominal_root_z_w[B], recovered[B,C,4], valid[B], collision[B], penetration[B], base_contact[B], physical_failure[B], reset[B], ended[B]`。recovered必须按scope.course_ids匹配，不用tensor位置猜身份。
- `RecoveryResult`：`eligible, stable, success, vetoed` bool[B]；`interval_count, start_frame, last_frame` long[B]；`elapsed_s, start_time_s, net_forward_m` float64[B]；`reason: tuple[str,...]`。缺少起点用-1/NaN明确N/A，不伪造0完成。
- `CrossingRecoveryTracker(scope: RecoveryScope)`；`reset(rows: Tensor, scope: RecoveryScope) -> None`；`update(frame: RecoveryFrame) -> RecoveryResult`；合同常量 `RECOVERY_CONTRACT='crossing-recovery-0p3-v1'`。

- [x] 添加RED `test_fifteen_intervals_not_fifteen_observations`：16个20ms相邻合格观测/净前进.01成功；前15个 `not success`，最终interval_count==15，elapsed≈.3。非20ms序列累计真实时间；单个少步不能用epsilon补齐。
- [x] 添加RED `test_identity_and_window_isolation`：同帧同数据重复不加时间、同帧异数据报错；缺帧/反向time/不相符dt/非有限值拒绝证据且不成功；一段.16+中断+一段.14不拼接；reset一行不动peer，旧episode/scope输入拒绝。
- [x] 添加RED `test_scope_requires_all_receipts_and_cylinder_far_side`：空required、单轮代全轮、wrong course ID、root已过但倾斜轮体尾端未过均不eligible。使用Y圆柱r=.0959/宽=.0465沿forward的解析投影，不以有限采样没有命中证明无重叠。
- [x] 添加RED `test_real_restored_motion_and_sticky_veto`：过程倾斜但无违规不否决后续窗口；窗口tilt>.15、rate>.20、腿误差>.15、高差>.08、任一Fz<=10或横向>Fz、yaw误差>.15、forward velocity<=0分别清连续窗口。轮转/root不动、侧移、绕圈不能靠路径长度过.01；早先collision/physical_failure始终veto，ended/reset终帧不能成功。
- [x] 运行 `python -m pytest Go2Pvcnn/tests/test_m1_crossing_recovery.py -q`，确认RED来自缺实现。
- [x] 实现纯monitor及输入合同。所有required收据和四轮最靠后投影超过scope最后障碍远侧才eligible；每帧恢复条件如上。首合格观测计0，只累计连续相邻合格区间；窗口中净位移用固定forward首末root差。表示误差容差不得达到一个dt，缺数据不能默默跳过；碰撞/穿透/机身接触/物理失败sticky否决。
- [x] 同命令GREEN，验证update不修改任何输入、不生成action；逐行/批量结果一致；审查并提交新模块/测试，消息 `feat: evaluate crossing with a measured recovery window`。

## Task 4：探针持续采样、终帧证据及正式A结果

**Files:** probe、probe_contract测试及新recovery_evidence测试；仅任务2/3完成后开始。
**Interfaces:** probe新增 `capture_recovery_scope(state: TeacherState, rows: Tensor, required_pairs: list, *, scope_ids: Tensor) -> RecoveryScope`；`capture_recovery_frame(snapshot: dict, scope: RecoveryScope) -> RecoveryFrame`；`verify_recovery_record(record: dict) -> list[str]` 从raw逐帧重建，不相信缓存success。record新增 `recovery_contract, recovery_scope`；samples新增 `recovery_input, recovery_result`（字段对应任务3，保留轮quat/默认腿角/名义高度/原始失败标记）。

- [x] 添加RED `test_receipt_completion_does_not_end_before_recovery`：用现有AST提取/纯fake NativeProbe测试框架，所有局部凭据齐全后仍执行15个区间；Teacher动作继续原前进，未额外停轮或给每腿加15帧。first-obstacle只固定首障碍义务，transitions固定前两障碍，course全部义务；flat-preparation/single-wheel不输出整机成功。
- [x] 添加RED `test_terminal_recovery_snapshot_and_peer_reset`：auto-reset前捕获终帧；timeout与最后合格窗口同帧仍未完成，不从reset后新root/forces补数据；peer结束/缓存不得串行重算另行状态。collision sticky不因重新合格洗白，20秒不足窗口不能跨episode补时。
- [x] 添加RED `test_recovery_record_tampering_and_suite_gates`：完整新schema正例无errors；删轮quat/时间/身份、伪造净位移/elapsed/success、改scope、仅旧receipt各自有errors。正式course stage3须recovery.success且所有旧unsafe/executable/trace/video检查通过；stage0原20秒平地标准不强加非空crossing。保留两stage各5seed×20/各>=95，不把diagnostic通过算A。
- [x] 运行 `python -m pytest Go2Pvcnn/tests/test_m1_teacher_recovery_evidence.py Go2Pvcnn/tests/test_m1_teacher_probe_contract.py -q`，确认预期RED。
- [x] 在每episode开头冻结scope及固定课程方向；采集所有行raw终帧后才处理任何reset。任务3monitor只在结果路径工作；替换first/transitions/course的receipt即时结束，只有monitor成功才task_complete/local_complete；自然done/timeout/locked/证据错误优先。
- [x] 对schema7要求新结果合同及原始输入，verify_episode从头重放且比对结果；历史schema直接拒绝、不回填。保留原feedback/控制证据检查、视频/trace SHA和中断行计数。没有恢复空间时记录未完成，不遮蔽下个障碍/改Teacher target来凑窗口。
- [x] 同命令及任务1–3测试GREEN；审查并提交，消息 `feat: verify post-cross recovery in teacher probe lifecycle`。

## Task 5：独立审查与新主机隔离逐级验证

**Files:** 仅必要测试反例及上述实现修复；记录至新 `notes/log/2026-10-14-m1-dual-support-crossing-recovery-implementation.md`、README、notes/T306及ai-17/human-17现有入口。工具/脚本新增必须可审查，不用一次性命令偷偷改变控制。
**Interfaces:** 使用probe既有CLI：`--candidate --python --output --mode --teacher-scope --diagnostic-steps --active-wheel --headless --device cuda:0`；candidate必须是脚本所在Go2Pvcnn、python须实际sys.executable，output为candidate内未存在路径。

- [x] 本地只读定位实际可用Python（WindowsApps别名不算已验证解释器），显式执行 `python -m pytest Go2Pvcnn/tests/test_m1_teacher_pose.py Go2Pvcnn/tests/test_m1_reference_teacher.py Go2Pvcnn/tests/test_m1_teacher_ik.py Go2Pvcnn/tests/test_m1_teacher_reference_validity.py Go2Pvcnn/tests/test_m1_teacher_reference_commit.py Go2Pvcnn/tests/test_m1_teacher_feedback_transaction.py Go2Pvcnn/tests/test_m1_teacher_feedback_evidence.py Go2Pvcnn/tests/test_m1_teacher_replay_backend.py Go2Pvcnn/tests/test_m1_teacher_geometry_replay.py Go2Pvcnn/tests/test_m1_teacher_selection_evidence.py Go2Pvcnn/tests/test_m1_crossing_recovery.py Go2Pvcnn/tests/test_m1_teacher_recovery_evidence.py Go2Pvcnn/tests/test_m1_teacher_probe_contract.py -q`；缺环境报告阻塞，禁止称全库通过。
- [x] 请求独立整体验证审查；Critical/Important各用负例RED→修复→GREEN，并重跑涉及任务。不把物理调参伪装成软件bugfix。
- [x] 新host只读验证身份/cwd/Python/Isaac/资产SHA/任务进程及GPU。复用已核实可用隔离目录，或创建事先确认未存在的 `/tmp/m1-teacher-student-candidate-20261014`；此为候选路径而非已存在事实。部署仅本轮审查文件与所需baseline，记录完整SHA清单；不覆盖生产或旧证据。
- [x] GPU安全边界成立后，单次运行 `"$M1Python" "$M1Candidate/scripts/probe_m1_teacher.py" --candidate "$M1Candidate" --python "$M1Python" --output "$M1Candidate/evidence-contract" --mode contract --headless --device cuda:0`（变量由上步核实绝对路径绑定）。核验COMPLETE、逐原始record和实际退出/GPU释放，不仅看exit0。
- [ ] 同CLI改 `--mode teacher --teacher-scope flat-preparation --diagnostic-steps 1000` 和新output。核验四轮分别首次ready后再5帧、双预测/真实COM/载荷/跟踪/实际执行一致；首个失败停止，不跳scope。CPU几何正例不是本关通过。
- [ ] 准备通过后依次四次 `--teacher-scope single-wheel --active-wheel 0/1/2/3 --diagnostic-steps 1000`，每次独立output且确认前进程退出；核验真实抬升、未失支撑、落轮恢复。任一失败则后续NOT_RUN。
- [ ] 依次 `--teacher-scope first-obstacle`、`transitions`、`course`（各1000步上限和独立output）；逐次检查同episode完整义务、圆柱far侧、0.3秒/净前进>=.01、raw/video/trace及backend重算。保持原20秒，不为恢复延长。
- [ ] 局部全过才运行独立output `--mode acceptance --teacher-scope course`，核实stage0/3各5seed×20，全部分母及失败/同行中断保存、各>=95/100，真实视频与完整事件一致。任何关键失败仅诊断并停后续，不启动BC/PPO。
- [x] 按实际结果更新README/notes和计划勾选，分别说明软件通过、局部物理、正式A及NOT_RUN；提交精确任务文件。GitHub普通push若执行须独立ref确认，不把本地提交或文档完成说成掌握跨越。

## 自审与交接

- 已逐项映射双几何规格§2–4至任务1/2、恢复规格§2–4至任务3/4、两规格验证及停止条件至任务5。
- Review Focus五类均有命名负例；结果不反向控制Teacher，原锚点/真实ready/局部5帧与整机窗口不混用。
- 接口名称、shape、版本、身份和终帧优先级一致；任务2/4探针编辑串行，任务3可独立委派。
- 本计划只供审阅，未声称实现、测试、服务器部署或Teacher A通过。审阅确认后沿用子代理执行，不再重复询问执行方式。
