# Teacher 有界跟踪补偿 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变物理与成功标准的条件下，给Teacher增加有界实测位置纠偏，验证它能否解决支撑准备阶段的跟踪停滞。

**Architecture:** 纯张量反馈模块生成X轮速和Y/Z虚拟位移提案；Teacher逐行事务协调名义参考、执行参考、积分与回溯。探针独立记录真实process/apply及速度、effort，只以实际支撑/经过/恢复验收。

**Tech Stack:** Python、PyTorch、pytest、现有受约束IK、Isaac Lab/Sim、隔离候选目录。

**Spec:** [已确认的补充规格](../specs/2026-10-13-m1-teacher-bounded-feedback-design.md)，同时读取其链接的原支撑/IK规格。用户已确认本计划直接继续修正，执行方式沿用子代理；[实施记录](../../../notes/log/2026-10-13-m1-teacher-bounded-feedback-implementation.md)。

## Global Constraints

- 基线runtime `4f5a875`；设计提交 `c01bb8b`；工作分支 `10-13`。保留所有旧PT、轨迹和无关dirty文件，不整体stage工作树。
- 原16维动作（12腿位置、4轮速度）、PD、质量/重力、rootZ .62m、物理限位不变；无力矩前馈/MPC/WBC/AMP/外力/直接写状态。
- 10cm课程与20s上限不变；真实三轮支撑、COM≥.01m、跟踪位置≤.01m、零额外净空、无碰撞穿透、远侧5帧恢复不变。
- 碰撞每控制步2分、累计20重置、不重复终止费用；学生观测/奖励/std不变；不启动BC/PPO，学生后续完全移除Teacher/IK/补偿。
- X：Kp=1.0 s^-1、Ki=.2 s^-2、积分输出≤.02m/s、总纠偏≤.04m/s、变化率≤.10m/s²。Y/Z各：Kp=.5、Ki=.5 s^-1、积分输出≤.01m、总偏置≤.02m、变化率≤.02m/s。
- 使用捕获yaw坐标；X只进共同轮速，Y/Z只进虚拟位移。原航向纠偏、PASS锚点运输保持；不扩大物理名义参考±.04m X/±.06m Y/下移≤.08m包络。
- 执行关节slew≤2.5rad/s、abs(knee)≥.10、原膝分支、IK残差≤.002m/最多32次；不事后clip关节。最多2遍×8档×2个四腿IK。
- 剩余一次单机制原生修订由本候选使用。首关键失败停止，不自动改增益/PD/门槛重跑；GPU只允许串行原生，不部署生产、不恢复旧训练或自动监控。

## Review Focus

- 非零yaw及轮名重排时，正向位置误差不能变成反向轮速；Task1/2坐标和真实decoder测试固定。
- 比例输出已经限幅时积分不能暗中增长，零误差也不能突变清掉历史输出；Task1反饱和与退出测试固定。
- 只有虚拟IK通过、实际未跟上或名义IK无效时，不能推进阶段或给BC标签；Task2双参考测试固定。
- 重复帧、跳帧、单行reset、目标切换不得重放积分或跨episode污染；Task2生命周期测试固定。
- 请求/执行错位、缺腿effort、准备只短暂达标时，不能用完整文件或局部ready冒充验收成功；Task3负例固定。

## 文件边界与执行约定

新增`Go2Pvcnn/ame_baseline/m1_teacher_feedback.py`只做张量数学；现有`m1_teacher_pose.py`只加双参考求解；`m1_reference_teacher.py`拥有生命周期与提交。`m1_teacher_adapter.py`新增独立诊断快照，不把effort混入策略观测；`scripts/probe_m1_teacher.py`绑定真实证据和局部保持检查。

Task1→Task2→Task3→Task4顺序依赖。沿用子代理逐任务实现与独立规格/代码审查，不让多个实现者同时写Teacher。Task3测量测试可提前只读准备，但不能在Task2接口稳定前合入。原生仅主代理现场核实安全边界后串行执行。

