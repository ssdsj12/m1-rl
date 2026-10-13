# M1 Support Posture and Constrained IK Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现并独立验收支撑姿态与受约束IK教师；不把本计划完成等同学生已学会跨越。

**Architecture:** 只读测量、纯张量四腿IK、纯张量机身参考、状态提交分别隔离；探针绑定真实执行动作和终帧证据。实现与两阶段审查按任务推进，物理验收严格串行；教师A仍是后续BC/撤除/PPO的前置门槛。

**Tech Stack:** Python、PyTorch、pytest、Isaac Lab/Sim、现有AME动作解码与FK、SSH。

**Spec:** [已确认书面规格](../specs/2026-10-13-m1-support-ik-redesign-design.md)。用户本轮明确确认；基线`cb6fde9`，旧教师`4ec1bd6`。执行方式沿用用户指定子代理分工。本计划待用户审阅，不是实施/部署回执。

## Global Constraints

- 分支`10-13`；普通clone `C:/Users/xk/Documents/project/m1-ppo-recovery`已接受原地工作，不冒称linked worktree。保留dirty notes/watchers与全部PT，精确stage文件，普通push不force。
- 原资产/质量/重力/PD/关节限位/rootZ `.62m`不变；16维12腿+4轮，正式学生/PPO最终无教师/IK/轨迹接管，无MPC/WBC/AMP/扶持外力。
- 平地→10cm，8目标+70填充、20s、零额外净空；无碰撞/穿透、真实三轮支撑、经过及远侧5帧稳定恢复不变。
- 碰撞每控制步2分、累计20重置、耗尽不额外termination20；其余奖励、学生观测、std不改。
- 机身范围相对捕获参考X±.04m/Y±.06m/降低≤.08m，且不低于当前环境名义root高度−.08m，不高于捕获高度。
- 支撑Fz>30N、横向≤向上载荷；准备实测COM投影余量≥.01m。COM投影是平地近似，不是动态稳定证明。
- 刹稳速度≤.05m/s、倾角≤.15rad、角速度≤.20rad/s；原抬轮上界front .22m/rear .20m、far buffer .15m不变。
- IK最多32次、DLS damping .05/差分1e-4/每分量dq≤.25rad、残差≤.002m；膝分支保持且绝对角≥.10rad。执行腿目标变化≤2.5rad/s，不能clip后冒充达到原目标。
- 候选≤126组，参考回溯8级1至1/128；无解冻结，连续5步锁定失败，最多额外5步诊断后收尾。诊断退出不改环境终止规则，失败计入分母。
- 教师新设计初版加最多2次有证据单机制修订；失败停止、不启动BC。教师平地和10cm各固定5seed×20、≥95/100；学生后续mean/sample各10cm≥90/100、平地≥95/100。
- 旧训练/自动监控保持暂停。只在隔离candidate目录做验证，生产不覆盖；GPU任务严格串行，不改网络/全局Git/SSH/显示。

## Review Focus

- 混合批次中一行缺COM/目标证据或非有限值：拒绝该行，不用root/实角补造；合法行继续。Task1测试。
- 非零roll/pitch/yaw及非零环境origin：完整刚体变换、名义高度下界正确，不能依赖平地零原点巧合。Task3测试。
- 可达终点但中间迭代越膝分支/限位，或只有摆动腿可达：整行拒绝，不能截断解伪造成功。Task2测试。
- 同帧重复调用、缺帧、单行reset紧邻terminal：不多推参考，不把旧预算/目标/receipt交给新回合。Task4/5测试。
- action在wrapper解码后与请求不一致、失败回合早停或缺视频：显式失败，不能漏分母或给BC有效标签。Task5测试。

## 工作区、命令与职责

每任务由新实现子代理承担，随后新规格审查、质量审查；问题修复后复审再继续。主代理控制提交、同步、GPU与证据汇总，不把共享文件交给同时写入的代理。Task1→2→3→4→5→6串行依赖；独立审查可并行只读，禁止并行原生任务。每个子代理先读其任务、规格及仓库必要notes；不自行扩展工作流。

当前host `root@a21495354824192000872439`，生产`/root/quad/m1-rl/.worktrees/contact-recovery`，既有candidate `/tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn`；Python `/opt/conda/envs/env_issacsim/bin/python`。执行前核实身份及candidate import来源，备份candidate中将被替换文件并记录SHA；禁止直接运行硬编码旧host的helper。

下述CPU命令在candidate的`Go2Pvcnn`工作目录运行，前缀统一为：

```bash
CUDA_VISIBLE_DEVICES='' PYTHONPATH="$PWD:$PWD/rsl_rl" /opt/conda/envs/env_issacsim/bin/python -m pytest
```

本地缺torch/pytest不能报测试通过；纯CPU不导入Isaac，不安装/改动全局依赖。每个RED必须是预期行为断言失败，意外缺包不算RED。每次记录命令、退出码、源码SHA；隔离同步不意味着部署。

新增责任边界：`m1_teacher_measurements.py`只算COM和命名目标；`m1_teacher_ik.py`只做FK/Jacobian/受约束解；`m1_teacher_pose.py`只选姿态和参考回溯。状态生命周期仍在`m1_reference_teacher.py`，Isaac读取在`m1_teacher_adapter.py`，录像和证明在`probe_m1_teacher.py`。不改extension planner核心。

### Task 1：真实COM与上一实际执行目标

**Files:** Create `Go2Pvcnn/ame_baseline/m1_teacher_measurements.py`, `Go2Pvcnn/tests/test_m1_teacher_measurements.py`; Modify `m1_reference_teacher.py`的TeacherState、`m1_teacher_adapter.py`的snapshot及`tests/test_m1_reference_teacher.py`夹具（均在Go2Pvcnn相应ame_baseline/tests目录）。

**Interfaces:** 新增纯函数`mass_weighted_com(body_com_w: Tensor[B,N,3], masses: Tensor[B,N]) -> tuple[Tensor[B,3], Tensor[B,bool]]`；TeacherState新增`com_pos_w: Tensor[B,3]`, `measurement_valid: Tensor[B,bool]`, `last_applied_leg_target: Tensor[B,12]`, `applied_target_valid: Tensor[B,bool]`。snapshot新增必填同名target与valid关键字参数，由探针真实apply观测提供；shape/name/device错误抛异常，数值坏行置valid=False。

- [ ] RED：新增`test_mass_weighted_com_is_not_root_proxy`（两点x=0/4、质量3/1得x=1）、`test_bad_mass_is_row_local`（NaN/负质量/总质量0行无效、其他行不变）、`test_snapshot_clones_named_targets_and_never_steps`（打乱关节名仍映射正确、输入修改不影响快照、step/reset调用数0）。缺目标证据时不得从实角补齐。
- [ ] 运行上述测试文件，核实预期失败并记录。
- [ ] 实现纯测量函数与State校验；适配器读取真实body COM/mass且核对body维度，不读terrain作为actor新增特征。更新旧教师测试夹具显式提供测量证据，不默认所有真实输入有效。
- [ ] CPU运行`tests/test_m1_teacher_measurements.py tests/test_m1_reference_teacher.py -q`，通过后审查；此时探针调用点在Task5更新，禁止提前运行原生。
- [ ] 仅提交本任务文件：`feat: add measured teacher COM and applied-target contract`。

### Task 2：四腿受约束IK与拒绝诊断

**Files:** Create `Go2Pvcnn/ame_baseline/m1_teacher_ik.py`, `Go2Pvcnn/tests/test_m1_teacher_ik.py`; Modify `Go2Pvcnn/ame_baseline/m1_reference_teacher.py`中几何辅助函数导入/兼容导出，暂不接新状态逻辑。

**Interfaces:** 将`body_feet(q)`, `body_jacobian(q, epsilon=1e-4)`, `dls_step(...)`移入新模块并在旧模块兼容导出，避免循环import。新增`IKConfig`保存本规格IK常量；`solve_constrained_ik(q_seed: Tensor[B,12], target_b: Tensor[B,4,3], branch_q: Tensor[B,12], cfg: IKConfig) -> IKResult`。IKResult字段：`q[B,12]`, `valid[B]`, `residual_m[B,4]`, `joint_limit_ok[B,4]`, `branch_ok[B,4]`, `extension_margin_rad[B,4]`（abs(knee)−.10）, `workspace_ok[B,4]`, `iterations[B,4]`, `reason[B,4]`。reason用稳定IntEnum，含OK/NONFINITE/JOINT_LIMIT/BRANCH/NEAR_STRAIGHT/WORKSPACE/RESIDUAL。