每项RED应为预期行为失败，缺依赖不算RED。CPU在隔离候选`/tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn`运行，明确核对源码SHA/import来源：

```bash
CUDA_VISIBLE_DEVICES='' PYTHONPATH="$PWD:$PWD/tests:$PWD/rsl_rl" /opt/conda/envs/env_issacsim/bin/python -m pytest <该任务列出的测试路径> -q
```

上式仅为统一前缀，下面每项给出测试路径。不能在本地缺torch时声称测试通过；不安装依赖。用现有候选隔离和备份方式同步，生产`/root/quad/m1-rl/.worktrees/contact-recovery`不写。每个commit只显式stage本任务文件。

### Task 1：纯反馈提案与防积分累积

**Files:** Create `Go2Pvcnn/ame_baseline/m1_teacher_feedback.py`、`Go2Pvcnn/tests/test_m1_teacher_feedback.py`。

**Interfaces:** 新增frozen `FeedbackConfig`，按Global Constraints固定参数并拒绝越界或非有限配置。`FeedbackState(integral, output)`两字段均浮点Tensor[B,3]，列顺序X/Y/Z，X单位m/s，Y/Z单位m。`FeedbackProposal(error_h, integral_candidate, raw_output, output, limited)`，前四项[B,3]，limited为bool[B,3]。

`propose_feedback(root_ref_w, root_meas_w, captured_yaw, previous: FeedbackState, dt, cfg: FeedbackConfig, *, active) -> FeedbackProposal`，位置[B,3]、yaw/dt浮点[B]、active bool[B]。active=False仅清积分候选并衰减旧输出。`select_integral(previous, proposal, *, safe, transaction_valid, backtracked) -> Tensor[B,3]`：三bool[B]，实现一次回退及逐轴饱和卸积分规则。函数不修改输入、不提交状态、不调用IK。

- [ ] 写RED `test_heading_and_axis_assignment`：yaw=π/2且world误差[0,.03,0]时heading X=.03；Y/Z纯误差不能产生X输出。`test_limits_and_units`以dt=.02断言首步X≤.002，Y/Z各≤.0004；连续饱和总输出≤[.04,.02,.02]、积分≤[.02,.01,.01]。测试值用torch.testing.assert_close，不依赖精确十进制相等。
- [ ] 写RED `test_antiwindup_and_unwind`：限幅/回溯/transaction_valid=False不增长积分；仅安全且有效时允许减小已饱和轴|I|；safe=False不允许卸积分例外。`test_exit_slew_with_residual_integral`：零误差保留合法残余积分，active=False才清积分并限速回零。`test_bad_shape_nan_dt_and_owned_output`拒绝形状/设备/非有限输入、dt≤0，并验证结果不alias输入。
- [ ] 运行`tests/test_m1_teacher_feedback.py`确认预期RED。
- [ ] 实现上述三类数据与两函数；先按Ki*e*dt提案，限积分、限幅及限速独立记录；wheel总上限由Task2提供事务反馈，不在纯模块猜测电机顺序。
- [ ] 同命令GREEN；独立规格/质量审查通过后commit `feat: add bounded teacher feedback proposals`。

### Task 2：双参考IK与Teacher事务集成

**Files:** Modify `Go2Pvcnn/ame_baseline/m1_teacher_pose.py`、`Go2Pvcnn/ame_baseline/m1_reference_teacher.py`；Create `Go2Pvcnn/tests/test_m1_teacher_feedback_transaction.py`；Extend `Go2Pvcnn/tests/test_m1_teacher_reference_commit.py`。

**Interfaces:** 使用Task1类型。pose新增`FeedbackReferenceStep(physical, command, nominal_ik, command_ik, output, valid, backtrack_index, slew_ok)`，前两项PoseReference、两IK为既有IKResult、output[B,3]、valid/slew_ok bool[B]、index long[B]。