- [ ] RED：`test_all_four_legs_must_be_valid`使支撑腿目标不可达，即使摆动腿可达valid=False；`test_iterates_do_not_cross_limits_or_knee_branch`记录所有接受迭代；`test_near_straight_is_rejected_at_point_one`固定.099/.100边界；`test_residual_and_budget_are_not_relaxed`断言residual≤.002且iterations≤32才有效。
- [ ] RED补充`test_fk_offsets_not_root_radius_shortcut`、`test_nan_row_does_not_poison_batch`及现有Jacobian/autograd对照。运行新测试核实失败。
- [ ] 实现以真实FK和安装偏移计算工作空间检查；DLS提案仅在原限位/分支内且误差下降时接受，否则该腿保持本次迭代前值；32次内仍未达标返回拒绝诊断。不得放宽残差/增迭代/事后clip最终解。
- [ ] CPU运行`tests/test_m1_teacher_ik.py tests/test_m1_reference_teacher.py -q`；保持旧求解入口兼容到Task4替换，审查拒绝路径与参数。
- [ ] 提交：`feat: add bounded four-leg teacher IK with rejection evidence`。

### Task 3：统一坐标的机身候选与参考回溯

**Files:** Create `Go2Pvcnn/ame_baseline/m1_teacher_pose.py`, `Go2Pvcnn/tests/test_m1_teacher_pose.py`。Consume Task2的IKConfig/IKResult及solver；不import ReferenceTeacher。

**Interfaces:** `BodyPose(pos_w: Tensor[B,3], quat_w: Tensor[B,4])`；`PoseReference(body: BodyPose, wheels_w: Tensor[B,4,3])`；`world_to_goal_body(reference: PoseReference) -> Tensor[B,4,3]`；`support_margin(com_w, wheel_w, active_wheel) -> tuple[Tensor[B], Tensor[B,bool]]`。

`choose_support_pose(measured: BodyPose, anchor: BodyPose, accepted: BodyPose, com_w, wheel_anchors_w, active_wheel, nominal_root_z_w, q_seed, branch_q, cfg: IKConfig) -> PoseChoice`，PoseChoice含`reference`, `ik`, `valid`, `candidate_index`, `predicted_margin_m`, `candidate_count`。

`backtrack_reference(accepted: PoseReference, requested: PoseReference, q_seed, branch_q, last_applied_q, dt, cfg: IKConfig) -> ReferenceStep`，ReferenceStep含`reference`, `ik`, `valid`, `backtrack_index`, `slew_ok`。批次与Task2一致；roll/pitch/yaw插值用单位四元数最短弧，位置线性。

- [ ] RED：`test_full_world_body_transform_with_roll_pitch_yaw`将完整旋转前后往返与world点对齐；`test_origin_relative_height_floor`对不同env origin验证相同相对下界；`test_triangle_degenerate_and_com_margin`测试退化、边界.01m与外侧负值。
- [ ] RED：`test_search_envelope_and_stable_tie_order`断言候选≤126、原范围、归一化位移平方和/索引平局；`test_backtrack_not_joint_clipping`断言有效解保持.002m且执行增量≤2.5*dt、最多8级；`test_predicted_com_does_not_certify_measured_support`仅返回预测信息，不生成成功/phase。
- [ ] 运行新测试文件，核实失败；实现规格5×5×5网格加上一接受姿态，预测COM采用当前body偏移的候选刚体变换，按规格筛选/排序；回溯每次重新构造四轮body目标并求解。
- [ ] CPU运行`tests/test_m1_teacher_pose.py tests/test_m1_teacher_ik.py -q`，检查不超过范围、无混用heading、未借clip产生有效标签；两阶段审查。
- [ ] 提交：`feat: generate reachable teacher body references in one frame`。

### Task 4：教师状态提交、实测准备与失败冻结

**Files:** Modify `Go2Pvcnn/ame_baseline/m1_reference_teacher.py`, `Go2Pvcnn/tests/test_m1_reference_teacher.py`; Create `Go2Pvcnn/tests/test_m1_teacher_reference_commit.py`。

**Interfaces:** 沿用`ReferenceTeacher.step(TeacherState) -> TeacherOutput`；TeacherConfig新增并fingerprint记录所有已批准边界。TeacherOutput新增`diagnostic: Tensor[B,D]`及`failure_locked: Tensor[B,bool]`；固定列名元组`TEACHER_DIAGNOSTIC_FIELDS`定义D，旧六字段保留。诊断列包括请求/接受pose、world/body轮目标、实际/预测COM余量、Task2每腿诊断、回溯索引、无效连续步数和参考冻结原因；整数以列定义标注，不凭位置猜。