`backtrack_feedback_reference(accepted, requested, previous_output, proposed_output, captured_yaw, q_seed, branch_q, last_applied_q, dt, cfg: IKConfig, *, execution_valid) -> FeedbackReferenceStep`；沿用PoseReference和既有q[B,12]，dt为正浮点标量，yaw[B]。`execution_valid(command_ik: IKResult, output: Tensor[B,3]) -> Tensor[B]`为Teacher提供的无副作用检查回调，逐beta核对真实encode/decode、总轮速与执行连续性，返回bool。pose不反向import Teacher。每beta同步插值physical增量及三轴输出增量；command=physical加heading[0,Y,Z]，wheel world目标不变；两IK都验残差/限位/分支，仅command解验slew。Teacher在回溯前按固定名义轮速收缩新增X纠偏至总轮速与slew可行交集，再由回调逐beta核验；无可行交集拒绝，不允许先提交后再clip。

`ReferenceTeacher.step(state)`及`diagnostic_step(...)`签名不变。逐行新增feedback state及accepted_command；原accepted字段继续只表示physical参考。`TeacherConfig`增加固定反馈参数，fingerprint实现标识升级`support-ik-transaction-v8`且覆盖全部数值与诊断字段。避免把dataclass塞入现有只接受数字的校验循环。

- [ ] 写RED `test_tracking_freezes_physical_but_corrects_command`：复用prepared_teacher(diagnostic=True)，共同平移实际root/COM/wheels .03/.09m，未限幅X提案随误差改变且方向正确；物理参考和年龄冻结、真实decoded动作有合法反馈，不要求饱和首步两个动作不同。
- [ ] 写RED `test_virtual_ik_never_certifies_readiness`、`test_nominal_invalid_rejects_virtual_valid`、`test_nominal_solution_is_not_execution_slew`，分别固定实际未达不ready、名义失败不接受、仅执行解需相对last_apply满足2.5*dt。保留2mm、膝分支与真实decoder检查。
- [ ] 写RED `test_rejected_feedback_transaction_is_atomic`：强制IK/decoder/总轮速/连续性拒绝；检查物理与虚拟参考/积分/年龄不泄漏；无合法hold仍executable=False、物理步前abort。`test_bounded_second_pass`用计数器证明≤2×8×2次四腿求解，无递归重算，第二遍失败不apply。
- [ ] 写RED `test_feedback_lifecycle`覆盖重复帧逐位幂等、跳帧只dt一次、单行reset、terminal旧快照、阶段间保留、APPROACH衰减、未归零不得新捕获。`test_com_failure_does_not_disable_safe_feedback`保持三轮载荷合格但COM不足，允许纠偏，不推进阶段。
- [ ] 写RED `test_wheel_correction_respects_decoder_headroom`：按真实命名排列和半径转换，X共同量加入原名义/航向量，总限幅优先收缩新增量且不改名义。若总上限与纠偏slew无可行交集，拒绝事务/认证hold，不擅自违反任一约束。
- [ ] 运行新transaction测试及`tests/test_m1_teacher_reference_commit.py`，记录预期RED。
- [ ] 实现双参考求解和Teacher两遍积分事务；积分未被接受则固定旧值重新求解一次。安全失败不积累；输入合法且COM不足仅冻结名义进度，不关闭反馈。退出时保留旧参考过渡，不能清掉参考后再尝试平滑。
- [ ] 运行上述测试及Task1、`tests/test_m1_teacher_pose.py tests/test_m1_teacher_ik.py tests/test_m1_teacher_phase_progression.py tests/test_m1_teacher_reference_validity.py`；更新旧测试只调整被明确批准改变的准备轮速/双参考语义，保留原安全断言。两阶段审查通过后commit `feat: integrate transactional teacher tracking correction`。

### Task 3：真实速度/effort和补偿执行证据

**Files:** Modify `Go2Pvcnn/ame_baseline/m1_teacher_adapter.py`、`Go2Pvcnn/scripts/probe_m1_teacher.py`；Create `Go2Pvcnn/tests/test_m1_teacher_feedback_evidence.py`；Extend `Go2Pvcnn/tests/test_m1_teacher_measurements.py`、`Go2Pvcnn/tests/test_m1_teacher_probe_contract.py`。

**Interfaces:** adapter新增纯读取`read_actuation_evidence(robot) -> dict`，返回`joint_names`、`joint_vel[B,16]`（asset名称顺序）、`leg_joint_names`、`leg_computed_effort[B,12]`、`leg_applied_effort[B,12]`（planner顺序）、`sources`（API名/单位/估计属性）、`valid[B]`；返回clone。只在诊断采样使用，不更改TeacherState或策略观测。缺API、重复名称、错误shape/非有限腿值必须使诊断验收失败，不从差分或P项补造；Implicit轮力矩若附带必须标为估计。

probe `SCHEMA_VERSION=6`。已有TEACHER_DIAGNOSTIC_FIELDS追加命名字段：physical/command/measured参考、heading误差、integral_before/candidate/committed、output_before/requested/committed、限幅原因、第一/第二遍与beta、nominal/command IK残差、名义/最终轮速；完整声明稳定字段名及integer集合，fingerprint与verifier共用该声明，不手写错序列表。新`PreparationHoldCounter.update(row, *, input_ready, output_ready, frame, episode_id) -> bool`：首次双ready仅建立起点，其后连续5个控制帧双ready才True；中断归零、重复幂等、跳帧不补、单行reset不串行污染。只局部探针使用。

- [ ] 写RED `test_actuation_snapshot_names_and_missing_api`：fake robot打乱名称，核对速度/腿effort映射、来源和clone；缺字段/重复名拒绝。`test_terminal_evidence_is_pre_reset`确认数据来自相同旧episode物理结果，不读reset后buffer。
- [ ] 写RED `test_compensation_evidence_matches_actual_apply`：更改任一命令、残差参考、积分提交值或实执行目标，verifier拒绝；第一/第二遍未提交提案不可标成apply。`test_missing_effort_or_legacy_schema_rejects_acceptance`验证缺必需证据、schema5旧轨迹不获新验收。
- [ ] 写RED `test_preparation_requires_five_additional_ready_frames`：首次ready+4帧仍False，+5帧True；中途任何input/output不ready重新计数。`test_local_and_aborted_traces_never_become_bc`保留局部/失败/abort不可示范，旧abort完整性Minor仍单列，不在本任务泛化修复。
- [ ] 运行新evidence及两个扩展测试，确认RED。
- [ ] 实现快照、schema6writer/verifier、局部保持计数；保留一次process/4次apply/20ms、无可执行动作即prephysics abort和原失败分母。不能用虚拟位置复算实际ready，也不修改正式Teacher门槛。
- [ ] 运行Task1/2/3全部测试，加`tests/test_m1_teacher_geometry_replay.py tests/test_m1_teacher_episode_reset.py tests/test_m1_teacher_elapsed.py`；两阶段审查后commit `test: authenticate bounded feedback and actuation evidence`。

### Task 4：串行原生验收、停止及交付

**Files:** Create `notes/log/2026-10-13-m1-teacher-bounded-feedback-native.md`；Modify README、notes/index、notes/todo、T306、notes/log/index本任务条目。原生失败不自动产生第二个实现版本。

**Interfaces:** 使用现有probe CLI、Task3 schema6轨迹/result/video/SHA；scope顺序及mode不改。后续训练只接受正式Teacher A通过，不接受局部ready。

- [ ] 整体独立审查Task1–3及继承安全路径；相关CPU集合全部通过并保存命令/退出码/源码SHA。源码未完整同步或重要审查未关闭不得原生。核实新host `root@a21495354824192000872439`、训练/play/probe全部退出、GPU空闲；未知进程不杀、不并发。
- [ ] 备份并同步隔离candidate，记录逐文件SHA、Git ref、实际import来源；输出使用新目录，不覆盖v1/v2。运行一次原生合同，命令如下（cwd为候选Go2Pvcnn）：