局部空地夹具入口`ReferenceTeacher.diagnostic_step(state, *, active_wheel: int, lift: bool) -> TeacherOutput`复用同一准备/IK/冻结路径。lift=False只准备；lift=True在实测准备后按原front/rear抬升上界抬落指定轮（目标基于捕获轮高），不伪造障碍或receipt，输出active_target=-1且不能作为课程验收/BC数据。正式`step`不调用局部夹具。

- [ ] RED：`test_invalid_ik_freezes_all_reference_clocks`保存接受pose/age/body_age/lift_age，连续无解前4步不变且停轮，5步failure_locked；`test_hold_last_applied_target_not_falling_measured_q`让实角变化，合法fallback仍保持上次接受目标并无有效标签。
- [ ] RED：`test_lift_requires_measured_com_and_three_loads`预测通过但实测未达不进LIFT；`test_duplicate_gap_and_one_row_reset`重复不增计数、缺帧不累计稳定帧、reset只清该行，旧episode receipt不计入新回合。
- [ ] RED：`test_prepare_anchor_does_not_follow_slip`准备支撑轮滑移不运输锚点；`test_pass_transports_common_xy_only`运输三轮平均XY共同增量、记录各轮残差、不修改roll/pitch参考；`test_restore_receipt_is_not_phase_certificate`没有真实receipt始终不能结束必跨。
- [ ] RED：`test_diagnostic_lift_uses_same_constraints_without_course_receipt`局部夹具复用全部准备/IK/连续性/冻结门槛，不写course/receipt，不输出课程成功标签。
- [ ] 运行新/旧教师测试核实失败；实现请求/接受/测量分离及提交后再推进。采用已有1cm位置/.15rad姿态等实测准备阈值，附加真实COM余量；初始刹稳等待与活动阶段失败分开。APPROACH/RESTORE也要满足执行目标连续性，不可用旧nominal跳变绕过上限。
- [ ] CPU运行`tests/test_m1_reference_teacher.py tests/test_m1_teacher_reference_commit.py tests/test_m1_teacher_pose.py tests/test_m1_teacher_ik.py tests/test_m1_teacher_measurements.py -q`；审查所有早退与缓存路径都有完整诊断、无失效标签。
- [ ] 提交：`fix: commit teacher progress only after valid measured references`。

### Task 5：真实apply回读、逐帧证据和失败计数

**Files:** Modify `Go2Pvcnn/scripts/probe_m1_teacher.py`, `Go2Pvcnn/tests/test_m1_teacher_probe_contract.py`; Create `Go2Pvcnn/scripts/replay_m1_teacher_geometry.py`, `Go2Pvcnn/tests/test_m1_teacher_geometry_replay.py`。

**Interfaces:** `ActionEvidence`扩展apply后目标快照（不是仅process后的请求），按真实关节名提供Task1必填`last_applied_leg_target/applied_target_valid`；reset目标从机器人已写入target缓冲命名读取，若接口/证据缺失则probe失败，不猜nominal或实角。Task4固定列诊断转结构化JSON，schema升版，旧schema仍可读取但不能补造新字段。

探针新增`--teacher-scope {flat-preparation,single-wheel,first-obstacle,transitions,course}`默认course，`--active-wheel {0,1,2,3}`仅single-wheel使用；局部模式只能diagnostic，不允许acceptance。不改实际场景、物理或成功tracker。冻结几何CLI为`replay_m1_teacher_geometry.py --trace PATH --frames 49,57 --output PATH`，按实际输入schema/关节名读取，缺字段明确拒绝该行。

flat-preparation和single-wheel在原空地stage0调用Task4局部入口；前者依次检查四轮对应支撑准备，后者实测一次离地和承重恢复。first-obstacle/transitions/course在原10cm stage3调用正式step，分别观察首个目标、前后轮与下一个目标衔接、完整课程，不删目标或改required集合。