```bash
PYTHONPATH="$PWD:$PWD/rsl_rl" /opt/conda/envs/env_issacsim/bin/python scripts/probe_m1_teacher.py --candidate "$PWD" --python /opt/conda/envs/env_issacsim/bin/python --output "$PWD/m1-feedback-contract-v3" --mode contract --headless --device cuda:0 --enable_cameras
```

- [ ] 合同通过且进程退出/GPU释放后依次运行同CLI：`--mode teacher --teacher-scope flat-preparation --diagnostic-steps 1000`（候选内目录`$PWD/m1-feedback-flat-v3`）；随后single-wheel配`--active-wheel 0/1/2/3`各独立目录，再first-obstacle、transitions、course。每次只跑一个，前置实测未通过不跑后项。flat-preparation检查四个支撑准备且新增5帧保持，20s不延长。
- [ ] 首关键失败立即停止后续scope，仅按原诊断最多5额外帧收尾；记录同env/attempt补偿→实际q/qd/effort→载荷/COM/位置→拒绝或碰撞链、饱和比例及GPU释放。不能按一次失败自作主张换增益或力矩方案；剩余修订预算已使用。
- [ ] 仅全部局部与课程诊断通过，运行同CLI `--mode acceptance --teacher-scope course --diagnostic-steps 1000`，候选内独立目录`$PWD/m1-feedback-acceptance-v3`；核对内部固定seed101–105各20、stage0/3各100完整预定分母。每项≥95/100且完整视频/实际receipt才Teacher A PASS；相关并行行数不冒充独立随机试验。失败/not_run如实保留。
- [ ] 更新README/notes仅写现场事实，报告实际通过/阻挡、各阶段NOT_RUN和未解决Minor；检查旧PT/生产/物理均未变。保存证据后显式文件commit；按既有授权普通push `HEAD:refs/heads/10-13`并独立ls-remote核实，失败只报发布失败。不得stage旧watcher或无关历史文档，不force/改全局网络配置。
- [ ] 到Teacher A即停，不运行BC/PPO；训练和自动监控保持暂停，后续教师撤除/学生学习按父计划另行执行。

## 计划自审与交接

- [x] 规格1–4映射Task1/2；规格5映射Task3；规格6与预算映射Task4；退出、反饱和、真实执行及相关样本解释均有任务。
- [x] 五类Review Focus均有具名反例；新函数/types在本计划定义，沿用接口名称已核对源码。
- [x] 只新增外层位置反馈，不扩展物理、力矩控制、学生或reward功能；不把文档检查当算法测试。
- [x] 用户审阅并确认直接继续修正；沿用已选子代理执行，不重复询问执行方式。
- [x] 已进入superpowers:subagent-driven-development，逐任务RED/GREEN和两阶段审查；完成状态以实施记录为准。

## 2026-10-13 执行回执（覆盖上方计划勾选状态）

- [x] Task1 a3a7635、Task2 2e5f214、Task3 6189861实现并通过任务审查；终审集中修复39a6590及限定复审关闭I1/M1/M2。
- [x] CPU按[实施日志](../../../notes/log/2026-10-13-m1-teacher-bounded-feedback-implementation.md)记录真实RED/GREEN：聚合451pass/1fixture错误后11项补测，终修57及12项定向通过，不是全库重跑通过。
- [x] Task4新候选原生合同通过；flat-preparation首次关键证据失败后停止、保存实际轨迹/视频并释放GPU。
- [ ] 完整四腿准备/抬落/课程/Teacher A验收：NOT_RUN或BLOCKED，不以局部6帧ready替代。详见[原生记录](../../../notes/log/2026-10-13-m1-teacher-bounded-feedback-native.md)。
- [x] BC/PPO未启动，生产/PD/物理/成功阈值未改，旧PT/轨迹保留；不自动追加原生修订。