- [ ] RED：`test_apply_evidence_precedes_physics_and_survives_reset`同一控制步一次process、按实际decimation记录每个物理子步apply目标且一致、20ms输出、terminal仍旧episode；`test_wrapper_changed_target_rejects_label`请求和实际目标不符则标签无效；`test_locked_failure_counts_in_suite_denominator`早停失败不丢弃，至多额外5步；`test_missing_video_or_hash_fails_acceptance`。
- [ ] RED：`test_local_scope_cannot_claim_course_success`及`test_frozen_replay_missing_input_is_not_counterfactual`，不让局部、旧缺字段或数学重算形成物理成功证据。运行测试核实失败。
- [ ] 实现scope调度与日志；所有局部scope仅通过正常教师动作进入目标阶段，禁止直接写姿态制造支撑。保留完整20s及16个必跨receipt集合检查。新增学生示范可用性字段与failure_locked联动，旧失败轨迹不获BC标签。
- [ ] CPU运行`tests/test_m1_teacher_probe_contract.py tests/test_m1_teacher_geometry_replay.py`及Task1–4测试集；运行冻结run2/run3几何输入，记录输入SHA/实际输入帧/旧新目标/拒绝原因。缺COM或执行目标时仅比较有证据支持的几何子问题，不填假值运行完整新状态机。
- [ ] 提交：`test: bind redesigned teacher evidence to actual applied targets`。更新[设计记录](../../../notes/log/2026-10-13-m1-support-ik-redesign.md)与README，只写已测事实。

### Task 6：隔离原生分级验收与有界结论

**Files:** Create evidence log `notes/log/2026-10-13-m1-support-ik-native.md`; Modify README及notes/index、todo/T306、log/index当前条目。仅若出现可定位缺陷，按对应Task1–5 RED/GREEN做最多两次单机制修订，不预先预留放宽参数。

**Interfaces:** 使用Task5 CLI和带SHA的result/JSONL/video。通过输出必须同时包含候选commit、import来源、合同核对、完整episode分母与真实receipt；`MILESTONE_A PASS`不能由局部scope生成。

- [ ] 现场核实host、旧训练/回放都已退出、GPU无占用及当前candidate import来源。若有未知进程，停止此任务，不杀无关进程。精确同步候选并核对每个runtime SHA，记录备份。
- [ ] 先运行CPU全相关集合及原生`--mode contract`，确认16动作、原物理、10cm课程、每步2/预算20、一次步进。命令模板如下，每次使用新输出目录并等待退出/GPU释放：

```bash
PYTHONPATH="$PWD:$PWD/rsl_rl" /opt/conda/envs/env_issacsim/bin/python scripts/probe_m1_teacher.py --candidate "$PWD" --python /opt/conda/envs/env_issacsim/bin/python --output /tmp/m1-support-ik-contract-v1 --mode contract --headless --device cuda:0 --enable_cameras
```

- [ ] 依次运行`--mode teacher --teacher-scope flat-preparation`、single-wheel每个wheel、first-obstacle、transitions、course，`--diagnostic-steps 1000`为20s上限而非强制等待。每项通过其实际准备/抬落/receipt证据才进入下一项；失败锁定按5额外步收尾。将输出路径改为对应scope/版本，保留全部失败文件。
- [ ] 首次关键失败查看同env输入→动作→载荷→IK拒绝/碰撞顺序；仅有证据才允许新设计v2/v3单机制修订并回跑相关CPU与前置scope。第三版仍失败则停止，汇总新的阻挡子节点，不进入BC、不重启旧训练。
- [ ] 所有局部与完整诊断通过后运行`--mode acceptance --teacher-scope course`，固定seed101–105各20回合、stage0/3分别100回合。预先固定分母；平地与10cm均≥95/100才解除教师A阻挡。失败/超时/碰撞/无完整receipt都计失败，保留视频SHA和全量轨迹。
- [ ] 最终独立全分支审查，核对旧约束、CPU/native证据和notes一致。普通push HEAD至10-13并独立ls-remote确认；不stage旧watchers/PT/无关dirty notes。报告教师结果及GPU已释放，不启动BC/PPO。本计划到教师A结束，后续按父计划另行执行。

## 计划自审与交接

- [x] 规格各段已映射：测量Task1，IK Task2，坐标/候选Task3，提交/失败Task4，日志/身份Task5，串行验收与停止Task6。
- [x] Review Focus五类均有指定反例；共享接口名称、张量顺序与来源明确，未新增核心物理/学生功能。
- [x] 求解步与执行步、预测COM与实测COM、诊断早停与环境reset、局部成功与100回合验收分开。
- [ ] 用户审阅计划；执行方式已经指定为子代理，不重复询问方式。
- [ ] 开始Task1实现及逐任务两阶段审查。

本次计划编写不运行新控制代码、不开展GPU验证、不声称问题已修复。按writing-plans交接要求，计划审阅后开始实施。
